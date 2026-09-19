"""Current-data models: what the retrained models say, and how much to trust them.

Reads the artifacts written by scripts/train_current.py and scripts/train_current_dl.py (offline training, walk-forward tested).
All inputs are public-domain US-government or Federal Reserve series.
"""

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.services.freight_data import PRIMARY_INDEX, load_series

ART = Path(__file__).resolve().parents[1] / "ml" / "artifacts"


def _load(name: str) -> dict | None:
    f = ART / name
    return json.loads(f.read_text()) if f.exists() else None


def current_models(db: Session) -> dict:
    res, dl = _load("current_results.json"), _load("current_dl.json")
    if res is None:
        raise ValueError("Current-data models have not been trained yet (run scripts/train_current.py).")
    hist = load_series(db, PRIMARY_INDEX).iloc[-72:]
    lines = []
    for h in res["forecast_gulf_rate"]:
        cands = {k: v for k, v in h["models"].items() if k != "naive" and v["p_vs_naive"] is not None}
        n = len(cands)
        best = min(h["models"], key=lambda k: h["models"][k]["mae_usd_per_t"])
        b, nv = h["models"][best], h["models"]["naive"]
        adj = min(1.0, b["p_vs_naive"] * n) if b["p_vs_naive"] is not None else None
        if best == "naive":
            verdict = "no model beats assuming no change."
        elif adj is not None and adj < 0.05:
            verdict = f"significantly better (p = {b['p_vs_naive']}, {adj:.3f} after correcting for {n} models compared)."
        else:
            verdict = f"better in error but not significant once {n} models are compared (p = {b['p_vs_naive']}, {adj:.2f} after correction)."
        worse = [k for k, v in cands.items() if v["mae_usd_per_t"] > nv["mae_usd_per_t"] and v["p_vs_naive"] < 0.05]
        lines.append(f"{h['horizon_months']}-month rate forecast: best model {best} (MAE ${b['mae_usd_per_t']}/t) vs no-change ${nv['mae_usd_per_t']}/t; {verdict}"
                     + (f" Significantly WORSE than no change: {', '.join(worse)}." if worse else ""))
    if dl:
        lines.append(f"GRU neural network: MAE ${dl['gru_mae_usd_per_t']}/t vs no-change ${dl['naive_mae_usd_per_t']}/t (p = {dl['p_vs_naive']}); "
                     + ("better than" if dl["gru_mae_usd_per_t"] < dl["naive_mae_usd_per_t"] and dl["p_vs_naive"] < 0.05 else "it does not beat") + f" the naive forecast on {dl['origins']} months.")
    return {
        "data_through": res["data_through"], "trained_at": res["trained_at"], "inputs": res.get("inputs"),
        "gulf_rate_history": [{"month": d.date().isoformat(), "usd_per_t": round(float(v), 2)} for d, v in hist.items()],
        "gulf_rate_forecast": res["gulf_forecast"], "forecast_tests": res["forecast_gulf_rate"], "deep_learning": dl, "verdicts": lines,
        "caveat": "The USDA ocean rate behaves close to a random walk: no model is reliably better than assuming no change. The forecasts are shown with their honest test results.",
    }
