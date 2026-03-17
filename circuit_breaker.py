import time
from threading import Lock

# Simple in-memory circuit breaker
_lock = Lock()
_consecutive_failures = 0
_open_until = 0.0

# Configurable thresholds
THRESHOLD = 5
COOLDOWN_SECONDS = 300


def record_failure():
    global _consecutive_failures, _open_until
    with _lock:
        _consecutive_failures += 1
        if _consecutive_failures >= THRESHOLD:
            _open_until = time.time() + COOLDOWN_SECONDS


def record_success():
    global _consecutive_failures, _open_until
    with _lock:
        _consecutive_failures = 0
        _open_until = 0.0


def is_open() -> bool:
    with _lock:
        if _open_until and time.time() < _open_until:
            return True
        return False


def reset():
    global _consecutive_failures, _open_until
    with _lock:
        _consecutive_failures = 0
        _open_until = 0.0
