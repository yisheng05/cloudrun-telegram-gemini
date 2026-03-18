import os
import sys
import logging
import json
import requests
from typing import List, Dict, Any, Optional

# Add project root to path
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(_THIS_DIR))

from tools.ingest_osm import fetch_osm_tourism_data, map_osm_to_kg
from tools.ingest_enrich import enrich_nodes
from tools.merge_kg import merge_nodes

KG_PATH = os.path.join(os.path.dirname(_THIS_DIR), "data", "knowledge_graph.json")

# Fallback coordinate map for common Singapore districts to help OSM radius search
DISTRICT_COORDS = {
    "Tiong Bahru": (1.2865, 103.8328),
    "Outram": (1.2828, 103.8379),
    "Tampines": (1.3525, 103.9447),
    "Jurong": (1.3329, 103.7436),
    "Ang Mo Kio": (1.3691, 103.8454),
    "Bedok": (1.3236, 103.9273),
    "Bugis": (1.3007, 103.8560),
}

def fetch_osm_by_radius(lat: float, lon: float, radius: int = 500, limit: int = 10):
    """Fallback search using coordinates and radius."""
    url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"~"restaurant|cafe"](around:{radius},{lat},{lon});
      way["amenity"~"restaurant|cafe"](around:{radius},{lat},{lon});
    );
    out center {limit};
    """
    try:
        resp = requests.post(url, data={'data': query})
        resp.raise_for_status()
        return resp.json().get("elements", [])
    except Exception as e:
        logging.error(f"OSM Radius search failed: {e}")
        return []

def run_dynamic_ingestion(location: str, target_class: str = "Restaurant") -> int:
    """
    Triggers the Triple-Threat pipeline for a specific area/class.
    Returns the number of new nodes added.
    """
    logging.info(f"--- Triggering Dynamic Ingestion for: {location} ({target_class}) ---")
    
    # 1. Physicality (OSM)
    search_area = f"{location}, Singapore" if "Singapore" not in location else location
    raw_osm = fetch_osm_tourism_data(area_name=search_area, limit=10)
    
    # Fallback to radius search if area name fails
    if not raw_osm and location in DISTRICT_COORDS:
        lat, lon = DISTRICT_COORDS[location]
        logging.info(f"Area search failed. Retrying with 1000m radius around {lat},{lon}")
        raw_osm = fetch_osm_by_radius(lat, lon, radius=1000, limit=10)

    if not raw_osm:
        logging.warning(f"No real-time data found in OSM for {location}")
        return 0
    
    # 2. Map to KG Format
    kg_nodes = map_osm_to_kg(raw_osm)
    
    # 3. Enrichment (OneMap + LLM Cultural Context)
    # We only enrich the top 3 to keep response times reasonable for a chat session
    enriched = enrich_nodes(kg_nodes[:3])
    
    # Update locatedIn to the specific district if we used coordinates
    for n in enriched:
        if n["properties"].get("locatedIn") == "Singapore":
             n["properties"]["locatedIn"] = location
    
    # 4. Merge into KG
    temp_file = os.path.join(_THIS_DIR, f"dynamic_batch_{os.getpid()}.json")
    try:
        with open(temp_file, "w") as f:
            json.dump(enriched, f)
        
        # Merge logic
        with open(KG_PATH, "r") as f:
            master_kg = json.load(f)
        
        existing_ids = {n["id"] for n in master_kg.get("nodes", [])}
        added = 0
        for node in enriched:
            if node["id"] not in existing_ids:
                master_kg["nodes"].append(node)
                added += 1
        
        with open(KG_PATH, "w") as f:
            json.dump(master_kg, f, indent=2)
            
        return added
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    # Test run
    logging.basicConfig(level=logging.INFO)
    added = run_dynamic_ingestion("Tiong Bahru", "Restaurant")
    print(f"Dynamic ingestion added {added} nodes.")
