import json
import os
import logging
from typing import List, Dict, Any, Optional

_THIS_DIR = os.path.dirname(__file__)
_DEFAULT_KG = os.path.join(_THIS_DIR, "data", "knowledge_graph.json")


def load_kg(path: str | None = None) -> Dict[str, Any]:
    p = path or _DEFAULT_KG
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception:
        logging.exception("Failed to load knowledge graph at %s", p)
        return {"nodes": []}


def resolve_alias(name: str) -> str:
    """Resolve an alias to its canonical name if it exists."""
    kg = load_kg()
    aliases = kg.get("aliases", {})
    return aliases.get(name.lower(), name)



def query_by_class(cls: str) -> List[Dict[str, Any]]:
    kg = load_kg()
    return [n for n in kg.get("nodes", []) if n.get("class") == cls]


def query_by_facet(facet: str) -> List[Dict[str, Any]]:
    """Query nodes that have a specific facet (e.g., 'Accessibility', 'Event_Host')."""
    kg = load_kg()
    results = []
    for n in kg.get("nodes", []):
        facets = n.get("facets", [])
        if facet in facets:
            results.append(n)
    return results


def query_by_facets(facets: List[str]) -> List[Dict[str, Any]]:
    """Query nodes that have ALL specified facets (intersection)."""
    kg = load_kg()
    results = []
    for n in kg.get("nodes", []):
        node_facets = set(n.get("facets", []))
        if all(f in node_facets for f in facets):
            results.append(n)
    return results


_ONTOLOGY_FILE = os.path.join(_THIS_DIR, "src", "ontology", "tourism_ontology.json")

def load_ontology() -> Dict[str, Any]:
    try:
        with open(_ONTOLOGY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logging.warning("Ontology file not found or invalid.")
        return {}

def query_by_ontology(
    target_class: Optional[str] = None,
    facets: List[str] = [],
    properties: Dict[str, Any] = {}
) -> List[Dict[str, Any]]:
    """Complex ontology-driven query.
    
    Example: 
    - target_class="Restaurant"
    - facets=["Accessibility", "FamilyFriendly"]
    - properties={"childrensMenu": True, "servesCuisine": "Italian"}
    """
    kg = load_kg()
    ontology = load_ontology()
    results = []

    for node in kg.get("nodes", []):
        # 1. Class Check
        if target_class and node.get("class") != target_class:
            continue
        
        # 2. Facet Check
        node_facets = set(node.get("facets", []))
        if facets and not all(f in node_facets for f in facets):
            continue
        
        # 3. Property Check
        node_props = node.get("properties", {})
        match = True
        for k, v in properties.items():
            prop_val = node_props.get(k)
            if isinstance(prop_val, list):
                if v not in prop_val:
                    match = False
                    break
            elif prop_val != v:
                match = False
                break
        
        if match:
            results.append(node)
            
    return results

def find_by_filters(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Find nodes matching all filter criteria."""
    results = []
    for n in load_kg().get("nodes", []):
        props = n.get("properties", {})
        ok = True
        for k, v in filters.items():
            # Handle aliases for name lookups
            if k == "name":
                v = resolve_alias(v)

            # Handle both exact matches and list containment
            prop_val = props.get(k)
            if isinstance(prop_val, list):
                if v not in prop_val:
                    ok = False
                    break
            else:
                if prop_val != v:
                    ok = False
                    break
        if ok:
            results.append(n)
    return results


def find_by_facet_and_filters(
    required_facets: List[str],
    filters: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Find nodes that have all required facets AND match all filters.
    
    This enables nuanced queries like:
    - "Find places (Place facet) that serve dinner (Service facet) 
       and are wheelchair accessible (Accessibility facet) 
       and have Italian cuisine"
    """
    kg = load_kg()
    results = []
    
    for n in kg.get("nodes", []):
        node_facets = set(n.get("facets", []))
        props = n.get("properties", {})
        
        # Check if node has all required facets
        if not all(f in node_facets for f in required_facets):
            continue
        
        # Check if node matches all filters
        match = True
        for k, v in filters.items():
            prop_val = props.get(k)
            if isinstance(prop_val, list):
                if v not in prop_val:
                    match = False
                    break
            else:
                if prop_val != v:
                    match = False
                    break
        
        if match:
            results.append(n)
    
    return results


def get_entity_by_id(entity_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single entity by its ID."""
    kg = load_kg()
    for n in kg.get("nodes", []):
        if n.get("id") == entity_id:
            return n
    return None


def find_by_partial_name(name_fragment: str) -> List[Dict[str, Any]]:
    """Find nodes with names containing the fragment (case-insensitive)."""
    kg = load_kg()
    fragment_lower = name_fragment.lower()
    results = []
    for n in kg.get("nodes", []):
        if fragment_lower in n.get("name", "").lower():
            results.append(n)
    return results


if __name__ == "__main__":
    kg = load_kg()
    print("Loaded nodes:", len(kg.get("nodes", [])))
    
    # Test facet-aware queries
    print("\nAccess facet nodes:", len(query_by_facet("Accessibility")))
    print("Event_Host facet nodes:", len(query_by_facet("Event_Host")))
    print("Nodes with both Place and Service:", len(query_by_facets(["Place", "Service"])))
