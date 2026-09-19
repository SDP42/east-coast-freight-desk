"""Port signals: cyclone-adjusted ETA risk and the cargo demand estimator. Derived from public-domain data in the database
(NOAA IBTrACS-derived exposure, SAIL annual-report figures); assumed parameters are named and returned with each result."""

from datetime import date, timedelta

import numpy as np
from sqlalchemy.orm import Session

from app.models import CycloneExposure, Port

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


# SAIL annual-report figures (crude steel and imported coking coal, MT): the two data points the demand estimate is calibrated on.
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
