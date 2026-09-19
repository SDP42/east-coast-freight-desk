import time

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.redis_client import get_redis
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    """Liveness/readiness probe — also confirms Postgres and Redis are reachable."""
    started = time.perf_counter()

    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    redis_ok = True
    try:
        get_redis().ping()
    except Exception:
        redis_ok = False

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

    return {
        # Redis is optional: without it the response cache runs in process memory.
        "status": "ok" if db_ok else "degraded",
        "database": "up" if db_ok else "down",
        "cache": "redis" if redis_ok else "in-memory",
        "latency_ms": elapsed_ms,
    }
