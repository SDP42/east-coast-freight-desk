"""Persona features that answer questions each role asks every quarter.

- programme_plan (Finance): the year's freight bill for a list of parcels, with a P5/P50/P95 budget range and the saving from
  moving volume between origins.
- resilience (Procurement): how concentrated the coking-coal sourcing is, and what each supplier disruption would cost.
- admin_analytics (Administrator): who uses which feature, and what is being refused.
All costs come from the same illustrative landed-cost model as the Urgent Desk and What-If Studio; they are not quotes.
"""

from collections import Counter
from datetime import datetime, timedelta

import numpy as np
from sqlalchemy.orm import Session

from app.models import AuditLog, User
from app.services.freight_data import load_series
from app.services.whatif import Levers, landed_cost

# Illustrative sourcing mix for coking coal into India (assumption). Public sources say Australia supplies more than half of
# India's roughly 70 Mt of coking-coal imports; the split of the rest is a placeholder the user should replace with SAIL's own.
DEFAULT_MIX = {"Australia": 0.55, "United States": 0.15, "Russia": 0.12, "Mozambique": 0.13, "Indonesia": 0.05}
DEFAULT_PROGRAMME = [
    {"origin": "Australia", "port": "Paradip", "cargo_tonnes": 75000, "vessel_class": "Panamax", "count": 10},
    {"origin": "Australia", "port": "Visakhapatnam", "cargo_tonnes": 75000, "vessel_class": "Panamax", "count": 6},
    {"origin": "United States", "port": "Paradip", "cargo_tonnes": 75000, "vessel_class": "Panamax", "count": 4},
    {"origin": "Mozambique", "port": "Visakhapatnam", "cargo_tonnes": 75000, "vessel_class": "Panamax", "count": 4},
]


def _shocks(db: Session, n: int, seed: int = 21) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    idx, inr = load_series(db, "BPI"), load_series(db, "INR")
    f = np.log(idx.where(idx > 0)).diff(90).dropna().iloc[-365 * 3:].to_numpy()  # last three years of the series, as in cost-at-risk
    x = np.log(inr.where(inr > 0)).diff(90).dropna().iloc[-365 * 3:].to_numpy()
    return np.exp(rng.choice(f, n) - f.mean()), np.exp(rng.choice(x, n) - x.mean())


def programme_plan(db: Session, parcels: list[dict] | None = None, n: int = 5000) -> dict:
    parcels = parcels or DEFAULT_PROGRAMME
    rows, freight_total, other_total = [], 0.0, 0.0
    inr = None
    for p in parcels:
        out = landed_cost(db, Levers(origin=p["origin"], port=p["port"], cargo_tonnes=p["cargo_tonnes"], vessel_class=p.get("vessel_class", "Panamax")))
        k = int(p.get("count", 1))
        inr = out.inr_per_usd
        freight_total += (out.freight_usd + out.fuel_adjustment_usd) * k
        other_total += (out.total_usd - out.freight_usd - out.fuel_adjustment_usd) * k
        rows.append({**p, "count": k, "per_parcel_inr_crore": out.total_inr_crore, "total_inr_crore": round(out.total_inr_crore * k, 2), "days": out.total_days})
    fm, xm = _shocks(db, n)
    total_cr = (freight_total * fm + other_total) * inr * xm / 1e7  # one freight draw applies to the whole year: freight moves together
    pc = lambda q: round(float(np.percentile(total_cr, q)), 2)  # noqa: E731
    base_cr = round(sum(r["total_inr_crore"] for r in rows), 2)
    by_origin: dict[str, float] = {}
    for r in rows:
        by_origin[r["origin"]] = round(by_origin.get(r["origin"], 0) + r["total_inr_crore"], 2)

    # What if half of the Australian parcels to Paradip moved to Mozambique?
    shift = None
    aus = next((r for r in rows if r["origin"] == "Australia" and r["port"] == "Paradip"), None)
    if aus:
        moved = aus["count"] // 2
        alt = landed_cost(db, Levers(origin="Mozambique", port="Paradip", cargo_tonnes=aus["cargo_tonnes"], vessel_class=aus["vessel_class"]))
        saving = moved * (aus["per_parcel_inr_crore"] - alt.total_inr_crore)
        shift = {"moved_parcels": moved, "from": "Australia", "to": "Mozambique", "port": "Paradip", "saving_inr_crore": round(saving, 2), "days_change_per_parcel": round(alt.total_days - aus["days"], 1),
                 "caution": "Cost only. Mozambique coal differs in quality and supply reliability; check the blend before shifting volume."}
    return {
        "parcels": rows, "base_inr_crore": base_cr, "by_origin_inr_crore": by_origin,
        "budget_range_inr_crore": {"p5": pc(5), "p50": pc(50), "p95": pc(95)}, "budget_to_hold_inr_crore": pc(95), "overrun_risk_inr_crore": round(pc(95) - base_cr, 2),
        "shift_scenario": shift, "runs": n,
        "method": "Base = illustrative landed cost per parcel x number of parcels. Range = 5,000 draws where one bootstrap of real 90-day freight moves and one of real 90-day rupee moves are applied to the whole year (freight moves together, so parcels do not diversify away the risk). The freight history ends July 2019, so the spread is historical, not a view on today.",
    }


