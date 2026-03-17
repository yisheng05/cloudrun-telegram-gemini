#!/usr/bin/env python3
"""
Test suite for Actionability and Mixed-Initiative Dialog features.

Demonstrates:
1. CHECK_ACTIONABILITY function validating critical parameters
2. Mixed-Initiative REQUEST_INFO_SCRIPT providing clarifications
3. Faceted knowledge graph querying across multiple facets
"""

import logging
import json
from middleware import (
    perception_simulate,
    check_actionability,
    request_info_script,
    deliberation_query_kg,
    action_render_response,
)
from knowledge import (
    load_kg,
    query_by_facet,
    query_by_facets,
    find_by_facet_and_filters,
)

logging.basicConfig(level=logging.INFO)

# ============================================================================
# TEST 1: Actionability Checking with Clarification
# ============================================================================

print("\n" + "="*80)
print("TEST 1: Actionability Checking and Mixed-Initiative Learning")
print("="*80)

test_cases_actionability = [
    {
        "user_input": "Book me a table",
        "expected_actionable": False,
        "description": "Vague dining request - no cuisine or location"
    },
    {
        "user_input": "Find Italian restaurants",
        "expected_actionable": True,
        "description": "Specific cuisine provided"
    },
    {
        "user_input": "Show me restaurants near Marina Bay",
        "expected_actionable": True,
        "description": "Location specified"
    },
    {
        "user_input": "Hi, how are you?",
        "expected_actionable": True,
        "description": "Chat intent - doesn't need parameters"
    },
    {
        "user_input": "Who won the world cup?",
        "expected_actionable": True,
        "description": "General knowledge - doesn't need parameters"
    },
]

for i, test in enumerate(test_cases_actionability, 1):
    user_input = test["user_input"]
    print(f"\n[Test 1.{i}] {test['description']}")
    print(f"User: {user_input}")
    
    # Perception phase
    tmr = perception_simulate(user_input)
    intent = tmr.get("intent")
    entities = tmr.get("entities", {})
    
    print(f"  → Intent detected: {intent}")
    print(f"  → Entities extracted: {json.dumps(entities, indent=2)}")
    
    # Check actionability
    is_actionable, clarification = check_actionability(intent, entities)
    
    print(f"  → Actionable: {is_actionable}")
    if clarification:
        print(f"  → Clarification: {clarification}")
    
    assert is_actionable == test["expected_actionable"], \
        f"Expected actionability {test['expected_actionable']}, got {is_actionable}"


# ============================================================================
# TEST 2: Faceted Knowledge Graph Querying
# ============================================================================

print("\n" + "="*80)
print("TEST 2: Faceted Knowledge Graph Querying")
print("="*80)

kg = load_kg()
print(f"\nLoaded {len(kg.get('nodes', []))} entities from knowledge graph")

# Test 2.1: Query by single facet
print("\n[Test 2.1] Entities with 'Accessibility' facet:")
accessibility_entities = query_by_facet("Accessibility")
print(f"  Found {len(accessibility_entities)} entities:")
for entity in accessibility_entities:
    print(f"    - {entity.get('name')} (class: {entity.get('class')})")
    props = entity.get('properties', {})
    if props.get('wheelchairAccessible'):
        print(f"      ✓ Wheelchair accessible")

# Test 2.2: Query by multiple facets (intersection)
print("\n[Test 2.2] Entities with BOTH 'Place' and 'Service' facets:")
place_service = query_by_facets(["Place", "Service"])
print(f"  Found {len(place_service)} entities:")
for entity in place_service:
    print(f"    - {entity.get('name')} (class: {entity.get('class')})")

# Test 2.3: Complex faceted query with filters
print("\n[Test 2.3] Find Italian restaurants WITH wheelchair access (multi-facet + filter):")
results = find_by_facet_and_filters(
    required_facets=["Place", "Service", "Accessibility"],
    filters={
        "servesCuisine": "Italian",
        "wheelchairAccessible": True
    }
)
print(f"  Found {len(results)} restaurants:")
for entity in results:
    props = entity.get('properties', {})
    print(f"    - {entity.get('name')}")
    print(f"      Location: {props.get('locatedIn')}")
    print(f"      Cuisine: {props.get('servesCuisine')}")
    print(f"      Price: {props.get('hasPriceRange')}")
    print(f"      Hours: {props.get('openingHours')}")
    print(f"      Wheelchair Access: {props.get('wheelchairAccessible')}")


# ============================================================================
# TEST 3: End-to-End Deliberation with Actionability
# ============================================================================

print("\n" + "="*80)
print("TEST 3: End-to-End Deliberation Pipeline")
print("="*80)

end_to_end_tests = [
    {
        "user_input": "Book me something",
        "description": "Actionability failure - should request clarification"
    },
    {
        "user_input": "I want Italian food in Marina Bay",
        "description": "Actionability success - should find restaurants"
    },
    {
        "user_input": "Find accessible restaurants",
        "description": "Partial information - location missing"
    },
]

for i, test in enumerate(end_to_end_tests, 1):
    user_input = test["user_input"]
    print(f"\n[Test 3.{i}] {test['description']}")
    print(f"User: {user_input}")
    
    # Full Perception -> Deliberation pipeline
    tmr = perception_simulate(user_input)
    deliberation = deliberation_query_kg(tmr)
    
    mode = deliberation.get("mode")
    print(f"  → Mode: {mode}")
    
    if mode == "CLARIFICATION_NEEDED":
        clarification = deliberation.get("clarification_message")
        print(f"  → Clarification needed: {clarification}")
    elif mode == "KG_DRIVEN":
        verified = deliberation.get("verified", [])
        print(f"  → Found {len(verified)} verified results:")
        for result in verified:
            print(f"    - {result.get('name')}")
    elif mode == "LLM_FALLBACK":
        print(f"  → No results in KG, would use LLM")
    
    # Render response
    response = action_render_response(deliberation, user_input)
    print(f"  → Response: {response[:200]}...")


# ============================================================================
# TEST 4: Facet-Specific Response Rendering
# ============================================================================

print("\n" + "="*80)
print("TEST 4: Facet-Aware Response Rendering")
print("="*80)

print("\n[Test 4.1] Restaurant with multiple facets (Place + Service + Accessibility + Event_Host):")
tmr = perception_simulate("I want Italian food in Marina Bay with wheelchair access and jazz")
deliberation = deliberation_query_kg(tmr)

verified = deliberation.get("verified", [])
print(f"Found {len(verified)} results")
for entity in verified:
    name = entity.get("name")
    facets = entity.get("facets", [])
    props = entity.get("properties", {})
    
    print(f"\n  Entity: {name}")
    print(f"  Facets: {', '.join(facets)}")
    print(f"  Properties:")
    
    if "Service" in facets:
        print(f"    - Cuisine: {props.get('servesCuisine')}")
        print(f"    - Price: {props.get('hasPriceRange')}")
    
    if "Place" in facets or "Building" in facets:
        print(f"    - Location: {props.get('locatedIn')}")
        print(f"    - Hours: {props.get('openingHours')}")
    
    if "Accessibility" in facets:
        print(f"    - Wheelchair Accessible: {props.get('wheelchairAccessible')}")
    
    if "Event_Host" in facets:
        events = props.get("hostingEvents", [])
        if events:
            print(f"    - Hosts Events: {', '.join(events)}")


print("\n" + "="*80)
print("All tests completed successfully!")
print("="*80)
