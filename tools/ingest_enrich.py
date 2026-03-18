import json
import os
import sys
import logging
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import google.generativeai as genai
from dotenv import load_dotenv
from tools.onemap_client import OneMapClient

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
onemap = OneMapClient()

def get_enrichment_from_llm(lat: float, lon: float, name: str) -> Dict[str, str]:
    """
    Pillar 2 & 3 Fallback: Resolves Planning Area and adds Cultural/Historical Context.
    """
    # 1. Attempt OneMap Resolution for Planning Area first (Pillar 2)
    planning_area = onemap.get_planning_area(lat, lon)
    
    # 2. Use LLM for Cultural Insight (Pillar 3) and as fallback for Pillar 2
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    if planning_area:
        prompt = (
            f"You are a Singapore tourism expert. An establishment named '{name}' is located in the '{planning_area}' Planning Area. "
            "Provide a one-sentence cultural or historical insight about this place or its specific location.\n"
            "Output ONLY a JSON object with keys: 'planning_area' and 'cultural_insight'. "
            f"Use '{planning_area}' for the planning_area key."
        )
    else:
        prompt = (
            f"You are a Singapore tourism and geography expert. Given the coordinates ({lat}, {lon}) "
            f"and the establishment name '{name}':\n"
            "1. Identify the official Singapore Planning Area (e.g., 'Chinatown', 'Marina Bay', etc.).\n"
            "2. Provide a one-sentence cultural or historical insight about this place or its specific location.\n"
            "Output ONLY a JSON object with keys: 'planning_area' and 'cultural_insight'."
        )
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        result = json.loads(text)
        if planning_area:
            result["planning_area"] = planning_area
        return result
    except Exception as e:
        logging.error(f"LLM Enrichment failed for {name}: {e}")
        return {"planning_area": planning_area or "Singapore", "cultural_insight": "A notable establishment in the heart of the city."}

def enrich_nodes(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich raw OSM nodes with Planning Area and cultural context.
    """
    enriched_nodes = []
    print(f"--- Enriching {len(nodes)} nodes with LLM (Triple-Threat Pillar 2 & 3) ---")
    
    for node in nodes:
        props = node.get("properties", {})
        lat, lon = props.get("lat"), props.get("lon")
        name = node.get("name")
        
        # Resolve enrichment via LLM
        enrichment = get_enrichment_from_llm(lat, lon, name)
        
        node["properties"]["locatedIn"] = enrichment.get("planning_area", "Singapore")
        node["properties"]["description"] = enrichment.get("cultural_insight", "")
        
        enriched_nodes.append(node)
        print(f"  ✓ {name} -> {node['properties']['locatedIn']}")
        
    return enriched_nodes

if __name__ == "__main__":
    sample_file = "osm_sample_ingest.json"
    if not os.path.exists(sample_file):
        print(f"Error: {sample_file} not found. Run ingest_osm.py first.")
        sys.exit(1)
        
    with open(sample_file, "r") as f:
        raw_nodes = json.load(f)
        
    # Test with top 5 for speed/token limits
    enriched = enrich_nodes(raw_nodes[:5])
    
    with open("enriched_sample.json", "w") as f:
        json.dump(enriched, f, indent=2)
        print(f"\nSaved enriched data to enriched_sample.json")
