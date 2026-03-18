import requests
import json
import os
import sys

# Add parent directory to path to allow importing knowledge
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def fetch_osm_tourism_data(area_name="Singapore", limit=20):
    """
    Fetch restaurants from OSM in a specific area that have 
    accessibility or family-friendly tags.
    """
    # Overpass QL query:
    # 1. Get the area ID for the given name
    # 2. Find restaurants/cafes in nodes and ways
    query = f"""
    [out:json][timeout:25];
    area[name="{area_name}"]->.searchArea;
    (
      node["amenity"~"restaurant|cafe"](area.searchArea);
      way["amenity"~"restaurant|cafe"](area.searchArea);
    );
    out center {limit};
    """
    
    print(f"--- Querying Overpass API for: {area_name} ---")
    try:
        response = requests.post(OVERPASS_URL, data={'data': query})
        response.raise_for_status()
        data = response.json()
        return data.get("elements", [])
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def map_osm_to_kg(osm_elements):
    """
    Convert raw OSM elements into our tourism Knowledge Graph node format.
    """
    kg_nodes = []
    
    for el in osm_elements:
        tags = el.get("tags", {})
        node_id = f"osm_{el.get('id')}"
        name = tags.get("name", "Unknown Establishment")
        
        # Facet mapping based on our TAO/TDKG
        facets = ["Place", "TourismService"]
        properties = {
            "locatedIn": "Singapore",
            "osm_id": el.get("id"),
            "lat": el.get("lat") or el.get("center", {}).get("lat"),
            "lon": el.get("lon") or el.get("center", {}).get("lon")
        }
        
        # 1. Determine Class
        if tags.get("amenity") in ["restaurant", "cafe"]:
            node_class = "Restaurant"
            properties["servesCuisine"] = tags.get("cuisine", "General").title()
        else:
            node_class = "TourismService" # Fallback

        # 2. Extract Opening Hours
        if "opening_hours" in tags:
            properties["openingHours"] = tags.get("opening_hours")

        # 3. Extract AccessRequirement Facet
        if tags.get("wheelchair") in ["yes", "designated"]:
            facets.append("AccessRequirement")
            facets.append("Accessibility") # Backward compat
            properties["wheelchairAccessible"] = True
        
        # 4. Extract ActivityFeature Facet (Family Friendly)
        # In OSM, this is often 'highchair' or 'diet:halal' (often proxy for family-friendly in SG)
        if tags.get("highchair") == "yes":
            facets.append("ActivityFeature")
            facets.append("FamilyFriendly") # Backward compat
            properties["childrensMenu"] = True # Proxy for child-friendly features
            
        kg_node = {
            "id": node_id,
            "class": node_class,
            "name": name,
            "facets": sorted(list(set(facets))),
            "properties": properties
        }
        kg_nodes.append(kg_node)
        
    return kg_nodes

if __name__ == "__main__":
    elements = fetch_osm_tourism_data()
    print(f"Found {len(elements)} elements in OSM.")
    
    if elements:
        print("\n--- Sample Mapping to KG Format ---")
        kg_formatted = map_osm_to_kg(elements)
        print(json.dumps(kg_formatted[:3], indent=2))
        
        # Save a sample to verify
        with open("osm_sample_ingest.json", "w") as f:
            json.dump(kg_formatted, f, indent=2)
            print(f"\nSaved {len(kg_formatted)} nodes to osm_sample_ingest.json")
