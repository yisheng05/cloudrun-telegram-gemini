import os
import re
import json
import time
import random
import logging
from typing import Any, Dict, Optional, Tuple

import knowledge
import metrics
import circuit_breaker
import memory
from tools import dynamic_ingest


# ============================================================================
# SCRIPT DEFINITIONS: Define what parameters are required for each intent/action
# ============================================================================

SCRIPT_REQUIREMENTS = {
    "dining": {
        "required": ["servesCuisine_or_locatedIn"],  # At least one to narrow search
        "optional": ["time", "party_size", "accessibility", "price_range"],
        "critical_message": "To help you find a restaurant, I need at least the cuisine type or location. What are you looking for?"
    },
    "booking": {
        "required": ["booking_type"],
        "optional": ["check_in_date", "check_out_date", "guests", "price_range", "destination", "origin"],
        "critical_message": "I can help with booking flights, hotels, or restaurants. What would you like to book?"
    },
    "event": {
        "required": ["event_type"],  # concert, exhibition, etc.
        "optional": ["date", "location", "time"],
        "critical_message": "To find events, could you tell me what type of event you're interested in?"
    },
    "activity": {
        "required": ["activity_type"],
        "optional": ["location", "date", "time", "skill_level", "nature_feature"],
        "critical_message": "What kind of activity are you interested in (sightseeing, sports, cultural, etc.)?"
    },
    "shopping": {
        "required": ["shopping_type"],
        "optional": ["location", "price_range", "item_type"],
        "critical_message": "What kind of shopping are you interested in (malls, markets, boutiques)?"
    },
    "planning": {
        "required": ["planning_intent"], # Generic, usually handled by LLM if complex
        "optional": ["location", "duration", "preferences"],
        "critical_message": "I can help plan your day! What are your interests or preferred location?"
    },
    "query": {
        "required": [],
        "optional": ["locatedIn", "servesCuisine", "price_range"],
        "critical_message": "What are you looking for?"
    }
}


# ============================================================================
# DELIBERATION PHASE: Actionability Checking and Mixed-Initiative Learning
# ============================================================================

