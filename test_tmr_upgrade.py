import os
import json
import memory
from middleware import handle_request

# Mock Gemini
def mock_call_gemini(prompt):
    return "I found some places for you."

# Use simulated perception
os.environ["USE_TMR"] = "false"

def test_tmr_improvements():
    chat_id = 111
    memory.session_manager.clear_session(chat_id)
    
    print("\n--- [TEST 1: Negative Constraint] ---")
    # "Find me a restaurant, but not in Marina Bay"
    # Should find Saizeriya (Marina Bay) but FILTER IT OUT
    user_text1 = "Find me a restaurant but not in Marina Bay"
    print(f"User: {user_text1}")
    resp1 = handle_request(mock_call_gemini, user_text1, chat_id)
    session = memory.session_manager.get_session(chat_id)
    print(f"Bot: {resp1}")
    print(f"Entities: {session.entities}")
    
    # Assert 'locatedIn' has 'NOT' op
    assert session.entities["locatedIn"]["op"] == "NOT"
    assert "Saizeriya" not in resp1 # Should not show Saizeriya

    print("\n--- [TEST 2: Dialogue Act Correction] ---")
    # Turn 1: "I want Italian food"
    # Turn 2: "No, I meant Japanese food instead"
    memory.session_manager.clear_session(chat_id)
    handle_request(mock_call_gemini, "I want Italian food", chat_id)
    print("User: No, I meant Japanese food instead")
    resp2 = handle_request(mock_call_gemini, "No, I meant Japanese food instead", chat_id)
    session = memory.session_manager.get_session(chat_id)
    print(f"Bot: {resp2}")
    print(f"Goal: {session.goal}, Dialogue Act: {session.dialogue_act}")
    print(f"Entities: {session.entities}")

    assert session.dialogue_act == "correction"
    assert session.entities["servesCuisine"]["value"] == "Japanese"

    print("\nSUCCESS: TMR Upgrades (Constraints, Dialogue Acts, State) verified!")

if __name__ == "__main__":
    test_tmr_improvements()
