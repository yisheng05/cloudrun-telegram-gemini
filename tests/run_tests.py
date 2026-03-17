import sys
import os
# Ensure project root is on sys.path so imports work when running this script
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from middleware import handle_request, request_tmr_from_model, perception_simulate
from knowledge import load_kg


def test_deliberation_filters():
    kg = load_kg()
    print('KG nodes:', len(kg.get('nodes', [])))

    # Simulate TMR entities with time outside opening hours
    tmr = {'intent': 'inform', 'entities': {'servesCuisine': 'Italian', 'locatedIn': 'Marina Bay', 'time': '23:00'}}
    # Use internal function via handle_request path (we'll call handle_request with text trigger)
    res = handle_request(None, 'Find Italian restaurants in Marina Bay at 23:00')
    print('Response for late time:', res)

    # Now a time within hours
    res2 = handle_request(None, 'Find Italian restaurants in Marina Bay at 12:00')
    print('Response for noon:', res2)

    # Accessibility filter
    res3 = handle_request(None, 'Find Italian restaurants in Marina Bay; wheelchair accessible')
    print('Response for accessibility:', res3)


if __name__ == '__main__':
    test_deliberation_filters()
