"""Model monitoring and retraining (#25), demonstrated on the daily Brent crude series (US EIA, public domain; a bunker-fuel proxy). A forecast model is trained up to a cut-off and then frozen;
the monitor scores its one-step-ahead errors on data that arrived after the cut-off and compares them with
the errors in the period just before. Drift is flagged when recent errors are significantly and
materially worse, or when the daily-return distribution has shifted (population stability index)."""

import numpy as np
from scipy.stats import mannwhitneyu
from sqlalchemy.orm import Session
from statsmodels.tsa.arima.model import ARIMA

from app.models import ModelRun
from app.services.freight_data import load_series
from app.services.quick_forecast import _cache

ORDER = (2, 1, 2)
RECENT_DAYS = 90
REFERENCE_DAYS = 365
FIT_DAYS = 800


def _psi(ref: np.ndarray, new: np.ndarray, bins: int = 10) -> float:
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    r = np.histogram(ref, edges)[0] / len(ref)
    n = np.histogram(new, edges)[0] / len(new)
    r, n = np.clip(r, 1e-4, None), np.clip(n, 1e-4, None)
    return float(np.sum((n - r) * np.log(n / r)))


def drift_report(db: Session, index_name: str = "BRENT") -> dict:
    s = load_series(db, index_name)
    if len(s) < FIT_DAYS + RECENT_DAYS + REFERENCE_DAYS:
        raise ValueError(f"Not enough {index_name} history for monitoring")
    cutoff = len(s) - RECENT_DAYS
    fit = ARIMA(s.iloc[cutoff - FIT_DAYS:cutoff], order=ORDER).fit()
    applied = fit.apply(s.iloc[cutoff - FIT_DAYS:])  # frozen parameters, one-step-ahead predictions on new data
    pred = applied.fittedvalues.reindex(s.index)
    ape = ((s - pred).abs() / s * 100).dropna()
    ape = ape[ape.index >= s.index[cutoff - FIT_DAYS + 30]]
    recent = ape[ape.index >= s.index[cutoff]]
    reference = ape[(ape.index < s.index[cutoff]) & (ape.index >= s.index[cutoff - REFERENCE_DAYS])]
    ratio = float(recent.mean() / reference.mean()) if reference.mean() else float("nan")
    p = float(mannwhitneyu(recent.values, reference.values, alternative="greater").pvalue)
    ret = np.log(s).diff().dropna()
    psi = _psi(ret.iloc[-(RECENT_DAYS + REFERENCE_DAYS):-RECENT_DAYS].values, ret.iloc[-RECENT_DAYS:].values)
    model_drift = bool(p < 0.01 and ratio > 1.5)
    data_drift = bool(psi > 0.25)
    rolling = ape.rolling(30).mean().dropna()
    series = [{"date": str(d.date()), "mape_30d": round(float(v), 3)} for d, v in rolling.iloc[-240::4].items()]
    last_run = db.query(ModelRun).filter(ModelRun.index_name == index_name).order_by(ModelRun.id.desc()).first()
    return {
        "index_name": index_name, "data_through": str(s.index[-1].date()), "frozen_model_trained_through": str(s.index[cutoff - 1].date()),
        "reference_mape": round(float(reference.mean()), 3), "recent_mape": round(float(recent.mean()), 3), "error_ratio": round(ratio, 2), "mann_whitney_p": round(p, 4),
        "return_psi": round(psi, 3), "model_drift": model_drift, "data_drift": data_drift, "status": "drift" if (model_drift or data_drift) else "stable",
        "thresholds": {"error_ratio": 1.5, "p_value": 0.01, "psi": 0.25}, "rolling_mape": series,
        "last_retrained": str(last_run.trained_at) if last_run else None,
        "method": f"ARIMA{ORDER} trained on the {FIT_DAYS} days before a cut-off {RECENT_DAYS} days ago, then applied with frozen parameters. One-step-ahead absolute percentage errors on the last {RECENT_DAYS} days are compared with the preceding {REFERENCE_DAYS} days (one-sided Mann-Whitney U). PSI compares the daily-return distribution over the same two windows.",
    }


def retrain(db: Session, index_name: str = "BRENT", trigger: str = "manual") -> ModelRun:
    before = drift_report(db, index_name)
    s = load_series(db, index_name)

    holdout = s.iloc[-30:]
    ref_fit = ARIMA(s.iloc[-FIT_DAYS - 30:-30], order=ORDER).fit()
    pred = ref_fit.apply(s.iloc[-FIT_DAYS - 30:]).fittedvalues.iloc[-30:]
    mape = float(((holdout - pred).abs() / holdout * 100).mean())
    for k in [k for k in _cache if k[0] == index_name]:
        _cache.pop(k, None)
    run = ModelRun(index_name=index_name, trigger=trigger, order=str(ORDER), train_rows=len(s.iloc[-FIT_DAYS:]), train_end=s.index[-1].date(), holdout_mape=mape,
                   drift_before=before["status"] == "drift")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def history(db: Session, index_name: str = "BRENT", limit: int = 20) -> list[dict]:
    rows = db.query(ModelRun).filter(ModelRun.index_name == index_name).order_by(ModelRun.id.desc()).limit(limit).all()
    return [{"id": r.id, "trained_at": str(r.trained_at), "trigger": r.trigger, "order": r.order, "train_rows": r.train_rows, "train_end": str(r.train_end),
             "holdout_mape": round(float(r.holdout_mape), 3) if r.holdout_mape is not None else None, "drift_before": r.drift_before} for r in rows]


