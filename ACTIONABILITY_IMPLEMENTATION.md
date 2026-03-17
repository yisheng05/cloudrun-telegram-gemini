# Actionability & Mixed-Initiative Dialog Implementation

## Overview

This document describes the implementation of two critical features for an intelligent conversational tourism agent:

1. **Actionability Checking** - Validates whether the agent has sufficient information to execute a query
2. **Mixed-Initiative Dialog** - Engages users in clarification when critical parameters are missing
3. **Faceted Knowledge Graph** - Enables nuanced multi-dimensional queries

---

## 1. Actionability Checking

### Concept

"Actionability" is the agent's ability to judge whether it understands a particular input sufficiently to act. Before querying the knowledge graph, the agent must validate that all **critical parameters** are present.

### Implementation

Located in `middleware.py`, the `CHECK_ACTIONABILITY` function validates intent and entities against predefined script requirements.

#### Script Requirements Definition

```python
SCRIPT_REQUIREMENTS = {
    "dining": {
        "required": ["cuisine_or_location"],  # At least one must be present
        "optional": ["time", "party_size", "accessibility", "price_range"],
        "critical_message": "To help you find a restaurant..."
    },
    "booking": {
        "required": ["accommodation_type"],
        "optional": ["check_in_date", "check_out_date", "guests"],
        "critical_message": "To help you book..."
    },
    "event": {
        "required": ["event_type"],
        "optional": ["date", "location", "time"],
        "critical_message": "To find events..."
    }
}
```

#### Actionability Algorithm

```
1. Map user intent to script (e.g., "inform" → "dining_script")
2. Retrieve required parameters for that script
3. Check if all required parameters exist in the TMR (Text Meaning Representation)
4. If missing: Return (False, clarification_message)
5. If present: Return (True, None) and proceed with query
```

#### Key Feature: Composite Requirements

Some requirements are composite with "or" semantics:

```python
"required": ["cuisine_or_location"]  # Either cuisine OR location is acceptable
```

The check validates this:
```python
if "_or_" in req:
    alternatives = req.split("_or_")
    has_required = any(alt in entities and entities[alt] is not None for alt in alternatives)
```

### Example Flows

**Example 1: Actionability Failure**
```
User: "Book me a table"
↓
Intent: "booking"
Entities: {} (empty)
↓
CHECK_ACTIONABILITY(booking, {})
→ "accommodation_type" is missing
→ Actionable: False
↓
Clarification: "To help you find accommodation, could you tell me what type 
of place you're looking for and your travel dates?"
```

**Example 2: Actionability Success**
```
User: "Find Italian restaurants"
↓
Intent: "inform" (dining)
Entities: {"servesCuisine": "Italian", "cuisine_or_location": "Italian"}
↓
CHECK_ACTIONABILITY(inform, entities)
→ "cuisine_or_location" is present ✓
→ Actionable: True
↓
Proceed to Knowledge Graph query
```

---

## 2. Mixed-Initiative Dialog (REQUEST_INFO_SCRIPT)

### Concept

When actionability fails, the agent doesn't attempt the query. Instead, it triggers a **Clarification Script** that explicitly asks the user for missing critical information.

This implements **Mixed-Initiative Learning**: the system and user collaborate to gather sufficient context.

### Implementation

The `REQUEST_INFO_SCRIPT` function generates natural language clarification requests:

```python
def request_info_script(
    script_name: str,
    missing_params: list,
    script_def: Dict[str, Any]
) -> str:
    """Generate a clarification request for missing parameters."""
```

#### Script-Specific Clarifications

For **dining scripts**, it maps missing parameters to friendly questions:

```python
param_to_question = {
    "cuisine_or_location": "the cuisine type or location",
    "time": "what time you'd like to dine",
    "party_size": "how many people",
    "accessibility": "your accessibility requirements",
    "price_range": "your preferred price range"
}
```

Result: `"I'd love to help you find a restaurant! Could you tell me [missing params]?"`

#### Metric Tracking

When actionability fails, the system increments a metric:
```python
metrics.inc('actionability_failures')
```

This allows monitoring how often the agent needs clarifications.

---

## 3. Faceted Knowledge Graph

### Concept

A **faceted hierarchy** allows entities to inherit properties from multiple conceptual dimensions:

