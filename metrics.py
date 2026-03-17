from threading import Lock
from collections import defaultdict
from typing import Dict, Any

_lock = Lock()
_counters = defaultdict(int)


def reset() -> None:
    with _lock:
        _counters.clear()


def inc(name: str, amount: int = 1) -> None:
    with _lock:
        _counters[name] += amount


def get(name: str) -> int:
    with _lock:
        return int(_counters.get(name, 0))


def snapshot() -> Dict[str, int]:
    with _lock:
        return dict(_counters)
