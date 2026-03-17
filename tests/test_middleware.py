import os
import metrics
import middleware


def setup_function():
    # ensure clean metrics per test
    metrics.reset()


def test_request_tmr_success():
    def good_model(prompt):
        return '{"intent": "inform", "entities": {"servesCuisine": "Italian", "locatedIn": "Marina Bay"}}'

    res = middleware.request_tmr_from_model(good_model, 'Find Italian restaurants in Marina Bay')
    assert isinstance(res, dict)
    assert res.get('entities', {}).get('servesCuisine') == 'Italian'
    assert metrics.get('tmr_failures') == 0


def test_request_tmr_retry_and_fallback(monkeypatch):
    # flaky model: always raise
    def bad_model(prompt):
        raise Exception('api down')

    res = middleware.request_tmr_from_model(bad_model, 'Find Italian restaurants in Marina Bay', max_retries=2, base_delay=0.01)
    # should return a TMR dict from perception_simulate
    assert isinstance(res, dict)
    # metrics should show failures and one fallback
    assert metrics.get('tmr_failures') >= 1
    assert metrics.get('tmr_fallbacks') == 1


def test_produce_final_response_model_and_fallback():
    # prepare a verified facts dict
    verified = {
        'verified': [
            {'name': 'Saizeriya', 'properties': {'servesCuisine': 'Italian', 'locatedIn': 'Marina Bay', 'hasPriceRange': 'Low', 'openingHours': '11:00-22:00'}}
        ]
    }

    def good_final(prompt):
        return 'Here are verified options: Saizeriya (Italian) at Marina Bay.'

    reply = middleware.produce_final_response(good_final, verified, 'Find Italian restaurants in Marina Bay')
    assert 'Saizeriya' in reply
    assert metrics.get('final_response_failures') == 0

    def bad_final(prompt):
        raise Exception('model error')

    metrics.reset()
    reply2 = middleware.produce_final_response(bad_final, verified, 'Find Italian restaurants in Marina Bay')
    assert 'Saizeriya' in reply2
    assert metrics.get('final_response_failures') == 1
