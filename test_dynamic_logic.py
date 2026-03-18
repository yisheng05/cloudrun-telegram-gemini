import os
import json
import logging
from middleware import handle_request
import memory

# Use a REAL Gemini call for this test to see if it acknowledges the update
from main import call_gemini

# Enable TMR
os.environ["USE_TMR"] = "true"

def test_dynamic_flow():
    logging.basicConfig(level=logging.INFO)
    chat_id = 555
    memory.session_manager.clear_session(chat_id)
    
    # Use a district NOT currently in the manual KG (e.g., Outram)
    query = "Find me a cafe in Outram"
    print(f"\n--- [TEST: Dynamic Ingestion] ---")
    print(f"User Query: {query}")
    
    # This should trigger run_dynamic_ingestion
    response = handle_request(call_gemini, query, chat_id)
    
    print(f"\nAgent Response: {response}")
    
    # Check if the response mentions OpenStreetMap or OneMap (as per our system note)
    if "OpenStreetMap" in response or "OneMap" in response or "database" in response:
        print("\nSUCCESS: Dynamic update acknowledged!")
    else:
        print("\nNOTE: Dynamic update happened but LLM didn't mention source explicitly. Checking KG...")
    
    # Check if KG actually has Outram now
    kg_path = "cloudrun-telegram-gemini/data/knowledge_graph.json"
    with open(kg_path, "r") as f:
        kg = json.load(f)
        found = any("Outram" in str(node) or "Outram" in str(node.get("properties", {}).get("locatedIn", "")) for node in kg["nodes"])
        if found:
            print("SUCCESS: Outram nodes found in Knowledge Graph!")
        else:
            # Check if any new nodes were added at all
            print(f"Total nodes in KG: {len(kg['nodes'])}")
            print("FAILURE: No new nodes found in KG matching Outram.")

if __name__ == "__main__":
    test_dynamic_flow()
