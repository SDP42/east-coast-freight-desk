"""Port signals: cyclone-adjusted ETA risk (#13), berth-slot availability forecast (#22), cross-port
congestion transfer (#23) and the cargo demand estimator (#21). Everything is derived from data in the
database (IBTrACS-derived exposure, IMF PortWatch daily dry-bulk calls, SAIL annual-report figures);
assumed parameters are named and returned with each result."""

from datetime import date, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from statsmodels.tools.sm_exceptions import InterpolationWarning  # noqa: F401
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import grangercausalitytests

from app.db.session import SessionLocal
from app.models import CycloneExposure, Port, PortActivity
from app.services.risk import _congestion_score

STORM_DAY_DELAY_DAYS = 1.5  # assumed average delay (waiting out weather, closed pilotage) per storm day near the port
SEVERE_EXTRA_DELAY_DAYS = 2.0  # assumed extra delay if the storm is severe (>=64 kt)


# ---------------------------------------------------------------- cyclone-adjusted ETA / laycan risk
def cyclone_eta_risk(db: Session, port_name: str, laycan_start: date, laycan_end: date, transit_days: float = 0.0) -> dict:
    rows = {r.month: r for r in db.query(CycloneExposure).filter(CycloneExposure.port_name == port_name).all()}
    if not rows:
        raise ValueError(f"No cyclone exposure data for {port_name}")
    arrival_start = laycan_start + timedelta(days=round(transit_days))
    days = [arrival_start + timedelta(days=i) for i in range((laycan_end - laycan_start).days + 1)]
    p_storm, p_severe = [], []
    for d in days:
        r = rows[d.month]
        p_storm.append(float(r.storm_day_prob))
        p_severe.append(float(r.severe_day_prob))
    expected_storm_days = float(np.sum(p_storm))
    expected_delay = expected_storm_days * STORM_DAY_DELAY_DAYS + float(np.sum(p_severe)) * SEVERE_EXTRA_DELAY_DAYS
    p_any = 1 - float(np.prod([1 - p for p in p_storm]))
    label = "High" if p_any > 0.35 else "Moderate" if p_any > 0.15 else "Low"
    monthly = [{"month": m, "storm_day_pct": round(float(rows[m].storm_day_prob) * 100, 2), "severe_day_pct": round(float(rows[m].severe_day_prob) * 100, 2),
                "storms_per_year": round(float(rows[m].storms_per_year), 3)} for m in range(1, 13)]
    safest = min(rows.values(), key=lambda r: float(r.storm_day_prob))
    return {
        "port": port_name, "arrival_window_start": str(days[0]), "arrival_window_end": str(days[-1]),
        "probability_storm_in_window": round(p_any, 3), "expected_storm_days": round(expected_storm_days, 3),
        "expected_delay_days": round(expected_delay, 2), "risk_label": label, "safest_month": safest.month, "monthly": monthly,
        "assumptions": {"delay_days_per_storm_day": STORM_DAY_DELAY_DAYS, "extra_delay_days_if_severe": SEVERE_EXTRA_DELAY_DAYS, "storm_radius_km": 400, "years": rows[1].years},
        "method": "Share of days 1990-2025 with a tropical storm (>=34 kt) centred within 400 km of the port, from IBTrACS; expected delay uses the two assumed delay parameters above.",
    }


# ---------------------------------------------------------------- port activity series
def _daily_calls(db: Session) -> pd.DataFrame:
    rows = db.query(PortActivity.port_name, PortActivity.activity_date, PortActivity.dry_bulk_calls).all()
    df = pd.DataFrame(rows, columns=["port", "date", "calls"])
    if df.empty:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"])
    return df.pivot_table(index="date", columns="port", values="calls", aggfunc="sum").asfreq("D").fillna(0.0)


