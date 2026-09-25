"""Voyage economics: carbon intensity per voyage (#15), INR/USD hedging overlay (#16) and the
rail-sea-rail modal comparison (#17). Assumed inputs are named and returned with each result."""

import math

import numpy as np
from sqlalchemy.orm import Session

from app.models import Port, Route
from app.services.freight_data import load_series
from app.services.recommendation import BASE_RATE_USD_PER_TONNE_PER_1000NM, VESSEL_CLASS_COST_MULTIPLIER, market_factor

# ---------------------------------------------------------------- carbon (IMO CII, bulk carriers)
REPRESENTATIVE_DWT = {"Capesize": 180_000, "Panamax": 80_000, "Supramax": 58_000, "Handysize": 35_000}
FUEL_T_PER_DAY_AT_SEA = {"Capesize": 50.0, "Panamax": 30.0, "Supramax": 26.0, "Handysize": 22.0}  # assumed, laden ~12 kn
CO2_T_PER_T_FUEL = {"VLSFO": 3.151, "HFO": 3.114, "MGO": 3.206}
CII_REDUCTION_PCT = {2023: 5, 2024: 7, 2025: 9, 2026: 11}
CII_BOUNDS = (0.86, 0.94, 1.06, 1.18)  # d1..d4 for bulk carriers


def cii_reference(dwt: float) -> float:
    """IMO reference line for bulk carriers, gCO2 per dwt-nm; capacity is capped at 279,000 dwt."""
    return 4745.0 * min(dwt, 279_000.0) ** -0.622


def carbon_estimate(db: Session, vessel_class: str, distance_nm: float, speed_knots: float = 12.0, fuel: str = "VLSFO",
                    year: int = 2026, include_ballast_return: bool = True, cargo_tonnes: float | None = None) -> dict:
    if vessel_class not in REPRESENTATIVE_DWT:
        raise ValueError(f"Unknown vessel class {vessel_class}")
    dwt = REPRESENTATIVE_DWT[vessel_class]
    laden_days = distance_nm / (speed_knots * 24)
    # Fuel scales roughly with speed cubed per day; the table is for ~12 knots.
    per_day = FUEL_T_PER_DAY_AT_SEA[vessel_class] * (speed_knots / 12.0) ** 3
    legs = 2 if include_ballast_return else 1
    fuel_t = per_day * laden_days * (1 + (0.9 if include_ballast_return else 0.0))  # ballast leg burns about 90% of laden
    co2_t = fuel_t * CO2_T_PER_T_FUEL[fuel]
    total_nm = distance_nm * legs
    aer = co2_t * 1e6 / (dwt * total_nm)
    ref = cii_reference(dwt)
    required = ref * (1 - CII_REDUCTION_PCT[year] / 100)
    ratio = aer / required
    d1, d2, d3, d4 = CII_BOUNDS
    rating = "A" if ratio < d1 else "B" if ratio < d2 else "C" if ratio <= d3 else "D" if ratio <= d4 else "E"
    cargo = cargo_tonnes or dwt * 0.9
    speeds = []
    for v in (10.0, 11.0, 12.0, 13.0, 14.0):
        pd_ = FUEL_T_PER_DAY_AT_SEA[vessel_class] * (v / 12.0) ** 3
        f = pd_ * (distance_nm / (v * 24)) * (1 + (0.9 if include_ballast_return else 0.0))
        a = f * CO2_T_PER_T_FUEL[fuel] * 1e6 / (dwt * total_nm)
        speeds.append({"speed_knots": v, "days": round(distance_nm / (v * 24), 1), "co2_t": round(f * CO2_T_PER_T_FUEL[fuel], 0), "aer": round(a, 3),
                       "rating": "A" if a / required < d1 else "B" if a / required < d2 else "C" if a / required <= d3 else "D" if a / required <= d4 else "E"})
    return {
        "vessel_class": vessel_class, "dwt_assumed": dwt, "laden_days": round(laden_days, 1), "fuel_t": round(fuel_t, 0), "co2_t": round(co2_t, 0),
        "co2_kg_per_tonne_cargo": round(co2_t * 1000 / cargo, 2), "attained_aer": round(aer, 3), "reference_aer": round(ref, 3), "required_aer": round(required, 3),
        "ratio_to_required": round(ratio, 3), "rating": rating, "year": year, "reduction_pct": CII_REDUCTION_PCT[year], "speed_sweep": speeds,
        "assumptions": {"fuel_t_per_day_at_12kn": FUEL_T_PER_DAY_AT_SEA[vessel_class], "co2_factor": CO2_T_PER_T_FUEL[fuel], "ballast_burn_share": 0.9 if include_ballast_return else 0,
                        "speed_law": "fuel per day scales with speed cubed", "representative_dwt": dwt},
        "note": "Indicative single-round-trip estimate on the IMO bulk-carrier reference line (a=4745, c=0.622, boundaries 0.86/0.94/1.06/1.18). A real CII rating is an annual figure per ship from measured fuel; consumption here is an assumed typical value, not a specific vessel's.",
    }


