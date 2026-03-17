import os
import logging
from middleware import handle_request

# Mock the Gemini call to avoid API keys if possible, or use a simple mock
def mock_call_gemini(prompt):
    return "This is a mock response from Gemini."

# Set environment variable to simulate Phase 2
os.environ["USE_TMR"] = "true"

print("--- Test 1: General Chat ---")
response = handle_request(mock_call_gemini, "Hello, who are you?")
print(f"Response: {response}\n")

print("--- Test 2: KG Query (Italian) ---")
response = handle_request(mock_call_gemini, "Find Italian food in Marina Bay")
print(f"Response: {response}\n")

print("--- Test 3: Fallback (Unknown) ---")
response = handle_request(mock_call_gemini, "Tell me about quantum physics")
print(f"Response: {response}\n")