# ---------------------------------------------------------------- berth slot availability
def berth_slots(db: Session, port_name: str, horizon: int = 14) -> dict:
    calls = _daily_calls(db)
    if calls.empty or port_name not in calls.columns:
        raise ValueError(f"No PortWatch activity for {port_name}")
    s = calls[port_name]
    smooth = s.rolling(7, min_periods=1).mean()
    cap = float(np.percentile(smooth.dropna(), 90))  # a busy-but-normal week is the pressure reference

    def cand_arima(train: pd.Series, h: int) -> np.ndarray:
        return np.asarray(ARIMA(train.iloc[-730:], order=(1, 1, 1)).fit().forecast(h))

    candidates = {
        "last 14-day mean": lambda tr, h: np.full(h, tr.iloc[-14:].mean()),
        "last 28-day mean": lambda tr, h: np.full(h, tr.iloc[-28:].mean()),
        "last 90-day mean": lambda tr, h: np.full(h, tr.iloc[-90:].mean()),
        "ARIMA(1,1,1)": cand_arima,
    }
    # Rolling-origin backtest over the last 12 windows; the model with the lowest mean absolute error is used.
    scores: dict[str, list[float]] = {k: [] for k in candidates}
    for k_ in range(12, 0, -1):
        cut = len(smooth) - k_ * horizon
        if cut < 400:
            continue
        actual = smooth.iloc[cut:cut + horizon].values
        for name, f in candidates.items():
            scores[name].append(float(np.mean(np.abs(f(smooth.iloc[:cut], horizon) - actual))))
    mae_by_model = {k: round(float(np.mean(v)), 3) for k, v in scores.items() if v}
    chosen = min(mae_by_model, key=mae_by_model.get)
    naive_mae = mae_by_model["last 14-day mean"]
    pred = candidates[chosen](smooth, horizon)
    start = smooth.index[-1] + pd.Timedelta(days=1)
    days = []
    for i, v in enumerate(pred):
        pressure = float(max(0.0, v) / cap) if cap else 0.0
        days.append({"date": str((start + pd.Timedelta(days=i)).date()), "expected_calls_per_day": round(float(max(0.0, v)), 2),
                     "pressure": round(pressure, 2), "slot": "tight" if pressure > 0.95 else "moderate" if pressure > 0.7 else "open"})
    open_days = [d["date"] for d in days if d["slot"] == "open"]
    mae = mae_by_model[chosen]
    return {
        "port": port_name, "data_through": str(smooth.index[-1].date()), "reference_calls_per_day_p90": round(cap, 2), "days": days,
        "open_days": open_days, "backtest": {"windows": len(scores["last 14-day mean"]), "chosen_model": chosen, "mae_calls_per_day": mae, "naive_mae": naive_mae,
                     "skill_vs_naive_pct": round((1 - mae / naive_mae) * 100, 1) if naive_mae else None, "mae_by_model": mae_by_model},
        "method": "Forecast of the 7-day mean of daily dry-bulk port calls (IMF PortWatch, AIS-derived), choosing the best of four simple models by 12-window rolling-origin backtest. Pressure = forecast / the port's own 90th-percentile weekly level. This measures traffic, not berth bookings.",
    }


# ---------------------------------------------------------------- congestion transfer
@lru_cache(maxsize=1)
def _transfer_matrix() -> list[dict]:
    db = SessionLocal()
    try:
        calls = _daily_calls(db)
    finally:
        db.close()
    if calls.empty:
        return []
    smooth = calls.rolling(7, min_periods=1).mean().diff().dropna()
    out = []
    ports = list(smooth.columns)
    for a in ports:
        for b in ports:
            if a == b:
                continue
            try:
                res = grangercausalitytests(smooth[[b, a]].iloc[-1500:], maxlag=10, verbose=False)
            except Exception:
                continue
            best_lag = min(res, key=lambda k: res[k][0]["ssr_ftest"][1])
            p = float(res[best_lag][0]["ssr_ftest"][1])
            out.append({"from_port": a, "to_port": b, "lag_days": int(best_lag), "p_value": p})
    return out