- **Place facet**: Location, coordinates, accessibility
- **Service facet**: Service type, hours, pricing, cuisine
- **Event_Host facet**: Events hosted, schedules
- **Building facet**: Amenities, parking, wifi
- **Accessibility facet**: Wheelchair access, braille, etc.

This enables **nuanced multi-dimensional queries** like:
> "Find a place that serves dinner (Service) AND has wheelchair access (Accessibility) AND is hosting a jazz night (Event_Host)"

### Schema Structure

Each entity now includes:

```json
{
  "id": "rest1",
  "class": "Restaurant",
  "facets": ["Place", "Service", "Building", "Accessibility"],
  "properties": {
    "servesCuisine": "Italian",
    "locatedIn": "Marina Bay",
    "wheelchairAccessible": true,
    "openingHours": "11:00-22:00",
    ...
  }
}
```

### Facet-Aware Querying Functions

**knowledge.py** provides new querying capabilities:

#### 1. Single Facet Query
```python
query_by_facet("Accessibility") 
→ [entities with Accessibility facet]
```

#### 2. Multi-Facet Query (Intersection)
```python
query_by_facets(["Place", "Service", "Accessibility"])
→ [entities that have ALL three facets]
```

#### 3. Faceted Query with Filters
```python
find_by_facet_and_filters(
    required_facets=["Place", "Service", "Accessibility"],
    filters={
        "servesCuisine": "Italian",
        "wheelchairAccessible": True
    }
)
→ [Italian restaurants with wheelchair access]
```

### Deliberation Enhancement

The `deliberation_query_kg` function now:

1. **Checks actionability** before querying
2. **Determines required facets** based on intent:
   - Dining intent → `["Place", "Service"]` + optionally `["Accessibility"]`
   - Event intent → `["Event_Host", "Place"]`
3. **Performs faceted queries** using the KG
4. **Validates results** against additional constraints (time, accessibility)

```python
# Example: Dining query with accessibility
required_facets = ["Place", "Service", "Accessibility"]
filters = {
    "servesCuisine": "Italian",
    "wheelchairAccessible": True
}
results = knowledge.find_by_facet_and_filters(required_facets, filters)
```

---

## 4. Unified Pipeline: Perception → Deliberation → Action

### Flow Diagram

```
USER INPUT
   ↓
PERCEPTION_SIMULATE (extract TMR: intent + entities)
   ↓
CHECK_ACTIONABILITY (validate critical params)
   ├─ Actionable: False
   │  ↓
   │  REQUEST_INFO_SCRIPT (generate clarification)
   │  ↓
   │  RETURN CLARIFICATION MESSAGE
   │
   └─ Actionable: True
      ↓
      DELIBERATION_QUERY_KG (determine facets, query KG)
      ├─ No results
      │  ↓
      │  mode = "LLM_FALLBACK"
      │
      └─ Results found
         ↓
         mode = "KG_DRIVEN" + verified results
      ↓
      ACTION_RENDER_RESPONSE (format results)
         ├─ Clarification mode → return clarification msg
         ├─ LLM mode → prepare for model
         └─ KG mode → format verified results
      ↓
      PRODUCE_FINAL_RESPONSE (polish with model if needed)
      ↓
      RETURN TO USER
```

### Mode Definitions

| Mode | Trigger | Action |
|------|---------|--------|
| `CLARIFICATION_NEEDED` | Actionability fails | Return clarification message |
| `LLM_ONLY` | Chat/general_knowledge intent | Use model for response |
| `LLM_FALLBACK` | Actionable but no KG results | Use model with context |
| `KG_DRIVEN` | Actionable + KG results found | Render verified results |

---

## 5. Response Rendering with Facet Awareness

### Basic Rendering (KG_DRIVEN mode)

```
User: "Find Italian restaurants in Marina Bay"

Results:
  → Saizeriya (Italian, Marina Bay, Low price, Wheelchair accessible)
  → Jazzroom Dinner Club (French, Marina Bay, High price, Wheelchair accessible, hosts jazz nights)

Rendered:
  "Here are some options I found for you:
   - Saizeriya: Italian, in Marina Bay, (Low price), ✓ wheelchair accessible
   - Jazzroom Dinner Club: French, in Marina Bay, (High price), ✓ wheelchair accessible, hosts jazz_night"
```

### Enhanced Rendering (Facet-Aware)

The response leverages facet information to provide richer descriptions:

