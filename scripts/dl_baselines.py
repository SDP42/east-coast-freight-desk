"""Stage 1 of the deep-learning experiment: the classical baselines (ARIMA, XGBoost, hybrid) on the Baltic Panamax
index, 7-day horizon, through the production walk-forward splits. Writes backend/app/ml/artifacts/dl_baselines.json.
Kept in its own process because PyTorch and XGBoost bundle conflicting OpenMP runtimes on macOS (segfault if
imported together). Run first: backend/.venv/bin/python scripts/dl_baselines.py"""

import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.ml.ensemble_backtest import paired_walk_forward_backtest  # noqa: E402
from app.services.freight_data import load_series  # noqa: E402

INDEX, HORIZON, N_SPLITS = "BPI", 7, 5
EXOG = ["SP500", "DXY", "COAL_AUS", "COAL_ZA"]


def main() -> None:
    db = SessionLocal()
    y = load_series(db, INDEX)
    exog = {n.lower(): load_series(db, n) for n in EXOG}
    exog = {k: v for k, v in exog.items() if not v.empty}
    report, _ = paired_walk_forward_backtest(y, (2, 1, 2), {"max_depth": 3, "learning_rate": 0.05, "n_estimators": 200}, exog, horizon=HORIZON, n_splits=N_SPLITS)
    out = {"index": INDEX, "horizon": HORIZON, "n_splits": N_SPLITS, "actuals": report.actuals, "arima": report.arima_abs_errors,
           "xgb": report.xgb_abs_errors, "hybrid": report.hybrid_abs_errors}
    path = ROOT / "backend" / "app" / "ml" / "artifacts" / "dl_baselines.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out))
    print(f"baselines written: {len(report.actuals)} paired forecasts")


if __name__ == "__main__":
    main()