def check_actionability(intent: str, entities: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Deliberation function that validates if we have enough critical data to act.
    
    Returns:
        (is_actionable, clarification_message)
        
    Example:
        If user says "Book me a table", but provides no time or party size,
        this returns (False, "For how many people and at what time?")
    """
    # Chat and general knowledge don't need parameters
    if intent in ["chat", "general_knowledge"]:
        return (True, None)
    
    # Get script requirements if they exist
    script_name = intent_to_script_name(intent)
    if script_name not in SCRIPT_REQUIREMENTS:
        # Unknown intent type - allow it and let LLM handle
        return (True, None)
    
    script = SCRIPT_REQUIREMENTS[script_name]
    required_keys = script.get("required", [])
    
    # Check if all required parameters are present
    missing_required = []
    for req in required_keys:
        # Handle composite requirements like "cuisine_or_location"
        if "_or_" in req:
            alternatives = req.split("_or_")
            # Check both the explicit alternative names AND the composite key
            has_required = any(alt in entities and entities[alt] is not None for alt in alternatives)
            # For dining, also accept cuisine_or_location directly
            if not has_required and req in entities and entities[req] is not None:
                has_required = True
            if not has_required:
                missing_required.append(req)
        else:
            if req not in entities or entities[req] is None:
                missing_required.append(req)
    
    if missing_required:
        # Not actionable - generate clarification request
        clarification = request_info_script(script_name, missing_required, script)
        return (False, clarification)
    
    # All required parameters present
    return (True, None)


def intent_to_script_name(intent: str) -> str:
    """Map generic intents to specific scripts."""
    mapping = {
        "inform": "query",
        "booking": "booking",
        "event": "event",
        "activity": "activity",
        "query": "query",
        "shopping": "shopping",
        "planning": "planning",
    }
    return mapping.get(intent, intent)


def request_info_script(
    script_name: str,
    missing_params: list,
    script_def: Dict[str, Any]
) -> str:
    """Mixed-Initiative Learning: Generate a clarification request for missing parameters.
    
    This script triggers when actionability check fails, asking the user
    for the specific missing parameters needed to proceed.
    """
    critical_msg = script_def.get("critical_message", "I need more information to help you.")
    
    if not missing_params:
        return critical_msg
    
    # Build a natural language request for missing info
    if script_name == "dining":
        missing_info = []
        param_to_question = {
            "servesCuisine_or_locatedIn": "the cuisine type or location",
            "time": "what time you'd like to dine",
            "party_size": "how many people",
            "accessibility": "your accessibility requirements",
            "price_range": "your preferred price range"
        }
        for param in missing_params:
            if param in param_to_question:
                missing_info.append(param_to_question[param])
        
        if missing_info:
            return f"I'd love to help you find a restaurant! Could you tell me {' and '.join(missing_info)}?"
    
    elif script_name == "booking":
        return "I can help with booking flights, hotels, or restaurants. What would you like to book?"
    
    elif script_name == "event":
        return "What type of event are you interested in? (e.g., concert, art exhibition, festival, sports)"
    
    elif script_name == "activity":
        return "What kind of activity interests you? (e.g., sightseeing tour, water sports, cultural experience)"

    elif script_name == "shopping":
        return "Are you looking for a specific type of shopping? (e.g., luxury malls, local markets)"

    elif script_name == "planning":
        return "I can help plan your itinerary! What kind of places do you like? (e.g., nature, shopping, museums)"
    
    # Default fallback
    return critical_msg


def perception_simulate(text: str) -> Dict[str, Any]:
    # Very small heuristic extractor for demo purposes
    text_l = text.lower()
    tmr = {"intent": "inform", "entities": {}}
    
    # Determine intent - check for chat/general_knowledge FIRST
    if any(x in text_l for x in ["hello", "hi", "hey", "thanks", "thank you", "who are you", "what's your name", "how are you", "good morning", "good night"]):
        tmr["intent"] = "chat"
        return tmr
    
    # Location detection
    found_location = False
    for location in ["marina bay", "marina", "chinatown", "clarke quay", "bras basah", "orchard", "sentosa", "harbourfront", "central", "kazakhstan", "mercury", "marine parade", "pasir ris", "mandai", "river valley", "singapore river", "serangoon", "rochor"]:
        if location in text_l:
            found_location = True
            if location in ["kazakhstan", "mercury"]:
                tmr["entities"]["destination"] = location.title()
                tmr["entities"]["locatedIn"] = location.title() 
            else:
                tmr["entities"]["locatedIn"] = location.title()
                tmr["entities"]["servesCuisine_or_locatedIn"] = location.title()
            break

    # Check for ontology classes
    if any(x in text_l for x in ["restaurant", "food", "eat", "dinner", "lunch", "breakfast", "cafe", "dining"]):
        tmr["class"] = "Restaurant"
        tmr["intent"] = "inform"
    elif any(x in text_l for x in ["museum", "art gallery", "exhibition"]):
        tmr["class"] = "Attraction"
        tmr["intent"] = "inform"
        tmr["entities"]["attraction_type"] = "Museum"
    elif any(x in text_l for x in ["attraction", "place", "see", "visit", "tourist"]):
        tmr["class"] = "Attraction"
        tmr["intent"] = "inform"

    # Children's menu detection
    if "children" in text_l or "kids" in text_l or "child" in text_l:
        tmr["entities"]["childrensMenu"] = True
    
    # Check for general knowledge questions - ONLY if no domain keywords found
    if not found_location and not tmr.get("class") and any(x in text_l for x in ["what", "when", "where", "why", "how", "who", "which", "tell me about", "explain", "won the", "is", "are"]):
        if not any(x in text_l for x in ["book", "reserve", "hotel", "event", "activity", "show", "concert", "shopping", "mall", "market", "shop", "park", "nature", "garden", "hike"]):
            tmr["intent"] = "general_knowledge"
            return tmr

    # Establishment name detection (Specific for our new nodes)
    if "jumbo" in text_l:
        tmr["entities"]["name"] = "Jumbo Seafood"
        tmr["class"] = "Restaurant"
    if "suki-ya" in text_l or "sukiya" in text_l:
        tmr["entities"]["name"] = "Suki-ya"
        tmr["class"] = "Restaurant"
    
    # Time detection (HH:MM or meal keywords)
    m = re.search(r"\b([01]?\d|2[0-3]):[0-5]\d\b", text_l)
    if m:
        tmr["entities"]["time"] = m.group(0)
    else:
        if "breakfast" in text_l:
            tmr["entities"]["mealType"] = "breakfast"
            tmr["entities"]["time"] = "08:00"
        elif "lunch" in text_l:
            tmr["entities"]["mealType"] = "lunch"
            tmr["entities"]["time"] = "12:00"
        elif "dinner" in text_l:
            tmr["entities"]["mealType"] = "dinner"
            tmr["entities"]["time"] = "19:00"
    
    # Party size detection
    party_match = re.search(r"\b(\d+)\s*(?:people|person|guests?|of us)\b", text_l)
    if party_match:
        tmr["entities"]["party_size"] = int(party_match.group(1))
    
    # Accessibility detection
    if "wheelchair" in text_l or "accessible" in text_l or "disability" in text_l or "mobility" in text_l:
        tmr["entities"]["wheelchairAccessible"] = True
        tmr["entities"]["accessibility"] = "wheelchair_accessible"
    
    # Price range detection
    if "cheap" in text_l or "budget" in text_l or "inexpensive" in text_l or "low price" in text_l:
        tmr["entities"]["price_range"] = "Low"
    elif "expensive" in text_l or "high end" in text_l or "luxury" in text_l or "upscale" in text_l:
        tmr["entities"]["price_range"] = "High"
    elif "medium" in text_l or "moderate" in text_l or "mid" in text_l:
        tmr["entities"]["price_range"] = "Medium"
    
    # Event detection
    if "jazz" in text_l or "music" in text_l or "concert" in text_l:
        tmr["entities"]["event_type"] = "jazz_night" if "jazz" in text_l else "concert"
    if "light show" in text_l or "show" in text_l:
        tmr["entities"]["event_type"] = "light_show"
    if "exhibition" in text_l or "art" in text_l or "museum" in text_l:
        tmr["entities"]["event_type"] = "art_exhibition"

    # Sightseeing detection
    if "sightseeing" in text_l or "tour" in text_l:
        tmr["intent"] = "activity"
        tmr["entities"]["activity_type"] = "sightseeing"

    # Shopping detection
    if "shop" in text_l or "mall" in text_l or "buy" in text_l or "market" in text_l:
        tmr["intent"] = "shopping"
        tmr["class"] = "ShoppingMall"
        if "mall" in text_l:
            tmr["entities"]["shopping_type"] = "Mall"
        elif "market" in text_l:
            tmr["entities"]["shopping_type"] = "Market"
        else:
             tmr["entities"]["shopping_type"] = "General" 

    # Nature/Park detection
    if "park" in text_l or "nature" in text_l or "garden" in text_l or "hike" in text_l:
        tmr["intent"] = "activity"
        tmr["class"] = "NaturePark"
        tmr["entities"]["activity_type"] = "Nature"
        tmr["entities"]["nature_feature"] = True

    return tmr


def build_tmr_prompt(user_text: str) -> str:
    examples = (
        "User: I want cheap Italian food for kids near Marina Bay\nTMR: {\"intent\": \"inform\", \"class\": \"Restaurant\", \"entities\": {\"servesCuisine\": \"Italian\", \"locatedIn\": \"Marina Bay\", \"price_range\": \"Low\", \"childrensMenu\": true}}\n",
        "User: Find me a wheelchair accessible hotel\nTMR: {\"intent\": \"booking\", \"class\": \"Hotel\", \"entities\": {\"booking_type\": \"Hotel\", \"wheelchairAccessible\": true}}\n",
        "User: Who are you?\nTMR: {\"intent\": \"chat\", \"entities\": {}}\n",
    )
    prompt = (
        "Extract a concise Text Meaning Representation (TMR) from the user's message.\n"
        "Output only a single JSON object with keys: intent (string), class (string, optional), entities (object).\n"
        "Intents: 'inform', 'booking', 'chat', 'general_knowledge', 'shopping', 'activity'.\n"
        "Classes: 'Restaurant', 'Hotel', 'NaturePark', 'ShoppingMall'.\n"
        "Entities keys: 'servesCuisine', 'locatedIn', 'price_range', 'childrensMenu', 'wheelchairAccessible', 'booking_type', 'destination'.\n"
        "Respond with valid JSON only.\n\n"
        f"{''.join(examples)}"
        f"User: {user_text}\nTMR:"
    )
    return prompt


def extract_json(text: str) -> Optional[str]:
    # Attempt to extract the first JSON object from text by scanning braces
    if not text:
        return None
    start = text.find('{')
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    return None


def request_tmr_from_model(call_gemini_fn: Any, user_text: str, max_retries: int = 3, base_delay: float = 1.0) -> Dict[str, Any]:
    prompt = build_tmr_prompt(user_text)

    # Circuit breaker: if open, skip model requests and fall back
    if circuit_breaker.is_open():
        logging.warning("Circuit breaker open for TMR requests; using local perception")
        metrics.inc('tmr_circuit_open')
        return perception_simulate(user_text)

    for attempt in range(1, max_retries + 1):
        try:
            raw = call_gemini_fn(prompt)
            if not raw:
                raise ValueError("empty response from model")

            # Try parsing as JSON directly
            try:
                parsed = json.loads(raw)
                circuit_breaker.record_success()
                return parsed
            except Exception:
                pass

            # Try to extract JSON substring
            j = extract_json(raw)
            if j:
                try:
                    parsed = json.loads(j)
                    circuit_breaker.record_success()
                    return parsed
                except Exception:
                    logging.exception("Failed to parse extracted JSON from model TMR output")

            # If we reach here, parsing failed
            raise ValueError("failed to parse TMR JSON from model output")

        except Exception as e:
            metrics.inc('tmr_failures')
            circuit_breaker.record_failure()
            if attempt >= max_retries:
                logging.exception("TMR request failed after %s attempts: %s", attempt, str(e))
                logging.warning("Falling back to local perception_simulate() for TMR")
                metrics.inc('tmr_fallbacks')
                return perception_simulate(user_text)

            # Exponential backoff with jitter
            sleep = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            logging.warning("TMR request attempt %s failed: %s. Retrying after %.2fs", attempt, str(e), sleep)
            time.sleep(sleep)
    
    # Final fallback if loop exhausted (should not happen due to max_retries logic)
    return perception_simulate(user_text)


def deliberation_query_kg(tmr: Dict[str, Any]) -> Dict[str, Any]:
    intent = tmr.get("intent", "inform")
    entities = tmr.get("entities", {})
    target_class = tmr.get("class") # NEW: Specific ontology class like Restaurant

    # Phase 1: Dual-Path check - does this need KG at all?
    if intent in ["chat", "general_knowledge"]:
        return {"verified": [], "filters": {}, "filtered_out": [], "tmr": tmr, "mode": "LLM_ONLY"}

    # Phase 2: DELIBERATION - CHECK ACTIONABILITY
    is_actionable, clarification = check_actionability(intent, entities)
    
    # PROACTIVE LOGIC: Even if not fully 'actionable' (missing mandatory fields),
    # we proceed if we have enough info to show *something* (class or location).
    has_minimal_info = bool(target_class or entities.get("locatedIn") or entities.get("servesCuisine"))

    if not is_actionable and not has_minimal_info:
        metrics.inc('actionability_failures')
        return {
            "verified": [], "filters": {}, "filtered_out": [], "tmr": tmr,
            "mode": "CLARIFICATION_NEEDED", "clarification_message": clarification
        }
    
    # Phase 3: Build ontology-driven query parameters
    filters = {}
    required_facets = []
    
    # Map intent/entities to facets and classes
    if target_class == "Restaurant" or intent == "inform":
        # Default to Restaurant if intent is inform and no class specified
        if not target_class:
            target_class = "Restaurant"
        
        if target_class == "Restaurant":
            required_facets = ["TourismService"]
            if "servesCuisine" in entities:
                filters["servesCuisine"] = entities["servesCuisine"]
            if "childrensMenu" in entities:
                filters["childrensMenu"] = entities["childrensMenu"]
                required_facets.append("ActivityFeature")
    
    if target_class == "Attraction":
        required_facets = ["Place"]
        if "attraction_type" in entities:
            filters["attraction_type"] = entities["attraction_type"]

    if target_class == "NaturePark":
        required_facets = ["Place"]
        if "activity_type" in entities:
            filters["activity_type"] = entities["activity_type"]

    if "locatedIn" in entities:
        filters["locatedIn"] = entities["locatedIn"]
    if "price_range" in entities:
        filters["hasPriceRange"] = entities["price_range"]
    if "accessibility" in entities or "wheelchairAccessible" in entities:
        required_facets.append("Accessibility")
        if "wheelchairAccessible" in entities:
            filters["wheelchairAccessible"] = entities["wheelchairAccessible"]

    # Use the new ontology-driven query engine
    try:
        candidates = knowledge.query_by_ontology(
            target_class=target_class,
            facets=required_facets,
            properties=filters
        )
    except Exception as e:
        logging.error(f"Ontology query failed: {e}")
        candidates = knowledge.find_by_filters(filters)

    # Phase 4: Validation layer - filter candidates by time constraints
    desired_time = entities.get("time") or entities.get("when")
    
    def run_validation(nodes):
        v, f = [], []
        for c in nodes:
            if desired_time:
                oh = c.get("properties", {}).get("openingHours")
                if not is_open_at(oh, desired_time):
                    f.append({"node": c, "reason": "closed_at_requested_time"})
                    continue
            v.append(c)
        return v, f

    verified, filtered_out = run_validation(candidates)

    # DYNAMIC INGESTION HOOK: If no results but we have a location, 
    # try to fetch real-time data on demand.
    dynamic_update_happened = False
    if not verified and entities.get("locatedIn") and intent != "chat":
        logging.info(f"KG miss for {entities.get('locatedIn')}. Triggering dynamic ingestion...")
        try:
            added = dynamic_ingest.run_dynamic_ingestion(entities["locatedIn"], target_class or "Restaurant")
            if added > 0:
                dynamic_update_happened = True
                # Re-query after ingestion
                candidates = knowledge.query_by_ontology(
                    target_class=target_class,
                    facets=required_facets,
                    properties=filters
                )
                verified, filtered_out = run_validation(candidates)
        except Exception as e:
            logging.error(f"Dynamic Ingestion failed: {e}")

    # Phase 5: Determine response mode
    if verified:
        mode = "KG_DRIVEN"
    elif not is_actionable:
        # No results AND not actionable -> hard block
        mode = "CLARIFICATION_NEEDED"
    else:
        mode = "LLM_FALLBACK"
    
    return {
        "verified": verified, "filters": filters, "filtered_out": filtered_out,
        "tmr": tmr, "mode": mode, "required_facets": required_facets,
        "is_actionable": is_actionable,
        "clarification_message": clarification,
        "dynamic_update_happened": dynamic_update_happened
    }


def action_render_response(verified: Dict[str, Any], original_text: str) -> str:
    mode = verified.get("mode")
    
    # Handle clarification mode (Mixed-Initiative)
    if mode == "CLARIFICATION_NEEDED":
        clarification_msg = verified.get("clarification_message", "I need a bit more information to help you best.")
        logging.info(f"Returning clarification message: {clarification_msg}")
        return clarification_msg
    
    if mode == "LLM_ONLY" or mode == "LLM_FALLBACK":
        return "USE_MODEL_DIRECTLY" # Sentinel for produce_final_response

    # Faceted query insights
    tmr = verified.get("tmr", {})
    intent = tmr.get("intent")
    entities = tmr.get("entities", {})
    target_class = tmr.get("class")

    items = verified.get("verified", [])
    if not items:
        if intent == "booking":
            btype = entities.get("booking_type", "accommodation")
            dest = entities.get("destination", "that location")
            return f"I couldn't find any available {btype.lower()}s for {dest}. I may not have that information in my database."
        return f"I'm sorry, I couldn't find any {target_class or 'places'} matching your specific criteria in my database."

    lines = ["Here are some options from my Tourism Knowledge Graph:"]
    for n in items:
        name = n.get("name")
        props = n.get("properties", {})
        loc = props.get("locatedIn")
        cuisine = props.get("servesCuisine")
        
        desc_parts = []
        if cuisine:
            desc_parts.append(cuisine)
        if loc:
            desc_parts.append(f"in {loc}")
        if props.get("childrensMenu"):
            desc_parts.append("✓ children's menu")
        if props.get("wheelchairAccessible"):
            desc_parts.append("✓ wheelchair accessible")
        
        description = ", ".join(desc_parts)
        lines.append(f"- {name}: {description}")

    return "\n".join(lines)


def produce_final_response(call_gemini_fn: Any, verified: Dict[str, Any], user_text: str) -> str:
    """Given verified facts, ask the model to produce a concise, polished reply.

    Falls back to `action_render_response` if the model is unavailable or returns unparsable output.
    """
    mode = verified.get("mode")
    
    # Handle clarification mode early (don't use model, return direct message)
    if mode == "CLARIFICATION_NEEDED":
        return verified.get("clarification_message", "I need a bit more information.")
    
    # Path A: LLM Knowledge (General or Fallback)
    if mode in ["LLM_ONLY", "LLM_FALLBACK"]:
        prompt = (
            f"You are a helpful travel assistant. The user asked: {user_text}\n"
            "Answer the user naturally based on your knowledge. "
            "Be helpful, polite, and concise. "
            "If you are unsure or the information is not generally known, say 'I don't have that information'. "
            "Do NOT use markdown. Keep it under 3500 characters."
        )
        try:
            raw = call_gemini_fn(prompt)
            if not raw:
                raise ValueError("empty response")
            return raw.strip().replace("**", "").replace("*", "")
        except Exception:
            logging.exception("LLM response generation failed")
            return "I'm sorry, I'm having trouble answering that right now."

    # Path B: KG Facts Rendering
    facts = verified.get("verified", [])
    facts_lines = []
    for n in facts:
        props = n.get("properties", {})
        
        # Build rich fact representation using ontology awareness
        facts_parts = [f"Name: {n.get('name')}"]
        facts_parts.append(f"Class: {n.get('class')}")
        
        if props.get('servesCuisine'):
            facts_parts.append(f"Cuisine: {props.get('servesCuisine')}")
        if props.get('locatedIn'):
            facts_parts.append(f"Location: {props.get('locatedIn')}")
        if props.get('childrensMenu'):
            facts_parts.append("Features: Children's Menu")
        if props.get('wheelchairAccessible'):
            facts_parts.append("Accessibility: Wheelchair Accessible")
        
        facts_lines.append(" | ".join(facts_parts))

    facts_blob = "\n".join(facts_lines)
    is_actionable = verified.get("is_actionable", True)
    clarification = verified.get("clarification_message")
    dynamic_update = verified.get("dynamic_update_happened", False)

    dynamic_note = ""
    if dynamic_update:
        dynamic_note = "[SYSTEM NOTE: I have just updated my database with real-time information from OpenStreetMap and OneMap for this area. Mention this once naturally in your reply.]\n\n"

    if not is_actionable and clarification:
        # PROACTIVE PROMPT: Show results AND ask the missing info
        prompt = (
            f"You are a helpful tourism concierge. The user asked: {user_text}\n\n"
            f"{dynamic_note}"
            "I found some initial options for them based on verified facts, but I need more info to give a perfect answer.\n"
            f"REQUIRED CLARIFICATION: {clarification}\n\n"
            "Below are some VERIFIED facts from our Knowledge Graph. "
            "1. Show these options to the user politely.\n"
            "2. THEN, ask the REQUIRED CLARIFICATION at the end of your response to help narrow it down.\n"
            "Do NOT invent facts. Keep the reply under 3500 characters.\n\n"
            f"VERIFIED_FACTS:\n{facts_blob}\n\nReply:"
        )
    else:
        prompt = (
            f"You are a helpful tourism concierge. The user asked: {user_text}\n\n"
            f"{dynamic_note}"
            "Below are VERIFIED facts from our Tourism Domain Knowledge Graph. "
            "Use ONLY these facts to create a concise, polished reply. "
            "Highlight specific features like children's menus or accessibility if requested. "
            "Do NOT use markdown. Keep the reply under 3500 characters.\n\n"
            f"VERIFIED_FACTS:\n{facts_blob}\n\nReply:"
        )

    try:
        raw = call_gemini_fn(prompt)
        if not raw:
            return action_render_response(verified, user_text)
        reply = raw.strip()
    except Exception:
        metrics.inc('final_response_failures')
        return action_render_response(verified, user_text)

    return reply.replace("**", "").replace("*", "")



def handle_request(call_gemini_fn: Optional[Any], text: str, chat_id: int) -> str:
    """Perception -> Memory Update -> Deliberation -> Action pipeline.
    """
    use_tmr = os.getenv("USE_TMR", "false").lower() in ("1", "true", "yes")

    # 1. Memory: Get session
    session = memory.session_manager.get_session(chat_id)
    
    # Handle reset command
    if text.lower() in ["/start", "reset", "clear"]:
        session.clear()
        return "I've reset our conversation. How can I help you today?"

    # 2. Perception: Extract TMR from current text
    if use_tmr and call_gemini_fn:
        tmr = request_tmr_from_model(call_gemini_fn, text)
    else:
        tmr = perception_simulate(text)

    # 3. Memory Update: Consolidate current TMR into Situation Model
    session.update(tmr, text)
    consolidated_tmr = session.to_dict()

    # 4. Deliberation: Query KG based on CONSOLIDATED state
    deliberation = deliberation_query_kg(consolidated_tmr)

    # 5. Action Rendering
    if use_tmr and call_gemini_fn:
        reply = produce_final_response(call_gemini_fn, deliberation, text)
    else:
        reply = action_render_response(deliberation, text)
    
    # Update history with bot response
    session.history.append({"role": "assistant", "content": reply})
    
    return reply


if __name__ == "__main__":
    print(handle_request(None, "Find Italian restaurants in Marina Bay", 12345))
