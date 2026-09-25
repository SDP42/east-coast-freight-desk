"""Analytical engines for the Lab pages: chokepoint map, anomaly feed, Monte-Carlo cost-at-risk with forecast fan paths, a
lightering planner, a laycan timing coach, and the data behind the market terrain and trade globe. Built only from
public-domain data; assumed parameters are named and returned with each result."""

from datetime import date, timedelta

import numpy as np
import pandas as pd

from sqlalchemy.orm import Session

from app.models import FreightRate, Port, Route
from app.services.financial import DEMURRAGE_RATE_USD_PER_DAY
from app.services.freight_data import PRIMARY_INDEX, is_monthly, load_series
from app.services.recommendation import BASE_RATE_USD_PER_TONNE_PER_1000NM, VESSEL_CLASS_COST_MULTIPLIER, get_market_signal, market_factor  # noqa: F401
from app.services.signals import cyclone_eta_risk

CHOKEPOINTS = {  # name: (lat, lon, why it matters)
    "Suez Canal": (30.5, 32.35, "Russia and US cargoes can route via Suez"),
    "Bab el-Mandeb Strait": (12.6, 43.35, "Red Sea exit; the diversion barometer"),
    "Malacca Strait": (2.5, 101.5, "Australia, Indonesia and Russia legs pass it"),
    "Cape of Good Hope": (-34.4, 18.5, "Where Red Sea diversions go"),
    "Lombok Strait": (-8.5, 115.7, "Deep-draft route for Capesize from Australia"),
    "Sunda Strait": (-6.0, 105.8, "Alternative Indonesia passage"),
    "Torres Strait": (-10.6, 142.2, "Queensland coal leaves through it"),
}
LANES = {  # origin: list of (lat, lon) waypoints, ending near the Bay of Bengal
    "Australia": [(-21.28, 149.30), (-10.6, 142.0), (-9.0, 125.0), (-9.0, 112.0), (-6.0, 100.0), (4.0, 92.0)],
    "Indonesia": [(-3.32, 114.59), (-3.5, 109.0), (1.3, 104.0), (5.5, 98.0), (8.0, 92.0)],
    "Mozambique": [(-14.5, 40.7), (-8.0, 55.0), (-1.0, 68.0), (5.5, 80.0), (11.0, 86.0)],
    "Russia": [(43.1, 132.9), (30.0, 125.0), (10.0, 112.0), (1.3, 104.0), (5.5, 98.0), (8.0, 92.0)],
    "United States (Suez)": [(37.0, -76.0), (36.0, -10.0), (31.3, 32.3), (12.6, 43.35), (12.0, 55.0), (10.0, 75.0), (9.0, 86.0)],
    "United States (Cape)": [(37.0, -76.0), (10.0, -30.0), (-34.4, 18.5), (-25.0, 50.0), (-5.0, 75.0), (8.0, 86.0)],
}


# ------------------------------------------------------------------ chokepoints
def chokepoint_status(db: Session) -> dict:
    out = [{"name": n, "lat": v[0], "lon": v[1], "why": v[2], "recent_per_day": None, "baseline_per_day": None, "ratio": None, "weekly": [], "through": None} for n, v in CHOKEPOINTS.items()]
    return {"chokepoints": out, "note": "Locations and lanes only. Live chokepoint traffic feeds carry licence conditions, so none is stored; the What-If Studio prices a Red Sea closure directly.",
            "lanes": {k: [list(w) for w in v] for k, v in LANES.items()}, "method": "Hand-placed sea-lane waypoints; no traffic data."}


# ------------------------------------------------------------------ anomalies
def anomalies(db: Session, min_abs_z: float = 2.0) -> list[dict]:
    names = [r[0] for r in db.query(FreightRate.index_name).distinct().all()]
    out = []
    for n in names:
        s = load_series(db, n)
        if len(s) < 300 or is_monthly(s):
            continue
        r = np.log(s.where(s > 0)).diff().dropna()
        sd = float(r.iloc[-260:-1].std())
        if sd == 0:
            continue
        for label, val, date_ in (("1 day", float(r.iloc[-1]), r.index[-1]), ("5 days", float(r.iloc[-5:].sum()), r.index[-1])):
            z = val / (sd * (1 if label == "1 day" else 5 ** 0.5))
            if abs(z) >= min_abs_z:
                out.append({"series": n, "window": label, "move_pct": round((np.exp(val) - 1) * 100, 2), "z": round(z, 2), "as_of": str(date_.date())})
    return sorted(out, key=lambda o: -abs(o["z"]))


