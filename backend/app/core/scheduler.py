"""Background job: evaluate every active alert rule on a fixed interval. One asyncio task per process;
evaluation runs in a worker thread so slow model calls never block requests."""

import asyncio
import logging

from app.db.session import SessionLocal
from datetime import datetime, timedelta

from app.models import ModelRun
from app.services import alerts, monitor

log = logging.getLogger("app.scheduler")
INTERVAL_SECONDS = 30 * 60


def _run_once() -> int:
    db = SessionLocal()
    try:
        # Scheduled retraining: refit when drift is flagged and no run happened in the last 24 hours.
        try:
            if monitor.drift_report(db, "BPI")["status"] == "drift":
                last = db.query(ModelRun).filter(ModelRun.index_name == "BPI").order_by(ModelRun.id.desc()).first()
                if last is None or last.trained_at < datetime.utcnow() - timedelta(hours=24):
                    monitor.retrain(db, "BPI", "scheduled")
        except Exception:
            log.exception("scheduled retraining failed")
        return len(alerts.evaluate(db))
    finally:
        db.close()


async def alert_loop() -> None:
    await asyncio.sleep(60)  # let the server finish starting
    while True:
        try:
            fired = await asyncio.to_thread(_run_once)
            log.info("alert evaluation finished, %d new event(s)", fired)
        except Exception:
            log.exception("alert evaluation failed")
        await asyncio.sleep(INTERVAL_SECONDS)


def _prewarm_once() -> None:
    from app.api import forecast as forecast_api
    from app.api import tools

    db = SessionLocal()
    try:
        forecast_api.get_forecast("BPI", 14, db)
        tools.forecast_multi("BPI", db)
        tools.transfer(db)
        from app.ml import intent

        intent.classify("warm up")  # builds the intent models, including the embedding model if available
        log.info("prewarm finished")
    finally:
        db.close()


async def prewarm() -> None:
    await asyncio.sleep(3)
    try:
        await asyncio.to_thread(_prewarm_once)
    except Exception:
        log.exception("prewarm failed")
