#!/usr/bin/env python3
"""
CODE EXAMPLES & ARCHITECTURE

This file demonstrates how to use the new Actionability & Mixed-Initiative features.
"""

# ============================================================================
# EXAMPLE 1: Using CHECK_ACTIONABILITY Directly
# ============================================================================

from middleware import check_actionability

print("="*80)
print("EXAMPLE 1: Direct Actionability Check")
print("="*80)

# Scenario: User wants to book
is_actionable, clarification = check_actionability(
    intent="booking",
    entities={}  # Empty - no parameters provided
)

print(f"\nBooking request with no parameters:")
print(f"  Actionable: {is_actionable}")
print(f"  Clarification: {clarification}")

# Scenario: User provides cuisine
is_actionable, clarification = check_actionability(
    intent="inform",
    entities={"servesCuisine": "Italian"}
)

print(f"\nDining request with cuisine:")
print(f"  Actionable: {is_actionable}")
print(f"  Clarification: {clarification}")


# ============================================================================
# EXAMPLE 2: Perception Phase - Intent & Entity Extraction
# ============================================================================

from middleware import perception_simulate

print("\n" + "="*80)
print("EXAMPLE 2: Perception Phase")
print("="*80)

test_inputs = [
    "Book me a table at 7 PM for 2 people",
    "Find accessible Italian restaurants",
    "Hi, how are you doing today?",
    "What's the weather in Singapore?",
]

for user_input in test_inputs:
    tmr = perception_simulate(user_input)
    print(f"\nInput: \"{user_input}\"")
    print(f"  Intent: {tmr.get('intent')}")
    print(f"  Entities: {tmr.get('entities')}")


# ============================================================================
# EXAMPLE 3: Deliberation Phase - KG Query with Facets
# ============================================================================

from middleware import deliberation_query_kg
import json

print("\n" + "="*80)
print("EXAMPLE 3: Deliberation Phase")
print("="*80)

# Scenario 1: Simple restaurant query
print("\nScenario 1: Find Italian restaurant")
tmr = perception_simulate("I want Italian food")
deliberation = deliberation_query_kg(tmr)

print(f"  Mode: {deliberation['mode']}")
print(f"  Required facets: {deliberation.get('required_facets')}")
if deliberation['mode'] == 'CLARIFICATION_NEEDED':
    print(f"  Clarification: {deliberation.get('clarification_message')}")
else:
    print(f"  Results found: {len(deliberation['verified'])}")

# Scenario 2: Specific request
print("\nScenario 2: Find Italian in Marina Bay")
tmr = perception_simulate("Italian restaurants in Marina Bay")
deliberation = deliberation_query_kg(tmr)

print(f"  Mode: {deliberation['mode']}")
print(f"  Filters applied: {deliberation['filters']}")
print(f"  Results found: {len(deliberation['verified'])}")
for result in deliberation['verified']:
    print(f"    - {result['name']}")


# ============================================================================
# EXAMPLE 4: Knowledge Graph Facet Queries
# ============================================================================

from knowledge import (
    query_by_facet,
    query_by_facets,
    find_by_facet_and_filters,
    load_kg
)

print("\n" + "="*80)
print("EXAMPLE 4: Facet-Aware Knowledge Queries")
print("="*80)

# Query 1: All entities with Accessibility facet
print("\n1. Entities with Accessibility facet:")
accessible = query_by_facet("Accessibility")
for entity in accessible:
    print(f"   - {entity['name']}")

# Query 2: Entities with multiple facets
print("\n2. Entities with Place AND Service facets:")
dining_places = query_by_facets(["Place", "Service"])
print(f"   Found {len(dining_places)} entities")
for entity in dining_places:
    print(f"   - {entity['name']} ({entity['class']})")

# Query 3: Complex query with facets and filters
print("\n3. Italian restaurants WITH wheelchair access:")
results = find_by_facet_and_filters(
    required_facets=["Place", "Service", "Accessibility"],
    filters={
        "servesCuisine": "Italian",
        "wheelchairAccessible": True
    }
)
for entity in results:
    props = entity['properties']
    print(f"   - {entity['name']}")
    print(f"     Location: {props.get('locatedIn')}")
    print(f"     Price: {props.get('hasPriceRange')}")


