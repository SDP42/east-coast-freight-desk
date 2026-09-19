"""Current-data models: what the retrained models say, and how much to trust them.

Reads the artifacts written by scripts/train_current.py and scripts/train_current_dl.py (offline training, walk-forward tested).
"""

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.services.mlproof import _series

ART = Path(__file__).resolve().parents[1] / "ml" / "artifacts"


def _load(name: str) -> dict | None:
    f = ART / name
    return json.loads(f.read_text()) if f.exists() else None


def current_models(db: Session) -> dict:
    res, dl = _load("current_results.json"), _load("current_dl.json")
    if res is None:
        raise ValueError("Current-data models have not been trained yet (run scripts/train_current.py).")
    hist = _series(db, "OCEAN_GULF_JAPAN")
    hist = hist.resample("MS").mean().interpolate(limit=6).dropna().iloc[-72:]
    tg = res["nowcast_baltic"]["targets"]
    lines = []
    for h in res["forecast_gulf_rate"]:
        best = min(h["models"], key=lambda k: h["models"][k]["mae_usd_per_t"])
        b, n = h["models"][best], h["models"]["naive"]
        sig = b["p_vs_naive"] is not None and b["p_vs_naive"] < 0.05
        lines.append(f"{h['horizon_months']}-month rate forecast: best model {best} (MAE ${b['mae_usd_per_t']}/t) vs no-change ${n['mae_usd_per_t']}/t; "
                     + ("significantly better." if sig else "not significantly better than assuming no change."))
    if dl:
        lines.append(f"GRU neural network: MAE ${dl['gru_mae_usd_per_t']}/t vs no-change ${dl['naive_mae_usd_per_t']}/t (p = {dl['p_vs_naive']}); it does not beat the naive forecast on {dl['origins']} months.")
    for name, t in tg.items():
        c = t[t["chosen"]]
        lines.append(f"{name} nowcast: out-of-sample skill {c['oos_r2_vs_mean']} against the historical mean ({t['chosen']}); " + ("usable as an estimate." if t["reliable"] else "too weak to use, so it is not shown as a figure."))
    return {
        "data_through": res["data_through"], "trained_at": res["trained_at"],
        "gulf_rate_history": [{"month": d.date().isoformat(), "usd_per_t": round(float(v), 2)} for d, v in hist.items()],
        "gulf_rate_forecast": res["gulf_forecast"], "forecast_tests": res["forecast_gulf_rate"], "deep_learning": dl,
        "baltic_nowcast": {n: {**{k: v for k, v in t.items() if k != "series"}, "series": (t["series"][-72:] if t["reliable"] else [])} for n, t in tg.items()},
        "nowcast_overlap": {k: res["nowcast_baltic"][k] for k in ("overlap_months", "overlap_from", "overlap_to")},
        "verdicts": lines,
        "caveat": "Baltic values after July 2019 are ESTIMATES from a relationship fitted on 84 months (2012 to 2019) and applied to a different market regime; treat them as indicative, with the wide band shown. They are not Baltic Exchange data.",
    }