```python
# For each entity:
desc_parts = []

if "Service" in facets:
    desc_parts.append(f"{cuisine}")  # From Service facet

if "Building" in facets:
    desc_parts.append(f"in {location}")  # From Building facet
    desc_parts.append(f"hours: {openingHours}")

if "Accessibility" in facets:
    if wheelchairAccessible:
        desc_parts.append("✓ wheelchair accessible")

if "Event_Host" in facets:
    events = hostingEvents
    desc_parts.append(f"hosts {events}")
```

---

## 6. Testing

A comprehensive test suite is provided in `test_actionability.py`:

### Test 1: Actionability Checking
- Vague queries (actionability fails)
- Specific queries (actionability succeeds)
- Chat/general knowledge (always actionable)

### Test 2: Faceted Querying
- Query by single facet
- Query by facet intersection
- Query by facets + filters

### Test 3: End-to-End Pipeline
- Clarification flow
- KG-driven results
- LLM fallback

### Test 4: Facet-Aware Rendering
- Rich entity descriptions
- Multiple facet visualization

**Run tests:**
```bash
python test_actionability.py
```

---

## 7. Key Metrics

The system tracks important metrics:

```python
metrics.inc('actionability_failures')      # User provided insufficient info
metrics.inc('actionability_success')       # Clear, actionable query
metrics.inc('tmr_failures')                # TMR extraction failed
metrics.inc('final_response_failures')     # Response generation failed
```

---

## 8. Benefits

### For Users
- **Clarification when confused**: Instead of guessing, ask for specifics
- **Nuanced search**: Can express multi-faceted requirements
- **Rich results**: Responses highlight relevant facet features

### For System
- **Semantic clarity**: Explicit validation before acting
- **Reduced errors**: Won't attempt invalid queries
- **Extensible**: New facets can be added for new domains
- **Monitorable**: Track actionability patterns

---

## 9. Example Conversations

### Example 1: Vague Request → Clarification

```
User: "Book me a table"
Agent: "To help you find accommodation, could you tell me what type of 
place you're looking for and your travel dates?"

User: "Italian restaurant, tomorrow at 7 PM, for 2 people"
Agent: [Actionable] "Searching for Italian restaurants..."
Agent: "Here are some options:
  - Saizeriya (Italian, Marina Bay, Low price, Wheelchair accessible)
  - Jazzroom Dinner Club (French, Marina Bay, High price, Wheelchair accessible, 
    hosts jazz nights)"
```

### Example 2: Multi-Facet Query

```
User: "I need a wheelchair-accessible restaurant with Italian food 
and I want to see live jazz"

Entity Processing:
  - Required facets: Place, Service, Accessibility, Event_Host
  - Filters: servesCuisine=Italian, wheelchairAccessible=True
  - Result: Jazzroom Dinner Club (matches all criteria)

Agent: "Perfect! Jazzroom Dinner Club serves French cuisine, has wheelchair 
access, and hosts jazz nights daily from 8 PM to 11 PM. It's located in 
Marina Bay and has a high-end price range."
```

### Example 3: Chat vs. Dining

```
User: "Hi, how are you?"
Agent: [Actionable without parameters - chat intent]
Agent: "Hello! I'm doing great. I'm here to help you find restaurants, 
events, and activities in Singapore. What can I help you with?"

User: "What was the weather like yesterday?"
Agent: [Actionable without parameters - general_knowledge intent]
Agent: [Uses LLM for general knowledge response]
```

---

## 10. Future Enhancements

- **Dynamic facet composition**: Allow runtime facet definition
- **Facet weights**: Prioritize certain facets in ranking
- **Temporal facets**: Handle time-dependent properties
- **Cross-domain faceting**: Share facet definitions across domains
- **User preference learning**: Remember user facet preferences
- **Contextual faceting**: Adapt facets based on conversation history

---

## Files Modified

- `middleware.py`: Added actionability checking, clarification scripts, facet-aware deliberation
- `knowledge.py`: Added facet querying functions
- `data/knowledge_graph.json`: Restructured with faceted entities
- `test_actionability.py`: Comprehensive test suite (new file)

---

## References

- **Actionability Principle**: "An intelligent agent must mimic the human ability to judge whether they understand a particular input sufficiently to act"
- **Mixed-Initiative Learning**: System and user collaborate to gather context
- **Faceted Classification**: Entities inherit from multiple conceptual dimensions
- **Tourism Domain**: Specialized for travel, dining, and event discovery