# ------------------------------------------------------------------ Monte Carlo cost-at-risk and fan
def _bootstrap_returns(s: pd.Series, horizon: int, n: int, rng, years: int = 15) -> np.ndarray:
    steps_per_year = 12 if is_monthly(s) else 365
    lr = np.log(s.where(s > 0)).diff().dropna().iloc[-steps_per_year * years:].to_numpy()
    block = 3 if is_monthly(s) else 5
    nb = int(np.ceil(horizon / block))
    starts = rng.integers(0, len(lr) - block, size=(n, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n, -1)[:, :horizon]
    return lr[idx]


def fan_paths(db: Session, index_name: str, horizon: int = 12, n: int = 400, seed: int = 7) -> dict:
    s = load_series(db, index_name)
    if len(s) < 60:
        raise ValueError("Not enough history")
    rng = np.random.default_rng(seed)
    rets = _bootstrap_returns(s, horizon, n, rng)
    paths = float(s.iloc[-1]) * np.exp(np.cumsum(rets, axis=1))
    pct = {p: np.percentile(paths, p, axis=0) for p in (5, 25, 50, 75, 95)}
    hist = s.iloc[-36:] if is_monthly(s) else s.iloc[-90:]
    unit = "months" if is_monthly(s) else "days"
    return {"index_name": index_name, "last_date": str(s.index[-1].date()), "last_value": round(float(s.iloc[-1]), 1), "horizon": horizon, "unit": unit,
            "history": [round(float(v), 1) for v in hist.values], "paths": [[round(float(v), 1) for v in p] for p in paths[:150]],
            "percentiles": {str(k): [round(float(v), 1) for v in val] for k, val in pct.items()},
            "terminal": {"p5": round(float(pct[5][-1]), 1), "p50": round(float(pct[50][-1]), 1), "p95": round(float(pct[95][-1]), 1)},
            "method": f"Block bootstrap of the last 15 years of real log-changes ({unit} steps); 400 simulated paths, 150 drawn. Assumes changes keep their historical distribution."}


def cost_at_risk(db: Session, origin: str, port_name: str, cargo_tonnes: float, vessel_class: str = "Panamax", n: int = 5000, laytime_days: float = 2.5, seed: int = 11) -> dict:
    port = db.query(Port).filter(Port.name == port_name, Port.is_destination.is_(True)).first()
    route = (db.query(Route).join(Port, Route.origin_port_id == Port.id).filter(Port.country == origin, Route.destination_port_id == port.id).first()) if port else None
    if not port or not route or not route.distance_nm:
        raise ValueError("No priced route for that origin and port")
    rng = np.random.default_rng(seed)
    mult = VESSEL_CLASS_COST_MULTIPLIER.get(vessel_class, 1.0)
    base_freight = BASE_RATE_USD_PER_TONNE_PER_1000NM * market_factor(db) * float(route.distance_nm) / 1000 * mult
    index_name = PRIMARY_INDEX
    idx = load_series(db, index_name)
    inr = load_series(db, "INR")
    r30 = np.log(idx.where(idx > 0)).diff(1).dropna().iloc[-12 * 15:].to_numpy()  # one-month moves of the monthly USDA ocean rate
    fx30 = np.log(inr.where(inr > 0)).diff(30).dropna().iloc[-365 * 3:].to_numpy()
    freight_mult = np.exp(rng.choice(r30, n) - r30.mean())  # centred: remove the sample drift, keep the spread
    fx_mult = np.exp(rng.choice(fx30, n) - fx30.mean())
    spot_inr = float(inr.iloc[-1])
    month = date.today().month
    cyc = cyclone_eta_risk(db, port_name, date.today() + timedelta(days=30), date.today() + timedelta(days=45), float(route.typical_transit_days or 0))
    storm_delay = rng.poisson(cyc["expected_storm_days"] * 3, n) * 1.5 / 3
    turnaround_days = float(port.avg_turnaround_hours or 49.5) / 24
    turnaround = rng.lognormal(np.log(turnaround_days), 0.3, n) + storm_delay
    demurrage_days = np.maximum(0.0, turnaround - laytime_days)
    rate = DEMURRAGE_RATE_USD_PER_DAY.get(vessel_class, 8000)
    freight_usd = base_freight * freight_mult * cargo_tonnes
    demurrage_usd = demurrage_days * rate
    total_usd = freight_usd + demurrage_usd
    total_inr_cr = total_usd * spot_inr * fx_mult / 1e7
    pct = lambda a, q: float(np.percentile(a, q))  # noqa: E731
    hist, edges = np.histogram(total_inr_cr, bins=36)
    comp_var = {"freight": float(np.var(freight_usd)), "demurrage": float(np.var(demurrage_usd)), "currency": float(np.var(total_usd * (fx_mult - 1)))}
    tv = sum(comp_var.values()) or 1.0
    return {
        "origin": origin, "port": port_name, "cargo_tonnes": cargo_tonnes, "vessel_class": vessel_class, "runs": n,
        "base_freight_usd_per_t": round(base_freight, 2), "inr_per_usd": round(spot_inr, 2), "index_used": index_name, "index_data_through": str(idx.index[-1].date()),
        "percentiles_inr_crore": {q: round(pct(total_inr_cr, q), 2) for q in (5, 25, 50, 75, 90, 95)}, "mean_inr_crore": round(float(total_inr_cr.mean()), 2),
        "cost_at_risk_inr_crore": round(pct(total_inr_cr, 95) - pct(total_inr_cr, 50), 2),
        "histogram": {"counts": [int(c) for c in hist], "edges": [round(float(e), 3) for e in edges]},
        "share_of_variance_pct": {k: round(v / tv * 100, 1) for k, v in comp_var.items()},
        "prob_demurrage": round(float((demurrage_days > 0).mean()), 3), "expected_demurrage_usd": round(float(demurrage_usd.mean())),
        "assumptions": {"laytime_days": laytime_days, "demurrage_usd_per_day": rate, "storm_delay_days_each": 1.5, "voyage_fixed_30_days_ahead": True, "month": month},
        "method": "5,000 draws: freight = the illustrative route cost scaled by a bootstrap of real one-month moves of the USDA ocean rate (drift removed); currency from real 30-day INR/USD moves; demurrage from a lognormal port turnaround (real average) plus cyclone delay. The spread is historical, not a view on today.",
    }


# ------------------------------------------------------------------ lightering planner
HALDIA_CEILING_T = 35_000.0  # ASSUMED practical cargo per vessel at Haldia (published draft limit about 8.5 m); replace with SAIL's figure


def lightering_plan(db: Session, cargo_tonnes: float, barge_capacity_t: float = 6000, barge_cycle_days: float = 1.2, vessel_class: str = "Panamax") -> dict:
    lighten = max(0.0, cargo_tonnes - HALDIA_CEILING_T)
    trips = int(np.ceil(lighten / barge_capacity_t)) if lighten else 0
    return {
        "regression": None, "points": [], "draft_ceiling_m": 8.5, "max_cargo_at_ceiling_t": HALDIA_CEILING_T, "regression_cargo_at_ceiling_t": None, "fit_quality": "assumption",
        "cargo_tonnes": cargo_tonnes, "tonnes_to_lighten": round(lighten, -2), "barge_trips": trips, "lightering_days": round(trips * barge_cycle_days / 2, 1) if trips else 0.0,
        "parcels_of_median_size": int(np.ceil(cargo_tonnes / HALDIA_CEILING_T)), "median_parcel_t": HALDIA_CEILING_T,
        "assumptions": {"haldia_cargo_ceiling_t": HALDIA_CEILING_T, "barge_capacity_t": barge_capacity_t, "barge_cycle_days": barge_cycle_days, "two_barges_working": True},
        "method": "Haldia's shallow river draft (about 8.5 m) limits a vessel to roughly 35,000 t; anything above is lightened into barges at Sagar. The 35,000 t ceiling, the barge capacity and the cycle time are ASSUMPTIONS (the earlier data-driven fit used port reports whose licence is unclear and was removed); replace them with SAIL's own figures.",
    }


# ------------------------------------------------------------------ timing coach
def timing_coach(db: Session, port_name: str, origin: str, days: int = 60) -> dict:
    port = db.query(Port).filter(Port.name == port_name).first()
    r = (db.query(Route).join(Port, Route.origin_port_id == Port.id).filter(Port.country == origin, Route.destination_port_id == port.id).first()) if port else None
    transit = float(r.typical_transit_days) if r and r.typical_transit_days else 15.0
    today = date.today()
    cells = []
    for i in range(days):
        start = today + timedelta(days=i)
        cyc = cyclone_eta_risk(db, port_name, start, start + timedelta(days=6), transit)
        cells.append({"laycan_start": str(start), "storm_probability": cyc["probability_storm_in_window"], "expected_delay_days": cyc["expected_delay_days"]})
    for c in cells:
        c["score"] = round(1 - min(1.0, c["storm_probability"] * 2.5), 3)  # higher is better
    best = sorted(cells, key=lambda c: -c["score"])[:5]
    return {"port": port_name, "origin": origin, "transit_days": transit, "cells": cells, "best": best,
            "method": "For each possible laycan start, the historical chance of a Bay of Bengal storm within 400 km of the port during the arrival week (transit time added). Freight direction is not scored here; see the Verdict and the Forecast page for the market view.",
            "note": "Cyclone exposure is a long-run frequency by calendar month, so this ranks seasons, not specific weather."}


# ------------------------------------------------------------------ terrain
TERRAIN_SERIES = [("OCEAN_GULF_JAPAN", "Ocean rate Gulf"), ("OCEAN_PNW_JAPAN", "Ocean rate PNW"), ("DEEPSEA_PPI", "Freight PPI"), ("COAL_PPI", "Coal PPI"), ("BRENT", "Brent"), ("DXY", "Dollar idx"), ("INR", "INR/USD"), ("AUD", "AUD/USD")]


def terrain(db: Session) -> dict:
    frames = {}
    for key, _ in TERRAIN_SERIES:
        s = load_series(db, key)
        if not s.empty:
            frames[key] = s.resample("MS").mean()
    df = pd.DataFrame(frames).loc["2010-01-01":].dropna(how="all").ffill().bfill()
    z = (df - df.mean()) / df.std()
    return {"series": [{"key": k, "label": l} for k, l in TERRAIN_SERIES if k in z.columns], "months": [str(m.date()) for m in z.index],
            "z": [[round(float(v), 3) for v in z[k].values] for k, _ in TERRAIN_SERIES if k in z.columns],
            "method": "Monthly averages of public-domain series since 2010, each standardised over its own history (height is how many standard deviations above that series' own average)."}
