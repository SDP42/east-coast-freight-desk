"""Lab pages: anomalies, terrain, forecast fan, cost at risk, lightering, timing, live ticks, model proof and the current-data models."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from datetime import date  # noqa: F401

from app.api.deps import get_current_user, require, require_port
from app.models import User
from app.services import lab as lab_service
from app.core.cache import cached, data_version
from app.db.session import get_db
from app.services.freight_data import load_series

from pathlib import Path

router = APIRouter(tags=["lab"])
MARKET = [Depends(require("market:read"))]


@router.get("/lab/anomalies", dependencies=MARKET)
def lab_anomalies(db: Session = Depends(get_db)) -> dict:
    items = cached(f"anomalies:{date.today()}", 1800, lambda: lab_service.anomalies(db))
    return {"items": items, "method": "Latest 1-day and 5-day log-return against the series' own last 260 days (z-score, flagged at 2 or more). 'As of' is each series' last observation. Daily series only (oil, exchange rates, dollar index)."}


@router.get("/lab/terrain", dependencies=MARKET)
def lab_terrain(db: Session = Depends(get_db)) -> dict:
    return cached("terrain", 6 * 3600, lambda: lab_service.terrain(db))


@router.get("/lab/fan/{index_name}", dependencies=MARKET)
def lab_fan(index_name: str, horizon: int = 12, db: Session = Depends(get_db)) -> dict:
    if not 3 <= horizon <= 36:
        raise HTTPException(status_code=422, detail="horizon must be 3 to 36 steps (months for the USDA ocean rate)")
    try:
        return cached(f"fan:{index_name.upper()}:{horizon}:{data_version(db, index_name.upper())}", 6 * 3600, lambda: lab_service.fan_paths(db, index_name.upper(), horizon))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/lab/chokepoints", dependencies=[Depends(require("ports:read"))])
def lab_chokepoints(db: Session = Depends(get_db)) -> dict:
    return cached(f"chokepoints:{date.today()}", 3600, lambda: lab_service.chokepoint_status(db))


@router.get("/lab/lightering", dependencies=[Depends(require("ports:read"))])
def lab_lightering(cargo_tonnes: float = 150000, barge_capacity_t: float = 6000, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    require_port(user, "Haldia", db)  # the fit is built from Haldia's own vessel calls
    if not 20000 <= cargo_tonnes <= 400000:
        raise HTTPException(status_code=422, detail="cargo_tonnes must be 20,000 to 400,000")
    try:
        return lab_service.lightering_plan(db, cargo_tonnes, barge_capacity_t)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/lab/timing", dependencies=[Depends(require("ports:read"))])
def lab_timing(port: str, origin: str = "Australia", db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    require_port(user, port, db)
    return cached(f"timing:{port}:{origin}:{date.today()}", 3600, lambda: lab_service.timing_coach(db, port, origin))


@router.get("/lab/cost-at-risk", dependencies=[Depends(require("financial:read"))])
def lab_cost_at_risk(origin: str, port: str, cargo_tonnes: float = 75000, vessel_class: str = "Panamax", db: Session = Depends(get_db)) -> dict:
    if not 5000 <= cargo_tonnes <= 400000:
        raise HTTPException(status_code=422, detail="cargo_tonnes must be 5,000 to 400,000")
    try:
        return lab_service.cost_at_risk(db, origin, port, cargo_tonnes, vessel_class)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


LIVE_SERIES = [("BRENT", "Brent crude", "usd/bbl"), ("INR", "INR per USD", "inr"), ("AUD", "USD per AUD", "usd"), ("ZAR", "ZAR per USD", "zar"), ("DXY", "US dollar index", "pts")]


@router.get("/live/seed", dependencies=MARKET)
def live_seed(db: Session = Depends(get_db)) -> dict:
    """Real anchors for the simulated minute ticks: last two closes and daily volatility per series. Off unless SHOW_SIMULATED_FEEDS is set."""
    import numpy as np
    from app.core.config import get_settings

    if not get_settings().SHOW_SIMULATED_FEEDS:
        raise HTTPException(status_code=404, detail="Simulated feeds are switched off in this deployment.")

    out = []
    for key, label, unit in LIVE_SERIES:
        s = load_series(db, key)
        if len(s) < 300:
            continue
        r = np.log(s.where(s > 0)).diff().dropna()
        out.append({"key": key, "label": label, "unit": unit, "prev_close": round(float(s.iloc[-2]), 4), "last_close": round(float(s.iloc[-1]), 4),
                    "prev_date": str(s.index[-2].date()), "last_date": str(s.index[-1].date()), "daily_vol": round(float(r.iloc[-250:].std()), 6)})
    return {"series": out, "simulated": True,
            "note": "SIMULATED minute ticks. Each series replays its last real trading day as 390 one-minute steps (a Brownian bridge between the two real closes, with the series' real daily volatility). This is not a market feed: no free source of minute-level market data exists."}


@router.get("/lab/proof/{index_name}", dependencies=MARKET)
def model_proof(index_name: str, db: Session = Depends(get_db)) -> dict:
    """Live, uncached refit with timings."""
    from app.services import mlproof
    try:
        return mlproof.proof(db, index_name.upper() if index_name.upper() != 'PRIMARY' else 'OCEAN_GULF_JAPAN')
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/lab/interval-calibration", dependencies=MARKET)
def interval_calibration() -> dict:
    """Measured coverage of forecast bands from a walk-forward test (scripts/eval_intervals.py)."""
    import json

    f = Path(__file__).resolve().parents[1] / "ml" / "artifacts" / "interval_calibration.json"
    if not f.exists():
        raise HTTPException(status_code=404, detail="Interval calibration has not been generated. Run scripts/eval_intervals.py.")
    return json.loads(f.read_text())


@router.get("/lab/current", dependencies=MARKET)
def current_models(db: Session = Depends(get_db)) -> dict:
    """Models retrained on the current data: the USDA ocean-rate forecast and the Baltic nowcast, with honest tests."""
    from app.services import current
    try:
        out = cached(f"current:{data_version(db, 'OCEAN_GULF_JAPAN')}", 3600, lambda: current.current_models(db))
        from app.ml.intervals import calibrated_halfwidth
        from app.services.freight_data import load_series

        vals = load_series(db, "OCEAN_GULF_JAPAN").to_numpy()
        path = out.get("gulf_rate_forecast", {}).get("path", [])
        out = {**out, "gulf_rate_forecast": {**out["gulf_rate_forecast"], "path": [
            {**p, **({"low": round(p["forecast"] - hw, 2), "high": round(p["forecast"] + hw, 2)} if (hw := calibrated_halfwidth(vals, k)) is not None else {})}
            for k, p in enumerate(path, start=1)], "band": "calibrated 95% band from the last five years of actual moves"}}
        return out
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
