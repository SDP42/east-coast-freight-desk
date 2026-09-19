"""Train and honestly test the models that use the current (post-2019) public data.

Task A: forecast the USDA U.S. Gulf-to-Japan grain ocean rate (monthly, to Aug 2026), 1 and 3 months ahead.
Inputs are public-domain only: the USDA ocean rates, the US BLS coal and deep-sea freight indices, US EIA Brent oil and the
Federal Reserve rupee rate. (The Baltic nowcast was removed with the Baltic data, whose licence is proprietary.)
Everything is expanding-window walk-forward: a model only ever sees data before the month it predicts.
Writes backend/app/ml/artifacts/current_results.json. Run with the backend's Python (no torch needed; the GRU is train_current_dl.py).
"""

import json
import sys
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.linear_model import Ridge
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA
from xgboost import XGBRegressor

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.db.session import SessionLocal  # noqa: E402
from app.models import FreightRate  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "backend" / "app" / "ml" / "artifacts" / "current_results.json"


def monthly(db, name: str) -> pd.Series:
    rows = db.query(FreightRate.rate_date, FreightRate.value).filter(FreightRate.index_name == name).order_by(FreightRate.rate_date).all()
    s = pd.Series([float(v) for _, v in rows], index=pd.to_datetime([d for d, _ in rows]))
    return s.resample("MS").mean().interpolate(limit=6)  # a few months are missing in the USDA sheet; fill short gaps only


def load(db) -> pd.DataFrame:
    cols = {"GULF": "OCEAN_GULF_JAPAN", "PNW": "OCEAN_PNW_JAPAN", "COAL": "COAL_PPI", "OIL": "BRENT", "INR": "INR"}
    df = pd.concat({k: monthly(db, v) for k, v in cols.items()}, axis=1)
    return df


def lag_frame(df: pd.DataFrame, h: int) -> tuple[pd.DataFrame, pd.Series]:
    l = np.log(df[["GULF", "PNW", "COAL", "OIL", "INR"]])
    d = l.diff()
    X = pd.concat({f"gulf_d{k}": d["GULF"].shift(k) for k in (0, 1, 2)}, axis=1)
    X["pnw_d0"], X["coal_d0"], X["oil_d0"], X["inr_d0"] = d["PNW"], d["COAL"], d["OIL"], d["INR"]
    X["gap_gulf_pnw"] = l["GULF"] - l["PNW"]
    y = l["GULF"].shift(-h) - l["GULF"]  # change over the next h months
    return X, y