# ============================================================================
# EXAMPLE 5: End-to-End Pipeline
# ============================================================================

from middleware import handle_request, action_render_response

print("\n" + "="*80)
print("EXAMPLE 5: Complete Pipeline (Perception → Deliberation → Action)")
print("="*80)

print("\nScenario: User asks for wheelchair-accessible restaurant")
user_input = "I need accessible dining options"

# Phase 1: Perception
print(f"\n1. PERCEPTION")
print(f"   Input: \"{user_input}\"")
tmr = perception_simulate(user_input)
print(f"   TMR: {json.dumps(tmr, indent=6)}")

# Phase 2: Actionability
print(f"\n2. ACTIONABILITY CHECK")
is_actionable, clarification = check_actionability(tmr['intent'], tmr['entities'])
print(f"   Actionable: {is_actionable}")
if not is_actionable:
    print(f"   Clarification: {clarification}")

# Phase 3: Deliberation (if actionable)
if is_actionable:
    print(f"\n3. DELIBERATION")
    deliberation = deliberation_query_kg(tmr)
    print(f"   Mode: {deliberation['mode']}")
    print(f"   Required facets: {deliberation.get('required_facets')}")
    print(f"   Results: {len(deliberation['verified'])} found")
    
    # Phase 4: Action
    print(f"\n4. ACTION - RENDER RESPONSE")
    response = action_render_response(deliberation, user_input)
    print(f"   {response[:150]}...")


# ============================================================================
# EXAMPLE 6: Facet-Specific Property Access
# ============================================================================

from knowledge import get_entity_by_id

print("\n" + "="*80)
print("EXAMPLE 6: Entity with Multiple Facets")
print("="*80)

# Get a complex entity
entity = get_entity_by_id("rest4")  # Jazzroom Dinner Club
if entity:
    print(f"\nEntity: {entity['name']}")
    print(f"Class: {entity['class']}")
    print(f"Facets: {', '.join(entity['facets'])}")
    
    print(f"\nProperties organized by facet:")
    props = entity['properties']
    
    print(f"  [Service] Cuisine: {props.get('servesCuisine')}")
    print(f"  [Service] Price: {props.get('hasPriceRange')}")
    print(f"  [Service] Hours: {props.get('openingHours')}")
    
    print(f"  [Place] Location: {props.get('locatedIn')}")
    print(f"  [Building] WiFi: {props.get('hasWifi')}")
    print(f"  [Building] Parking: {props.get('hasParking')}")
    
    print(f"  [Accessibility] Wheelchair: {props.get('wheelchairAccessible')}")
    
    print(f"  [Event_Host] Events: {', '.join(props.get('hostingEvents', []))}")


# ============================================================================
# EXAMPLE 7: Response Rendering with Facet Awareness
# ============================================================================

from middleware import action_render_response

print("\n" + "="*80)
print("EXAMPLE 7: Rich Response Rendering")
print("="*80)

# Create a deliberation result
tmr = perception_simulate("Italian restaurant with jazz")
deliberation = deliberation_query_kg(tmr)

print(f"\nDiningMode: {deliberation['mode']}")
if deliberation['mode'] == 'KG_DRIVEN':
    print(f"\nVerified Results ({len(deliberation['verified'])} found):")
    
    response = action_render_response(deliberation, "Italian restaurant with jazz")
    print(f"{response}")


# ============================================================================
# EXAMPLE 8: Intent Classification Tree
# ============================================================================

print("\n" + "="*80)
print("EXAMPLE 8: Intent Classification & Actionability Matrix")
print("="*80)

intent_matrix = {
    "chat": {
        "examples": ["Hi!", "How are you?", "What's your name?"],
        "required": "None",
        "actionable": "Always"
    },
    "general_knowledge": {
        "examples": ["Who won the World Cup?", "What's the capital of France?"],
        "required": "None",
        "actionable": "Always"
    },
    "dining": {
        "examples": ["Find Italian food", "Restaurants near Marina Bay"],
        "required": "cuisine_or_location",
        "actionable": "If cuisine OR location provided"
    },
    "booking": {
        "examples": ["Book me a hotel", "Find accommodation"],
        "required": "accommodation_type",
        "actionable": "If accommodation type provided"
    },
    "event": {
        "examples": ["Find concerts", "Art exhibitions"],
        "required": "event_type",
        "actionable": "If event type provided"
    }
}

