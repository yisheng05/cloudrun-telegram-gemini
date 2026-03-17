#!/usr/bin/env python3
"""
QUICK REFERENCE: Actionability & Mixed-Initiative Dialog Features

This file demonstrates the key features with practical examples.
"""

from middleware import (
    perception_simulate,
    check_actionability,
    deliberation_query_kg,
)

print("=" * 80)
print("ACTIONABILITY & MIXED-INITIATIVE DIALOG - QUICK REFERENCE")
print("=" * 80)

# ============================================================================
# FEATURE 1: Automatic Clarification for Vague Requests
# ============================================================================
print("\n1. AUTOMATIC CLARIFICATION FOR VAGUE REQUESTS")
print("-" * 80)

test_cases = [
    ("Book me a table", "Too vague - system will ask for clarification"),
    ("Find Italian restaurants", "Actionable - cuisine provided"),
    ("Pizza place near Chinatown", "Actionable - cuisine and location"),
]

for user_input, explanation in test_cases:
    print(f"\nUser: \"{user_input}\"")
    print(f"Status: {explanation}")
    
    tmr = perception_simulate(user_input)
    is_actionable, clarification = check_actionability(tmr.get("intent"), tmr.get("entities"))
    
    if not is_actionable:
        print(f"❌ Not actionable")
        print(f"Clarification: {clarification}")
    else:
        print(f"✓ Actionable - proceeding with query")


# ============================================================================
# FEATURE 2: Multi-Faceted Search Capabilities
# ============================================================================
print("\n\n2. MULTI-FACETED SEARCH CAPABILITIES")
print("-" * 80)

print("\nBefore: Flat restaurant list")
print("  Restaurant = {name, cuisine, location, price}")
print("\nAfter: Multi-faceted entities")
print("  Restaurant = {")
print("    Place facet:          {location, coordinates, ...}")
print("    Service facet:        {cuisine, hours, pricing, meals, ...}")
print("    Building facet:       {parking, wifi, amenities, ...}")
print("    Accessibility facet:  {wheelchair, braille, elevators, ...}")
print("    Event_Host facet:     {events, schedule, capacity, ...}")
print("  }")

print("\nExample query: 'Italian restaurant with wheelchair access and jazz'")
print("  Required facets: Place + Service + Accessibility + Event_Host")
print("  Filters: cuisine=Italian, wheelchairAccessible=True, events=jazz")
print("  Result: Jazzroom Dinner Club ✓")


# ============================================================================
# FEATURE 3: Intent Classification with Actionability Checks
# ============================================================================
print("\n\n3. INTENT CLASSIFICATION WITH ACTIONABILITY")
print("-" * 80)

intents = [
    ("dining", ["cuisine_or_location"], "Need at least cuisine OR location"),
    ("booking", ["accommodation_type"], "Need accommodation type"),
    ("event", ["event_type"], "Need event type (concert, exhibition, etc.)"),
    ("activity", ["activity_type"], "Need activity type"),
    ("chat", [], "No parameters needed"),
    ("general_knowledge", [], "No parameters needed"),
]

print("\nIntent Requirements:")
for intent, required_params, explanation in intents:
    params_str = ", ".join(required_params) if required_params else "(none)"
    print(f"  {intent:20} requires: {params_str}")
    print(f"  {' '*20} → {explanation}")


# ============================================================================
# FEATURE 4: Facet-Aware Response Examples
# ============================================================================
print("\n\n4. FACET-AWARE RESPONSE RENDERING")
print("-" * 80)

print("\nResponse for restaurant with multiple facets:")
print("""
Jazzroom Dinner Club
- French cuisine, Marina Bay (from Place & Service facets)
- Hours: 6 PM - 11 PM (from Service facet)
- ✓ Wheelchair accessible (from Accessibility facet)
- Hosts jazz nights daily 8 PM-11 PM (from Event_Host facet)
- High price range (from Service facet)
""")


# ============================================================================
# FEATURE 5: Deliberation Pipeline
# ============================================================================
print("\n5. DELIBERATION PIPELINE")
print("-" * 80)

print("""
Perception Phase:
  Input: "Book me a table at 7 PM for 2 people"
  Output: TMR {
    intent: "booking",
    entities: {time: "19:00", party_size: 2}
  }

Actionability Phase:
  Check: booking requires ["accommodation_type"]
  Result: ❌ accommodation_type missing
  Action: Trigger REQUEST_INFO_SCRIPT

Clarification:
  Message: "To help you find accommodation, could you tell me what type 
  of place you're looking for and your travel dates?"

(User responds: "I want Italian restaurant")

Deliberation Phase:
  Check: "inform" requires ["cuisine_or_location"]
  Result: ✓ cuisine provided (Italian)
  Action: Query KG with facets [Place, Service]

Knowledge Graph Phase:
  Query: find_by_facet_and_filters(
    facets=["Place", "Service"],
    filters={servesCuisine: "Italian"}
  )
  Result: [Saizeriya, PastaMania, Jazzroom]

Rendering Phase:
  Response: Rich description with all relevant facets
""")


# ============================================================================
# FEATURE 6: Metrics Tracking
# ============================================================================
print("\n\n6. METRICS TRACKING")
print("-" * 80)

print("""
Key Metrics:
  - actionability_failures:    How often users provide vague requests
  - actionability_success:     How often queries are actionable
  - facet_query_count:         Usage of multi-facet queries
  - clarification_triggers:    How often clarification is requested
  
Use these to:
  ✓ Monitor user clarity patterns
  ✓ Identify unclear intents
  ✓ Optimize clarification messages
  ✓ Track feature usage
""")


# ============================================================================
# BENEFIT SUMMARY
# ============================================================================
print("\n\n7. KEY BENEFITS")
print("-" * 80)

benefits = [
    ("User Experience", [
        "Clear clarifications when confused",
        "Multi-faceted search capabilities",
        "Richer, more relevant results"
    ]),
    ("System Quality", [
        "Avoid invalid queries",
        "Explicit semantic validation",
        "Fewer hallucinations"
    ]),
    ("Extensibility", [
        "Add new facets for new domains",
        "Reuse facet infrastructure",
        "Consistent multi-faceted approach"
    ]),
    ("Monitoring", [
        "Track actionability patterns",
        "Identify problematic queries",
        "Optimize disambiguation"
    ])
]

for category, items in benefits:
    print(f"\n{category}:")
    for item in items:
        print(f"  ✓ {item}")


print("\n" + "=" * 80)
print("For more details, see ACTIONABILITY_IMPLEMENTATION.md")
print("For testing, run: python test_actionability.py")
print("=" * 80)
