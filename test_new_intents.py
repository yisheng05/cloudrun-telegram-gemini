
import os
import sys
import logging
import json
from middleware import handle_request, perception_simulate, deliberation_query_kg, action_render_response

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def run_test(name, input_text, expected_mode, expected_entities=None, expected_facets=None):
    print(f"\n--- Test: {name} ---")
    print(f"Input: '{input_text}'")
    
    # 1. Perception
    tmr = perception_simulate(input_text)
    print(f"TMR: {json.dumps(tmr)}")
    
    if expected_entities:
        for k, v in expected_entities.items():
            if tmr.get("entities", {}).get(k) != v:
                print(f"FAIL: Entity mismatch for {k}. Expected {v}, got {tmr.get('entities', {}).get(k)}")
    
    # 2. Deliberation
    result = deliberation_query_kg(tmr)
    mode = result.get("mode")
    verified = result.get("verified", [])
    
    print(f"Mode: {mode}")
    print(f"Found {len(verified)} items")
    for v in verified:
        print(f" - {v.get('name')} ({v.get('class')})")
        
    if mode != expected_mode:
        print(f"FAIL: Mode mismatch. Expected {expected_mode}, got {mode}")
    
    if expected_facets:
        used_facets = result.get("required_facets", [])
        if set(used_facets) != set(expected_facets):
             print(f"FAIL: Facet mismatch. Expected {expected_facets}, got {used_facets}")

    # 3. Action (Rendering)
    reply = action_render_response(result, input_text)
    print(f"Reply Preview: {reply[:100]}...")

def main():
    # Test 1: Hotel booking
    run_test("Hotel Search", 
             "I want to book a hotel in Marina Bay", 
             "KG_DRIVEN", 
             expected_entities={"accommodation": "hotel", "locatedIn": "Marina Bay"},
             expected_facets=["Place", "Accommodation"])

    # Test 2: Shopping
    run_test("Shopping Mall", 
             "Where can I find a mall near Orchard?", 
             "KG_DRIVEN", 
             expected_entities={"shopping_type": "Mall"},
             expected_facets=["Place", "Shopping"])

    # Test 3: Nature/Park
    run_test("Nature Park", 
             "I want to visit a nature park", 
             "KG_DRIVEN", 
             expected_entities={"activity_type": "Nature"},
             expected_facets=["Place", "Attraction", "NaturalFeature"])

    # Test 4: Planning (General)
    run_test("Planning Day", 
             "Plan a day trip for me", 
             "KG_DRIVEN", # Should default to broad search for now
             expected_entities={"planning_intent": "day_trip"},
             expected_facets=["Place", "Attraction"])

if __name__ == "__main__":
    main()
