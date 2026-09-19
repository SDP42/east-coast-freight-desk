"""Train and honestly test the models that use the current (post-2019) public data.

Task A: forecast the USDA U.S. Gulf-to-Japan grain ocean rate (monthly, to Aug 2026), 1 and 3 months ahead.
Task B: nowcast the Baltic Supramax, Panamax and Capesize indices from that rate (and coal, iron ore, rupee) for 2019-2026,
        where the Baltic series no longer exists. Fitted on the 84 months where both exist (Aug 2012 to Jul 2019).
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
from sklearn.linear_model import Ridge
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
    cols = {"GULF": "OCEAN_GULF_JAPAN", "PNW": "OCEAN_PNW_JAPAN", "COAL": "COAL_AUS", "ORE": "IRON_ORE", "INR": "INR", "BPI": "BPI", "BSI": "BSI", "BCI": "BCI"}
    df = pd.concat({k: monthly(db, v) for k, v in cols.items()}, axis=1)
    return df


def lag_frame(df: pd.DataFrame, h: int) -> tuple[pd.DataFrame, pd.Series]:
    l = np.log(df[["GULF", "PNW", "COAL", "ORE", "INR"]])
    d = l.diff()
    X = pd.concat({f"gulf_d{k}": d["GULF"].shift(k) for k in (0, 1, 2)}, axis=1)
    X["pnw_d0"], X["coal_d0"], X["ore_d0"], X["inr_d0"] = d["PNW"], d["COAL"], d["ORE"], d["INR"]
    X["gap_gulf_pnw"] = l["GULF"] - l["PNW"]
    y = l["GULF"].shift(-h) - l["GULF"]  # change over the next h months
    return X, y


def walk_forward_gulf(df: pd.DataFrame, h: int, start: str = "2010-01-01") -> dict:
    s = df["GULF"].dropna()
    X, y = lag_frame(df.loc[s.index[0]:], h)
    ok = X.dropna().index.intersection(y.dropna().index)
    origins = [t for t in s.index if t >= pd.Timestamp(start) and t + pd.DateOffset(months=h) in s.index]
    preds = {k: [] for k in ("naive", "ARIMA(1,1,1)", "Ridge", "XGBoost", "ARIMA+XGBoost")}
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
        for k, v in (("naive", last), ("ARIMA(1,1,1)", f_ar), ("Ridge", f_r), ("XGBoost", f_x), ("ARIMA+XGBoost", (f_ar + f_x) / 2)):
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


def nowcast(df: pd.DataFrame) -> dict:
    feats = ["GULF", "PNW", "COAL", "ORE", "INR"]
    L = np.log(df[feats + ["BPI", "BSI", "BCI"]])
    both = L.dropna()
    out: dict = {"overlap_months": len(both), "overlap_from": both.index[0].date().isoformat(), "overlap_to": both.index[-1].date().isoformat(), "targets": {}}
    full = np.log(df[feats]).dropna()
    future = full[full.index > both.index[-1]]
    for tgt, name in (("BSI", "Supramax"), ("BPI", "Panamax"), ("BCI", "Capesize")):
        for label, cols in (("gulf only", ["GULF"]), ("gulf + coal + ore", ["GULF", "COAL", "ORE"]), ("all five", feats)):
            oos_pred, oos_true, base = [], [], []
            for i in range(36, len(both)):  # expanding window, never sees the month it predicts
                tr, te = both.iloc[:i], both.iloc[[i]]
                m = Ridge(alpha=1.0).fit(tr[cols], tr[tgt])
                oos_pred.append(float(m.predict(te[cols])[0])); oos_true.append(float(te[tgt].iloc[0])); base.append(float(tr[tgt].mean()))
            y, p, b = np.array(oos_true), np.array(oos_pred), np.array(base)
            r2 = 1 - ((y - p) ** 2).sum() / ((y - b) ** 2).sum()  # skill against always predicting the training mean
            out["targets"].setdefault(name, {})[label] = {"oos_r2_vs_mean": round(float(r2), 3), "oos_mape_pct": round(float(np.abs(np.expm1(p - y)).mean() * 100), 1), "months_tested": len(y)}
        # Choose the feature set with the best out-of-sample skill; refit on all overlap months; nowcast the future months.
        best = max(out["targets"][name], key=lambda k: out["targets"][name][k]["oos_r2_vs_mean"])
        cols = {"gulf only": ["GULF"], "gulf + coal + ore": ["GULF", "COAL", "ORE"], "all five": feats}[best]
        m = Ridge(alpha=1.0).fit(both[cols], both[tgt])
        resid = both[tgt] - m.predict(both[cols])
        q = float(np.quantile(np.abs(resid), 0.9)) * 1.5  # widened: the relationship is extrapolated to a different regime
        pt = m.predict(future[cols])
        out["targets"][name]["chosen"] = best
        out["targets"][name]["reliable"] = bool(out["targets"][name][best]["oos_r2_vs_mean"] >= 0.5)
        out["targets"][name]["band_log"] = round(q, 3)
        out["targets"][name]["series"] = [{"date": d.date().isoformat(), "estimate": round(float(np.exp(v))), "low": round(float(np.exp(v - q))), "high": round(float(np.exp(v + q)))} for d, v in zip(future.index, pt)]
    return out


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
    res["nowcast_baltic"] = nowcast(df)
    for k, v in res["nowcast_baltic"]["targets"].items():
        print(k, {kk: vv["oos_r2_vs_mean"] for kk, vv in v.items() if isinstance(vv, dict) and "oos_r2_vs_mean" in vv}, "chosen", v["chosen"], "reliable", v["reliable"])
    res["gulf_forecast"] = gulf_forecast(df, {})
    OUT.write_text(json.dumps(res, indent=1))
    print("saved", OUT)


if __name__ == "__main__":
    main()