def walk_forward_gulf(df: pd.DataFrame, h: int, start: str = "2010-01-01") -> dict:
    s = df["GULF"].dropna()
    X, y = lag_frame(df.loc[s.index[0]:], h)
    ok = X.dropna().index.intersection(y.dropna().index)
    origins = [t for t in s.index if t >= pd.Timestamp(start) and t + pd.DateOffset(months=h) in s.index]
    preds = {k: [] for k in ("naive", "ARIMA(1,1,1)", "ETS (damped trend)", "Ridge", "ExtraTrees", "XGBoost", "ARIMA+XGBoost", "Ridge+ARIMA")}
    actual, dates = [], []
    for t in origins:
        train_idx = [i for i in ok if i + pd.DateOffset(months=h) <= t]  # only rows whose outcome was known at t
        if len(train_idx) < 60 or t not in X.index or X.loc[t].isna().any():
            continue
        Xt, yt = X.loc[train_idx], y.loc[train_idx]
        last = float(s.loc[t])
        truth = float(s.loc[t + pd.DateOffset(months=h)])
        f_ar = float(np.exp(np.log(last) + (ARIMA(np.log(s.loc[:t]).iloc[-240:], order=(1, 1, 1)).fit().forecast(h).iloc[-1] - np.log(last))))
        f_r = last * float(np.exp(Ridge(alpha=1.0).fit(Xt, yt).predict(X.loc[[t]])[0]))
        f_x = last * float(np.exp(XGBRegressor(n_estimators=120, max_depth=2, learning_rate=0.05, subsample=0.9, random_state=7, n_jobs=1).fit(Xt, yt).predict(X.loc[[t]])[0]))
        try:
            ets = ExponentialSmoothing(np.log(s.loc[:t]).iloc[-240:], trend="add", damped_trend=True).fit()
            f_e = float(np.exp(ets.forecast(h).iloc[-1]))
        except Exception:  # noqa: BLE001
            f_e = last
        f_t = last * float(np.exp(ExtraTreesRegressor(n_estimators=150, min_samples_leaf=5, random_state=7, n_jobs=1).fit(Xt, yt).predict(X.loc[[t]])[0]))
        for k, v in (("naive", last), ("ARIMA(1,1,1)", f_ar), ("ETS (damped trend)", f_e), ("Ridge", f_r), ("ExtraTrees", f_t), ("XGBoost", f_x), ("ARIMA+XGBoost", (f_ar + f_x) / 2), ("Ridge+ARIMA", (f_r + f_ar) / 2)):
            preds[k].append(v)
        actual.append(truth)
        dates.append(t.date().isoformat())
    a = np.array(actual)
    res = {}
    base_err = np.abs(np.array(preds["naive"]) - a)
    for k, p in preds.items():
        e = np.abs(np.array(p) - a)
        pval = None
        if k != "naive" and np.any(e != base_err):
            pval = float(wilcoxon(e, base_err).pvalue)
        res[k] = {"mae_usd_per_t": round(float(e.mean()), 2), "mape_pct": round(float((e / a).mean() * 100), 2), "p_vs_naive": None if pval is None else round(pval, 4)}
    return {"horizon_months": h, "origins": len(a), "test_from": dates[0], "test_to": dates[-1], "models": res}


def gulf_forecast(df: pd.DataFrame, best_by_h: dict[int, str]) -> dict:
    """Six-month path of the USDA rate from ARIMA on log rates, with a band from historical 1-, 3-, 6-month change errors."""
    s = np.log(df["GULF"].dropna())
    fit = ARIMA(s.iloc[-240:], order=(1, 1, 1)).fit()
    f = fit.get_forecast(6)
    mean, ci = f.predicted_mean, f.conf_int(alpha=0.2)
    last = df["GULF"].dropna()
    return {"last_month": last.index[-1].date().isoformat(), "last_value": round(float(last.iloc[-1]), 2), "method": "ARIMA(1,1,1) on log rates, last 20 years, 80% band",
            "path": [{"month": (last.index[-1] + pd.DateOffset(months=i + 1)).date().isoformat(), "forecast": round(float(np.exp(m)), 2), "low": round(float(np.exp(lo)), 2), "high": round(float(np.exp(hi)), 2)}
                     for i, (m, lo, hi) in enumerate(zip(mean, ci.iloc[:, 0], ci.iloc[:, 1]))]}


def main() -> None:
    db = SessionLocal()
    df = load(db)
    db.close()
    res = {"trained_at": datetime.now().isoformat(timespec="seconds"), "data_through": df["GULF"].dropna().index[-1].date().isoformat(), "months_used": int(df["GULF"].notna().sum())}
    res["forecast_gulf_rate"] = [walk_forward_gulf(df, 1), walk_forward_gulf(df, 3)]
    for r in res["forecast_gulf_rate"]:
        print(f"h={r['horizon_months']}m origins={r['origins']} ({r['test_from']}..{r['test_to']})", {k: (v['mae_usd_per_t'], v['p_vs_naive']) for k, v in r["models"].items()})
    res["inputs"] = ["OCEAN_GULF_JAPAN", "OCEAN_PNW_JAPAN", "COAL_PPI (US BLS)", "BRENT (US EIA)", "INR (Federal Reserve)"]
    res["gulf_forecast"] = gulf_forecast(df, {})
    OUT.write_text(json.dumps(res, indent=1))
    print("saved", OUT)


if __name__ == "__main__":
    main()
