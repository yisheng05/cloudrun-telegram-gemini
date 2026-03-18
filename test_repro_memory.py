import os
import json
from middleware import handle_request
import memory

# Mock Gemini
def mock_call_gemini(prompt):
    return "This is a mock response from Gemini."

# Use simulated perception
os.environ["USE_TMR"] = "false"

def repro_memory_issue():
    chat_id = 777
    memory.session_manager.clear_session(chat_id)
    
    print("\n--- [TURN 1: Initial Request] ---")
    user_text1 = "2 day one night itinerary planning nature walks and shopping in Singapore."
    print(f"User: {user_text1}")
    resp1 = handle_request(mock_call_gemini, user_text1, chat_id)
    session = memory.session_manager.get_session(chat_id)
    print(f"Bot: {resp1}")
    print(f"State after Turn 1: {session.to_dict()}")
    
    print("\n--- [TURN 2: Refinement] ---")
    user_text2 = "Museums."
    print(f"User: {user_text2}")
    resp2 = handle_request(mock_call_gemini, user_text2, chat_id)
    session = memory.session_manager.get_session(chat_id)
    print(f"Bot: {resp2}")
    print(f"State after Turn 2: {session.to_dict()}")

    print("\n--- [TURN 3: Broad Planning near Mandai] ---")
    user_text3 = "itinerary planning near Mandai."
    print(f"User: {user_text3}")
    resp3 = handle_request(mock_call_gemini, user_text3, chat_id)
    session = memory.session_manager.get_session(chat_id)
    print(f"Bot: {resp3}")
    print(f"State after Turn 3: {session.to_dict()}")
    
    # In Turn 3, it should SHOW the Mandai attractions even if activity_type is missing
    # because it is now proactive!
    if "Botanic Gardens" in resp3 or "Jumbo" in resp1: # Checking for results in bot response
         pass 

if __name__ == "__main__":
    repro_memory_issue()
