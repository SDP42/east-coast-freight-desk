"""Measure how well forecast bands cover real outcomes, and save the result for the Model Lab.

Walk-forward over the last ~12 years of the USDA monthly ocean rate: at every origin an ARIMA(2,1,2) is refitted on data up to that
month, then the outcome h months later is checked against (a) ARIMA's own 95% band and (b) the calibrated band from
app/ml/intervals.py. Takes about a minute and a half. Run: python scripts/eval_intervals.py"""

import json
import sys
import warnings
from datetime import date
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from statsmodels.tsa.arima.model import ARIMA  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.ml.intervals import calibrated_halfwidth  # noqa: E402
from app.services.freight_data import load_series  # noqa: E402

HORIZONS = (1, 3, 6)
ORIGINS = 144


def main() -> None:
    s = load_series(SessionLocal(), "OCEAN_GULF_JAPAN")
    v = s.to_numpy()
    n = len(v)
    acc = {h: {"arima_hit": [], "arima_w": [], "c95_hit": [], "c95_w": [], "c80_hit": [], "c80_w": [], "naive": [], "model": []} for h in HORIZONS}
    for o in range(n - ORIGINS - max(HORIZONS), n - max(HORIZONS)):
        train = v[:o]
        fc = ARIMA(train[-240:], order=(2, 1, 2)).fit().get_forecast(max(HORIZONS))
        ci = fc.conf_int(alpha=0.05)
        mean = fc.predicted_mean
        for h in HORIZONS:
            actual, p = v[o + h - 1], float(mean[h - 1])
            lo, hi = float(ci[h - 1][0]), float(ci[h - 1][1])
            a = acc[h]
            a["arima_hit"].append(lo <= actual <= hi); a["arima_w"].append(hi - lo)
            for lvl, key in ((0.95, "c95"), (0.80, "c80")):
                hw = calibrated_halfwidth(train, h, lvl)
                a[key + "_hit"].append(abs(actual - p) <= hw); a[key + "_w"].append(2 * hw)
            a["naive"].append(abs(train[-1] - actual)); a["model"].append(abs(p - actual))
    out = {"index": "OCEAN_GULF_JAPAN", "generated": date.today().isoformat(), "origins": ORIGINS, "window_months": 60,
           "history_to": s.index[-1].date().isoformat(), "horizons": {}}
    for h, a in acc.items():
        out["horizons"][str(h)] = {
            "arima_95_coverage": round(float(np.mean(a["arima_hit"])), 3), "arima_95_width": round(float(np.mean(a["arima_w"])), 1),
            "calibrated_95_coverage": round(float(np.mean(a["c95_hit"])), 3), "calibrated_95_width": round(float(np.mean(a["c95_w"])), 1),
            "calibrated_80_coverage": round(float(np.mean(a["c80_hit"])), 3), "calibrated_80_width": round(float(np.mean(a["c80_w"])), 1),
            "mae_no_change": round(float(np.mean(a["naive"])), 2), "mae_arima": round(float(np.mean(a["model"])), 2),
        }
    dest = Path(__file__).resolve().parents[1] / "backend" / "app" / "ml" / "artifacts" / "interval_calibration.json"
    dest.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