# ---------------------------------------------------------------- INR/USD hedging overlay
HEDGE_POLICY_CAP_PCT = 25.0  # SAIL annual report FY25: hedging of USD exposure up to 25% permitted


def hedge_overlay(db: Session, usd_cost: float, months: int = 6, hedge_ratio_pct: float = 25.0, inr_rate_pct: float = 6.5, usd_rate_pct: float = 4.3) -> dict:
    s = load_series(db, "INR")
    if s.empty or len(s) < 300:
        raise ValueError("Not enough INR/USD history")
    spot = float(s.iloc[-1])
    days = int(months * 30.4)
    logret = np.log(s).diff(days).dropna()
    sigma = float(np.log(s).diff().dropna().std() * math.sqrt(252) * math.sqrt(months / 12))  # horizon vol from daily vol
    empirical_p95 = float(np.percentile(logret, 95))
    fwd_premium = (inr_rate_pct - usd_rate_pct) / 100 * months / 12
    forward = spot * (1 + fwd_premium)
    h = hedge_ratio_pct / 100
    z = 1.645
    unhedged_worst = spot * math.exp(z * sigma)
    exp_unhedged = spot  # random-walk expectation
    exp_hedged = h * forward + (1 - h) * exp_unhedged
    worst_hedged = h * forward + (1 - h) * unhedged_worst
    out = {
        "spot_inr_per_usd": round(spot, 3), "spot_date": str(s.index[-1].date()), "horizon_months": months, "horizon_vol_pct": round(sigma * 100, 2),
        "empirical_p95_move_pct": round((math.exp(empirical_p95) - 1) * 100, 2), "forward_rate": round(forward, 3), "forward_premium_pct": round(fwd_premium * 100, 2),
        "usd_cost": usd_cost, "hedge_ratio_pct": hedge_ratio_pct,
        "unhedged": {"expected_inr": round(usd_cost * exp_unhedged), "worst_case_95_inr": round(usd_cost * unhedged_worst)},
        "hedged": {"expected_inr": round(usd_cost * exp_hedged), "worst_case_95_inr": round(usd_cost * worst_hedged)},
        "cost_of_hedge_inr": round(usd_cost * (exp_hedged - exp_unhedged)), "worst_case_saved_inr": round(usd_cost * (unhedged_worst - worst_hedged)),
        "policy_cap_pct": HEDGE_POLICY_CAP_PCT, "within_policy": hedge_ratio_pct <= HEDGE_POLICY_CAP_PCT,
        "assumptions": {"inr_interest_pct": inr_rate_pct, "usd_interest_pct": usd_rate_pct, "forward_premium_from": "interest-rate differential (covered interest parity)", "expectation": "unhedged expected rate = today's spot"},
        "note": "Volatility and the empirical 95th-percentile move come from the real FRED INR/USD series; interest rates are assumed inputs. SAIL's FY25 annual report says hedging of USD exposure up to 25% is permitted; ratios above that are flagged.",
    }
    return out


