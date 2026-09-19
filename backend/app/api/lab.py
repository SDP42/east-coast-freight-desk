"""Model Lab: the deep-learning comparison and PyTorch-free deep forecasts."""

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from datetime import date  # noqa: F401

from app.api.deps import get_current_user, require, require_port
from app.models import User
from app.services import lab as lab_service
from app.core.cache import cached, data_version
from app.db.session import get_db
from app.ml import dl_infer
from app.services.freight_data import load_series

router = APIRouter(tags=["lab"])
MARKET = [Depends(require("market:read"))]


@router.get("/lab/models", dependencies=MARKET)
def lab_models() -> dict:
    res = dl_infer.results()
    if res is None:
        raise HTTPException(status_code=404, detail="The deep-learning experiment has not been run (scripts/train_dl.py).")
    board = res["leaderboard"]
    arima = next(r for r in board if r["model"].startswith("ARIMA("))
    best = board[0]
    deep = [r for r in board if r["model"] in ("LSTM", "GRU", "TCN", "Transformer", "Deep ensemble (mean of 4)")]
    sig_deep = [r["model"] for r in deep if r.get("vs_arima_p", 1) < 0.05]
    verdict = (
        f"On {res['paired_forecasts']} paired {res['horizon_days']}-day forecasts of the {res['index']} index, the most accurate model is {best['model']} "
        f"(MAE {best['mae']} vs ARIMA {arima['mae']}). "
        + (f"Deep models significantly better than ARIMA: {', '.join(sig_deep)}. " if sig_deep else "No deep model is significantly better than ARIMA at the 5% level. ")
        + "With about 2,500 daily observations, neural networks have little data to learn from; treat the ranking as evidence for this series and window, not a general result."
    )
    return {**res, "verdict": verdict, "served_models": dl_infer.available(res["index"]), "weather_experiment": dl_infer.weather_experiment()}


@router.get("/forecast-deep/{index_name}", dependencies=MARKET)
def forecast_deep(index_name: str, db: Session = Depends(get_db)) -> dict:
    name = index_name.upper()
    if name != "BPI" or not dl_infer.available(name):
        raise HTTPException(status_code=404, detail="Deep models are trained for BPI only.")

    def compute() -> dict:
        y = load_series(db, name)
        exog = {n: load_series(db, n) for n in dl_infer.EXOG}
        out = {}
        for kind in dl_infer.available(name):
            p = dl_infer.predict(kind, y, exog, name)
            out[kind] = [round(float(v), 2) for v in p]
        start = y.index[-1] + pd.Timedelta(days=1)
        return {"index_name": name, "last_date": str(y.index[-1].date()), "last_value": round(float(y.iloc[-1]), 2),
                "dates": [str((start + pd.Timedelta(days=i)).date()) for i in range(7)], "forecasts": out,
                "note": "Seven-day paths from LSTM and GRU models (average of three seeds each), served with NumPy. Compare with the ARIMA path on the Forecast page."}

    return cached(f"deep:{name}:{data_version(db, name)}", 6 * 3600, compute)


@router.get("/lab/anomalies", dependencies=MARKET)
def lab_anomalies(db: Session = Depends(get_db)) -> dict:
    items = cached(f"anomalies:{date.today()}", 1800, lambda: lab_service.anomalies(db))
    return {"items": items, "method": "Latest 1-day and 5-day log-return against the series' own last 260 days (z-score, flagged at 2 or more). 'As of' is each series' last observation, which for the freight indices is July 2019."}


@router.get("/lab/terrain", dependencies=MARKET)
def lab_terrain(db: Session = Depends(get_db)) -> dict:
    return cached("terrain", 6 * 3600, lambda: lab_service.terrain(db))


@router.get("/lab/fan/{index_name}", dependencies=MARKET)
def lab_fan(index_name: str, horizon: int = 60, db: Session = Depends(get_db)) -> dict:
    if not 10 <= horizon <= 120:
        raise HTTPException(status_code=422, detail="horizon must be 10 to 120 days")
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


LIVE_SERIES = [("BPI", "Panamax index", "points"), ("BCI", "Capesize index", "points"), ("BSI", "Supramax index", "points"), ("COAL_AUS", "Australian coal", "usd/t"),
               ("INR", "INR per USD", "inr"), ("SP500", "S&P 500", "usd"), ("DXY", "US dollar index", "pts")]


@router.get("/live/seed", dependencies=MARKET)
def live_seed(db: Session = Depends(get_db)) -> dict:
    """Real anchors for the simulated minute ticks: last two closes and daily volatility per series."""
    import numpy as np

    out = []
    for key, label, unit in LIVE_SERIES:
        s = load_series(db, key)
        if len(s) < 300:
            continue
        r = np.log(s.where(s > 0)).diff().dropna()
        out.append({"key": key, "label": label, "unit": unit, "prev_close": round(float(s.iloc[-2]), 4), "last_close": round(float(s.iloc[-1]), 4),
                    "prev_date": str(s.index[-2].date()), "last_date": str(s.index[-1].date()), "daily_vol": round(float(r.iloc[-250:].std()), 6)})
    return {"series": out, "simulated": True,
            "note": "SIMULATED minute ticks. Each series replays its last real trading day as 390 one-minute steps (a Brownian bridge between the two real closes, with the series' real daily volatility). This is not a market feed: no free source of minute-level freight rates exists."}