def resilience(db: Session, mix: dict[str, float] | None = None, port: str = "Paradip", cargo_tonnes: float = 75000) -> dict:
    mix = mix or DEFAULT_MIX
    total = sum(mix.values()) or 1.0
    share = {k: v / total for k, v in mix.items()}
    hhi = sum(s * s for s in share.values())
    cost = {}
    for o in share:
        try:
            cost[o] = landed_cost(db, Levers(origin=o, port=port, cargo_tonnes=cargo_tonnes)).total_inr_crore
        except ValueError:
            continue
    avg = sum(share[o] * cost[o] for o in cost) / sum(share[o] for o in cost)
    stress = []
    for o in cost:
        rest = {k: v for k, v in share.items() if k != o and k in cost}
        rs = sum(rest.values())
        if rs <= 0:
            continue
        new_avg = sum(rest[k] / rs * cost[k] for k in rest)
        stress.append({"lost_origin": o, "share_lost_pct": round(share[o] * 100, 1), "avg_cost_per_parcel_inr_crore": round(new_avg, 3), "freight_cost_change_pct": round((new_avg / avg - 1) * 100, 1),
                       "volume_to_replace_pct": round(share[o] * 100, 1)})
    stress.sort(key=lambda r: -r["share_lost_pct"])
    biggest = max(share, key=share.get)
    score = round((1 - hhi) * 100)
    label = "Concentrated" if hhi > 0.25 else "Moderate" if hhi > 0.15 else "Diversified"  # usual HHI bands on a 0 to 1 scale
    tip = f"{biggest} supplies {share[biggest]:.0%} of the mix. Losing it would force {share[biggest]:.0%} of volume onto other origins."
    return {
        "port": port, "mix_pct": {k: round(v * 100, 1) for k, v in share.items()}, "hhi": round(hhi, 3), "effective_suppliers": round(1 / hhi, 2), "diversification_score": score, "label": label,
        "stress": stress, "headline": tip,
        "assumption": "The mix is an illustrative placeholder (public reports say Australia supplies more than half of India's roughly 70 Mt coking-coal imports); enter SAIL's own shares. Stress costs are freight-only, so losing a dear origin can look cheaper; that ignores coal quality, price and availability, and the real risk is the volume that must be replaced.",
    }


def admin_analytics(db: Session, days: int = 14) -> dict:
    since = datetime.utcnow() - timedelta(days=days)
    rows = db.query(AuditLog).filter(AuditLog.created_at >= since).all()
    by_action = Counter(r.action for r in rows)
    by_role = Counter((r.role or "anonymous") for r in rows)
    denied = [r for r in rows if not r.allowed]
    per_day = Counter(r.created_at.date().isoformat() for r in rows)
    active = {r.email for r in rows if r.email}
    refused_by = Counter(f"{r.role or 'anonymous'}: {r.action}" for r in denied)
    return {
        "window_days": days, "events": len(rows), "active_users": len(active), "total_accounts": db.query(User).count(),
        "denied": len(denied), "denied_rate_pct": round(len(denied) / len(rows) * 100, 1) if rows else 0.0,
        "by_action": by_action.most_common(10), "by_role": by_role.most_common(), "per_day": sorted(per_day.items()),
        "top_refusals": refused_by.most_common(8),
        "note": "Counts come from the audit log; the demo accounts generate most of the activity in a demonstration.",
    }