for intent, info in intent_matrix.items():
    print(f"\n{intent.upper()}")
    print(f"  Examples: {', '.join(info['examples'][:2])}")
    print(f"  Required: {info['required']}")
    print(f"  Actionable: {info['actionable']}")


# ============================================================================
# EXAMPLE 9: Metrics & Monitoring
# ============================================================================

print("\n" + "="*80)
print("EXAMPLE 9: Metrics Tracking")
print("="*80)

print("""
Key Metrics for Monitoring:

1. actionability_failures
   - When: User provides vague request
   - Why: Shows how often clarification is needed
   - Use: Optimize prompts and UX

2. actionability_success
   - When: User provides clear, actionable request
   - Why: Shows user clarity
   - Use: Measure query quality

3. tmr_failures
   - When: TMR extraction fails
   - Why: Model struggling with intent extraction
   - Use: Fine-tune perception examples

4. final_response_failures
   - When: Response generation fails
   - Why: Model or KG issues
   - Use: Debug generation problems

5. facet_query_count
   - When: Multi-facet query executed
   - Why: Tracks advanced feature usage
   - Use: Feature adoption metrics
""")


# ============================================================================
# EXAMPLE 10: Architecture Overview
# ============================================================================

print("\n" + "="*80)
print("EXAMPLE 10: System Architecture")
print("="*80)

print("""
REQUEST FLOW:
┌─────────────────────────────────────────────────────────────────────┐
│ TELEGRAM                                                            │
│ (User sends message)                                                │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ MAIN.PY - Webhook Handler                                           │
│ (Receives POST, forwards to middleware)                             │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ MIDDLEWARE - Pipeline Orchestrator                                   │
│                                                                     │
│ 1. PERCEPTION                                                       │
│    ├─ perception_simulate() or request_tmr_from_model()            │
│    └─ Output: TMR {intent, entities}                               │
│                                                                     │
│ 2. CHECK ACTIONABILITY ★ NEW                                        │
│    ├─ check_actionability()                                        │
│    ├─ Validates: Required parameters present?                      │
│    └─ If fail: Trigger request_info_script()                       │
│                                                                     │
│ 3. DELIBERATION                                                     │
│    ├─ deliberation_query_kg()                                      │
│    ├─ Determine required facets based on intent                    │
│    ├─ Query KNOWLEDGE.PY with facets + filters ★ NEW               │
│    └─ Validate results (time, accessibility, etc.)                 │
│                                                                     │
│ 4. ACTION - RENDERING                                               │
│    ├─ action_render_response()                                     │
│    ├─ Format results using facet information ★ ENHANCED            │
│    └─ Return rendered response or clarification                    │
│                                                                     │
│ 5. FINAL RESPONSE                                                   │
│    ├─ produce_final_response()                                     │
│    ├─ Polish with LLM if needed                                    │
│    └─ Enforce Telegram limits (4096 chars)                         │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ KNOWLEDGE.PY - Faceted KG Access ★ ENHANCED                         │
│                                                                     │
│ query_by_facet(facet)                                              │
│ query_by_facets([facet1, facet2])                                  │
│ find_by_facet_and_filters(facets, filters) ★ NEW                   │
│ find_by_filters(filters)                                           │
│ get_entity_by_id(id)                                               │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ KNOWLEDGE GRAPH (data/knowledge_graph.json)                         │
│                                                                     │
│ Faceted Entities:                                                   │
│ - Place facet:          {location, coordinates}                    │
│ - Service facet:        {cuisine, hours, pricing}                  │
│ - Building facet:       {amenities, parking}                       │
│ - Accessibility facet:  {wheelchair, elevators}                    │
│ - Event_Host facet:     {events, schedule}                         │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ GEMINI LLM (for response polishing)                                  │
│ (Only used in LLM_ONLY, LLM_FALLBACK, or response polishing)       │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ MAIN.PY - Response Sender                                           │
│ (Formats and sends back to Telegram)                                │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ TELEGRAM                                                            │
│ (User receives response)                                            │
└─────────────────────────────────────────────────────────────────────┘

★ = New or Enhanced Component
""")

print("\n" + "="*80)
print("All examples completed")
print("="*80)