def congestion_transfer(db: Session) -> dict:
    pairs = _transfer_matrix()
    n = len(pairs) or 1
    for p in pairs:
        p["p_adjusted"] = min(1.0, p["p_value"] * n)  # Bonferroni across all pairs
        p["significant"] = p["p_adjusted"] < 0.05
    sig = sorted([p for p in pairs if p["significant"]], key=lambda p: p["p_adjusted"])

    calls = _daily_calls(db)
    status = []
    for port in calls.columns:
        s = calls[port]
        recent, base = float(s.iloc[-14:].mean()), float(s.mean())
        sd = float(s.rolling(14).mean().std()) or 1.0
        z = (recent - base) / sd
        status.append({"port": port, "recent_calls_per_day": round(recent, 2), "baseline": round(base, 2), "z": round(z, 2)})
    status.sort(key=lambda r: -r["z"])
    signal = None
    hot = [s for s in status if s["z"] > 1.0]
    if hot:
        h = hot[0]
        cool = [s for s in status if s["port"] != h["port"] and s["z"] < 0.5]
        linked = [p for p in sig if p["from_port"] == h["port"]]
        signal = {
            "hot_port": h["port"], "hot_z": h["z"],
            "consider": cool[0]["port"] if cool else None,
            "linked_ports_expected_to_follow": [{"port": p["to_port"], "after_days": p["lag_days"]} for p in linked],
            "text": f"{h['port']} traffic is {h['z']:.1f} standard deviations above its norm. "
                    + (f"Consider {cool[0]['port']} (currently {cool[0]['z']:.1f})." if cool else "No calm alternative right now.")
                    + (f" Historically pressure at {h['port']} leads {', '.join(p['to_port'] for p in linked)}." if linked else ""),
        }
    return {"pairs": sorted(pairs, key=lambda p: p["p_adjusted"])[:12], "significant_pairs": sig, "status": status, "signal": signal,
            "method": "Granger causality (F-test, best lag up to 10 days) on first differences of the 7-day mean of daily dry-bulk port calls, Bonferroni-corrected across all port pairs. Predictive precedence, not proof of cause.",
            "data_through": str(calls.index[-1].date()) if not calls.empty else None}


# ---------------------------------------------------------------- demand estimator
# Crude steel and imported clean coking coal, SAIL annual reports FY24 and FY25 (see SECTIONS.md 14c).
DEMAND_POINTS = [("FY24", 19.24, 16.92), ("FY25", 19.17, 16.32)]
REPORTED_CRUDE = {"Q1 FY26": 4.854, "Q2 FY26": 9.503 - 4.854, "FY26": 19.434, "Q1 FY27": 4.757}


def demand_estimate(growth_pct: float = 0.0, parcel_tonnes: float = 33_000) -> dict:
    ratios = [imp / cs for _, cs, imp in DEMAND_POINTS]
    k, spread = float(np.mean(ratios)), float(np.std(ratios))
    rows = []
    for label, crude in REPORTED_CRUDE.items():
        rows.append({"period": label, "crude_steel_mt": round(crude, 3), "imported_coal_mt": round(crude * k, 2),
                     "low_mt": round(crude * (k - 2 * spread), 2), "high_mt": round(crude * (k + 2 * spread), 2),
                     "parcels": int(round(crude * k * 1e6 / parcel_tonnes))})
    next_q = REPORTED_CRUDE["Q1 FY27"] * (1 + growth_pct / 100)
    return {
        "ratio_imported_to_crude": round(k, 3), "ratio_spread": round(spread, 3),
        "points": [{"year": y, "crude_steel_mt": c, "imported_coal_mt": i, "ratio": round(i / c, 3)} for y, c, i in DEMAND_POINTS],
        "estimates": rows,
        "next_quarter": {"assumed_growth_pct": growth_pct, "crude_steel_mt": round(next_q, 3), "imported_coal_mt": round(next_q * k, 2),
                         "parcels": int(round(next_q * k * 1e6 / parcel_tonnes)), "parcel_tonnes": parcel_tonnes},
        "method": "Imported coking coal is modelled as a fixed share of crude steel output, calibrated on two annual points (FY24, FY25) from SAIL's annual reports, then applied to reported quarterly crude steel. Two points cannot support a regression; the +/- band is two standard deviations of the two ratios and should be read as indicative only.",
    }


def congestion_now(db: Session) -> list[dict]:
    ports = db.query(Port).filter(Port.is_destination.is_(True)).all()
    return [{"port": p.name, "score": round(_congestion_score(p, db)[0], 1)} for p in ports]
