import os
import json
from middleware import handle_request
import memory

# Mock Gemini
def mock_call_gemini(prompt):
    return "I found some places for you."

# Ensure TMR is disabled for this logic test to use perception_simulate
os.environ["USE_TMR"] = "false"

def test_mandai_scenario():
    chat_id = 888
    memory.session_manager.clear_session(chat_id)
    
    print("\n--- [TEST: Memory Turn 1] ---")
    print("User: Are there wheel chair accessible attractions near Mandai?")
    resp1 = handle_request(mock_call_gemini, "Are there wheel chair accessible attractions near Mandai?", chat_id)
    session = memory.session_manager.get_session(chat_id)
    print(f"Bot: {resp1}")
    print(f"State after Turn 1: {session.to_dict()}")
    
    # Assertions
    assert session.entities.get("locatedIn") == "Mandai"
    assert session.entities.get("wheelchairAccessible") == True

    print("\n--- [TEST: Memory Turn 2] ---")
    print("User: Sightseeing tour")
    # This should now KEEP Mandai and Accessibility in the state
    resp2 = handle_request(mock_call_gemini, "Sightseeing tour", chat_id)
    session = memory.session_manager.get_session(chat_id)
    print(f"Bot: {resp2}")
    print(f"State after Turn 2: {session.to_dict()}")
    
    # CRITICAL ASSERTION: Did it remember Turn 1?
    assert session.entities.get("locatedIn") == "Mandai", "Bot FORGOT Mandai!"
    assert session.entities.get("wheelchairAccessible") == True, "Bot FORGOT Accessibility!"
    # And check the new entity
    assert session.intent == "activity"

    print("\nSUCCESS: Memory persists across turns!")

if __name__ == "__main__":
    try:
        test_mandai_scenario()
    except Exception as e:
        print(f"\nFAILURE: {e}")
