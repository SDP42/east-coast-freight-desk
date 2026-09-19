"""In-memory brute-force guard for the login endpoint: after MAX_FAILURES wrong passwords for an
email (or from one client address) within WINDOW_SECONDS, further attempts get HTTP 429 until the
window clears. Per-process only, which is fine for a single Render instance; a multi-instance
deployment should move this to Redis."""

import time
from collections import defaultdict, deque

MAX_FAILURES = 5
WINDOW_SECONDS = 600

_failures: dict[str, deque[float]] = defaultdict(deque)


def _prune(key: str, now: float) -> deque[float]:
    q = _failures[key]
    while q and now - q[0] > WINDOW_SECONDS:
        q.popleft()
    return q


def retry_after(*keys: str) -> int:
    """Seconds until a locked key may try again, or 0 if none is locked."""
    now = time.time()
    wait = 0
    for k in keys:
        q = _prune(k, now)
        if len(q) >= MAX_FAILURES:
            wait = max(wait, int(WINDOW_SECONDS - (now - q[0])) + 1)
    return wait


def record_failure(*keys: str) -> None:
    now = time.time()
    for k in keys:
        _prune(k, now).append(now)


def clear(*keys: str) -> None:
    for k in keys:
        _failures.pop(k, None)
