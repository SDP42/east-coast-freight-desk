"""Response cache for expensive model-backed endpoints.

Uses Redis when it is reachable and falls back to a per-process dict otherwise, so the API behaves the
same locally (no Redis) and in production. Values must be JSON-serialisable. Keys should include a data
version (see `data_version`) so a cache entry never outlives the data it was computed from."""

import json
import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.redis_client import get_redis
from app.models import FreightRate

log = logging.getLogger("app.cache")
_mem: dict[str, tuple[float, str]] = {}
_lock = threading.Lock()
_redis_ok: bool | None = None
_redis_checked_at = 0.0
_stats = {"hits": 0, "misses": 0}
PREFIX = "freightdesk:"


def _redis():
    """Return a live Redis client, or None. A failed check is remembered for 60 seconds."""
    global _redis_ok, _redis_checked_at
    now = time.time()
    if _redis_ok is False and now - _redis_checked_at < 60:
        return None
    if _redis_ok is None or now - _redis_checked_at >= 60:
        try:
            r = get_redis()
            r.ping()
            _redis_ok = True
        except Exception:
            _redis_ok = False
        _redis_checked_at = now
    return get_redis() if _redis_ok else None


def _get(key: str) -> str | None:
    r = _redis()
    if r is not None:
        try:
            return r.get(PREFIX + key)
        except Exception:
            pass
    with _lock:
        hit = _mem.get(key)
        if hit and hit[0] > time.time():
            return hit[1]
        _mem.pop(key, None)
    return None


def _set(key: str, ttl: int, payload: str) -> None:
    r = _redis()
    if r is not None:
        try:
            r.setex(PREFIX + key, ttl, payload)
            return
        except Exception:
            pass
    with _lock:
        if len(_mem) > 500:
            _mem.clear()
        _mem[key] = (time.time() + ttl, payload)


def cached(key: str, ttl: int, compute: Callable[[], Any]) -> Any:
    raw = _get(key)
    if raw is not None:
        _stats["hits"] += 1
        return json.loads(raw)
    _stats["misses"] += 1
    value = compute()
    _set(key, ttl, json.dumps(value, default=str))
    return value


def stats() -> dict:
    total = _stats["hits"] + _stats["misses"]
    return {**_stats, "hit_rate": round(_stats["hits"] / total, 3) if total else None, "backend": "redis" if _redis_ok else "memory", "memory_entries": len(_mem)}


def clear() -> None:
    with _lock:
        _mem.clear()
    r = _redis()
    if r is not None:
        try:
            for k in r.scan_iter(PREFIX + "*"):
                r.delete(k)
        except Exception:
            pass


def data_version(db: Session, *index_names: str) -> str:
    """Fingerprint of the underlying series: latest date and row count per index."""
    parts = []
    for name in index_names:
        d, n = db.query(func.max(FreightRate.rate_date), func.count(FreightRate.id)).filter(FreightRate.index_name == name).one()
        parts.append(f"{name}:{d}:{n}")
    return "|".join(parts)
