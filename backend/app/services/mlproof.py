"""Evidence that the models are real: live refits with measured timings, artifact fingerprints and how each answer is served.

Nothing here is cached. The forecast pages are fast because their results are cached for six hours and the deep models are
trained offline and only run forward in the browser session; this module shows the work behind them.
"""

import hashlib
import json
import time
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models import FreightRate

ART = Path(__file__).resolve().parents[1] / "ml" / "artifacts"


def _series(db: Session, name: str) -> pd.Series:
    rows = db.query(FreightRate.rate_date, FreightRate.value).filter(FreightRate.index_name == name).order_by(FreightRate.rate_date).all()
    return pd.Series([float(v) for _, v in rows], index=pd.to_datetime([d for d, _ in rows]))


def _lags(s: pd.Series, n: int = 10) -> tuple[np.ndarray, np.ndarray]:
    v = s.values
    X = np.array([v[i - n:i] for i in range(n, len(v))])
    return X, v[n:]


def live_refit(db: Session, index_name: str = "OCEAN_GULF_JAPAN", horizon: int = 3, splits: int = 10) -> dict:
    from statsmodels.tsa.arima.model import ARIMA
    from xgboost import XGBRegressor

    from app.services.freight_data import is_monthly, load_series

    s = load_series(db, index_name)
    monthly = is_monthly(s)
    if len(s) < (120 if monthly else 400):
        raise ValueError(f"Not enough history for {index_name}")
    warnings.filterwarnings("ignore")
    t0 = time.perf_counter()
    ar_err, xgb_err, naive_err, hyb_err = [], [], [], []
    ar_t = xgb_t = 0.0
    origins = [int(x) for x in np.linspace(len(s) - horizon - (96 if monthly else 600), len(s) - horizon - 1, splits)]  # spread over the last eight years (monthly) or ~2.5 years (daily)
    for o in origins:
        train, actual = s.iloc[:o], float(s.iloc[o + horizon - 1])
        t = time.perf_counter()
        f_ar = float(ARIMA(train.iloc[-750:], order=(2, 1, 2)).fit().forecast(horizon).iloc[-1])
        ar_t += time.perf_counter() - t
        t = time.perf_counter()
        d = train.iloc[-900:].diff().dropna()  # learn day-to-day changes, not levels
        X, y = _lags(d)
        m = XGBRegressor(n_estimators=150, max_depth=3, learning_rate=0.08, subsample=0.9, random_state=7, n_jobs=1).fit(X, y)
        hist = list(d.values[-10:])
        level = float(train.iloc[-1])
        for _ in range(horizon):  # recursive multi-step forecast of changes
            step = float(m.predict(np.array([hist[-10:]]))[0])
            hist.append(step)
            level += step
        f_x = level
        xgb_t += time.perf_counter() - t
        f_n = float(train.iloc[-1])
        ar_err.append(abs(f_ar - actual)); xgb_err.append(abs(f_x - actual)); naive_err.append(abs(f_n - actual)); hyb_err.append(abs((f_ar + f_x) / 2 - actual))
    total = time.perf_counter() - t0
    mae = lambda e: round(float(np.mean(e)), 1)  # noqa: E731
    return {
        "index": index_name, "horizon_steps": horizon, "walk_forward_origins": len(origins), "history_points": len(s), "step": "month" if monthly else "day",
        "history_from": s.index[0].date().isoformat(), "history_to": s.index[-1].date().isoformat(),
        "mae": {"naive (last value)": mae(naive_err), "ARIMA(2,1,2)": mae(ar_err), "XGBoost (10 lags)": mae(xgb_err), "ARIMA + XGBoost average": mae(hyb_err)},
        "timings_seconds": {"total": round(total, 2), "arima_fits": round(ar_t, 2), "xgboost_fits": round(xgb_t, 2), "models_fitted": len(origins) * 2},
        "window": {"from": s.index[origins[0]].date().isoformat(), "to": s.index[origins[-1]].date().isoformat()},
        "note": "Each origin refits both models on data up to that date, then predicts the next window it has not seen. This recent window is more volatile than the cached backtest, so errors are larger; compare the ranking, not the level, and treat ten origins as an illustration, not a significance test (the Model Lab has the paired tests).",
    }


def artifacts() -> list[dict]:
    out = []
    for p in sorted(ART.glob("*")):
        if p.is_file():
            out.append({"file": p.name, "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()[:16],
                        "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")})
    return out


def serving_map() -> list[dict]:
    return [
        {"result": "Forecast and ensemble pages", "how": "Computed on first request (ARIMA + XGBoost + SHAP, about 20 to 30 s), then cached for 6 hours and warmed at start-up.", "live": False},
        {"result": "GRU neural network (current data)", "how": "Trained offline with PyTorch (scripts/train_current_dl.py) with walk-forward retraining; the test results are saved as JSON (fingerprints below).", "live": False},
        {"result": "Assistant intent model", "how": "TF-IDF plus logistic regression retrained at every server start (a second or two); the accuracy figure is 5-fold cross-validation.", "live": True},
        {"result": "Urgent Desk, What-If, Verdict, Risk Lab", "how": "Computed on each request from the cost model and Monte Carlo draws (results cached 10 minutes for identical inputs).", "live": True},
        {"result": "This page", "how": "Refits ARIMA and XGBoost live on every call, uncached.", "live": True},
    ]


def dl_summary() -> dict | None:
    f = ART / "current_dl.json"
    return json.loads(f.read_text()) if f.exists() else None


def proof(db: Session, index_name: str = "OCEAN_GULF_JAPAN") -> dict:
    return {"live_refit": live_refit(db, index_name), "artifacts": artifacts(), "serving": serving_map(), "deep_learning_results": dl_summary()}