# ---------------------------------------------------------------- rail-sea-rail
PLANTS = ["Bokaro", "Durgapur", "IISCO (Burnpur)", "Rourkela", "Bhilai"]
# Approximate rail route distance, port to plant, km. ASSUMED planning figures, not Indian Railways tariff distances.
RAIL_KM = {
    "Haldia": {"Bokaro": 430, "Durgapur": 215, "IISCO (Burnpur)": 265, "Rourkela": 570, "Bhilai": 970},
    "Paradip": {"Bokaro": 640, "Durgapur": 700, "IISCO (Burnpur)": 730, "Rourkela": 380, "Bhilai": 720},
    "Dhamra": {"Bokaro": 690, "Durgapur": 620, "IISCO (Burnpur)": 640, "Rourkela": 430, "Bhilai": 830},
    "Visakhapatnam": {"Bokaro": 1250, "Durgapur": 1230, "IISCO (Burnpur)": 1300, "Rourkela": 780, "Bhilai": 690},
    "Gangavaram": {"Bokaro": 1255, "Durgapur": 1235, "IISCO (Burnpur)": 1305, "Rourkela": 785, "Bhilai": 695},
}
RAIL_INR_PER_TONNE_KM = 1.4
PORT_HANDLING_USD_PER_TONNE = 4.0


def modal_compare(db: Session, plant: str, origin_country: str, vessel_class: str = "Panamax", inr_per_usd: float | None = None,
                  rail_inr_per_tkm: float = RAIL_INR_PER_TONNE_KM, handling_usd: float = PORT_HANDLING_USD_PER_TONNE) -> dict:
    if plant not in PLANTS:
        raise ValueError(f"Unknown plant {plant}")
    if inr_per_usd is None:
        s = load_series(db, "INR")
        inr_per_usd = float(s.iloc[-1]) if not s.empty else 85.0
    mult = VESSEL_CLASS_COST_MULTIPLIER.get(vessel_class, 1.0) * market_factor(db)
    rows = []
    for port_name, km_map in RAIL_KM.items():
        port = db.query(Port).filter(Port.name == port_name).first()
        if not port:
            continue
        route = (db.query(Route).join(Port, Route.origin_port_id == Port.id)
                 .filter(Port.country == origin_country, Route.destination_port_id == port.id).first())
        if not route or not route.distance_nm:
            continue
        sea = BASE_RATE_USD_PER_TONNE_PER_1000NM * float(route.distance_nm) / 1000 * mult
        rail_usd = km_map[plant] * rail_inr_per_tkm / inr_per_usd
        rows.append({"port": port_name, "sea_usd_per_t": round(sea, 2), "handling_usd_per_t": handling_usd, "rail_km": km_map[plant], "rail_usd_per_t": round(rail_usd, 2),
                     "total_usd_per_t": round(sea + handling_usd + rail_usd, 2), "sea_share_pct": round(sea / (sea + handling_usd + rail_usd) * 100, 1)})
    rows.sort(key=lambda r: r["total_usd_per_t"])
    if rows:
        best = rows[0]["total_usd_per_t"]
        for r in rows:
            r["premium_vs_best_pct"] = round((r["total_usd_per_t"] / best - 1) * 100, 1)
    return {
        "plant": plant, "origin_country": origin_country, "vessel_class": vessel_class, "inr_per_usd": round(inr_per_usd, 2), "options": rows,
        "assumptions": {"rail_inr_per_tonne_km": rail_inr_per_tkm, "port_handling_usd_per_tonne": handling_usd, "rail_distances": "approximate planning figures, not railway tariff distances", "sea_cost": "illustrative distance-based estimate, as in the recommendation engine"},
        "note": "Compares landed cost to the plant across five discharge ports: sea freight (illustrative) + port handling + rail. Replace the rail distances and tariff with Indian Railways figures before relying on the ranking; the ranking is sensitive to them.",
    }
