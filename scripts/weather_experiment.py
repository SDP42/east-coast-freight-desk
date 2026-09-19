"""Does weather help forecast port traffic? For each East Coast port, predict the mean daily dry-bulk port calls over
the next 14 days from recent calls alone (baseline) and from recent calls plus recent wind, rain and wave height
(Open-Meteo, ERA5-based, CC BY 4.0), with a ridge regression, over the last 12 walk-forward windows. Writes
backend/app/ml/artifacts/weather_experiment.json. Run: backend/.venv/bin/python scripts/weather_experiment.py"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.linear_model import Ridge

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.db.session import SessionLocal  # noqa: E402
from app.models import PortActivity  # noqa: E402

RAW = ROOT / "data" / "raw" / "open"
PORTS = ["Paradip", "Visakhapatnam", "Haldia", "Dhamra", "Gopalpur"]
H, WINDOWS = 14, 12


def weather(port: str) -> pd.DataFrame:
    wx = json.loads((RAW / f"wx_{port}.json").read_text())["daily"]
    mr = json.loads((RAW / f"marine_{port}.json").read_text())["daily"]
    df = pd.DataFrame({"date": pd.to_datetime(wx["time"]), "wind": wx["wind_speed_10m_max"], "rain": wx["precipitation_sum"]}).set_index("date")
    df["wave"] = pd.Series(mr["wave_height_max"], index=pd.to_datetime(mr["time"]))
    return df.ffill()


def main() -> None:
    db = SessionLocal()
    rows = db.query(PortActivity.port_name, PortActivity.activity_date, PortActivity.dry_bulk_calls).all()
    calls = pd.DataFrame(rows, columns=["port", "date", "calls"])
    calls["date"] = pd.to_datetime(calls["date"])
    out, all_base, all_wx = [], [], []
    for port in PORTS:
        if not (RAW / f"wx_{port}.json").exists() or not (RAW / f"marine_{port}.json").exists():
            continue
        s = calls[calls.port == port].set_index("date")["calls"].asfreq("D").fillna(0.0)
        w = weather(port).reindex(s.index).ffill().bfill()
        X_base = pd.DataFrame({"m7": s.rolling(7).mean(), "m14": s.rolling(14).mean(), "m28": s.rolling(28).mean(), "m90": s.rolling(90).mean()})
        X_wx = X_base.assign(wind7=w.wind.rolling(7).mean(), wind14=w.wind.rolling(14).max(), rain14=w.rain.rolling(14).sum(), wave7=w.wave.rolling(7).mean(), wave14=w.wave.rolling(14).max(),
                             doy_s=np.sin(2 * np.pi * s.index.dayofyear / 365.25), doy_c=np.cos(2 * np.pi * s.index.dayofyear / 365.25))
        y = s.rolling(H).mean().shift(-H)  # mean of the next H days
        idx = np.arange(len(s))
        eb, ew, en = [], [], []
        for k in range(WINDOWS, 0, -1):
            cut = len(s) - k * H - H
            if cut < 500:
                continue
            train = idx[120:cut - H]
            for name, X, store in (("base", X_base, eb), ("wx", X_wx, ew)):
                m = Ridge(alpha=3.0).fit(X.iloc[train].to_numpy(), y.iloc[train].to_numpy())
                pred = float(m.predict(X.iloc[[cut]].to_numpy())[0])
                store.append(abs(pred - float(y.iloc[cut])))
            en.append(abs(float(X_base["m14"].iloc[cut]) - float(y.iloc[cut])))
        eb, ew, en = np.array(eb), np.array(ew), np.array(en)
        all_base += eb.tolist(); all_wx += ew.tolist()
        out.append({"port": port, "windows": len(eb), "mae_naive": round(float(en.mean()), 3), "mae_calls_only": round(float(eb.mean()), 3), "mae_with_weather": round(float(ew.mean()), 3),
                    "weather_gain_pct": round(float((1 - ew.mean() / eb.mean()) * 100), 1)})
    p = float(wilcoxon(np.array(all_wx), np.array(all_base), alternative="less").pvalue) if len(all_wx) > 5 else None
    res = {"horizon_days": H, "windows_per_port": WINDOWS, "ports": out, "pooled_p_weather_better": None if p is None else round(p, 4),
           "verdict": ("Adding weather did not significantly improve 14-day port-call forecasts." if p is None or p >= 0.05 else "Adding weather significantly improved 14-day port-call forecasts."),
           "note": "Ridge regression on recent calls (with and without wind, rain, wave height and season) predicting the mean calls over the next 14 days; last 12 walk-forward windows per port; pooled one-sided Wilcoxon test across ports."}
    path = ROOT / "backend" / "app" / "ml" / "artifacts" / "weather_experiment.json"
    path.write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
