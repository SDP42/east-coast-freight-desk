"""Monthly coking-coal allocation optimiser: which origin, through which port, to which plant.

A linear program (scipy HiGHS). Minimise landed cost (sea freight + port handling + rail) subject to each plant's monthly
need, each port's monthly capacity for SAIL cargo, and a cap on each origin's share (supply and concentration limits).
It also returns the SHADOW PRICES: what one more tonne of port capacity, or one more point of an origin's cap, is worth.

Every input below is an ASSUMPTION the user should replace with SAIL's own; costs use the same illustrative landed-cost
model as the rest of the desk (not quotes), and rail distances are the planning figures in services/voyage.py.
"""

import numpy as np
from scipy.optimize import linprog
from sqlalchemy.orm import Session

from app.services.voyage import PORT_HANDLING_USD_PER_TONNE, RAIL_INR_PER_TONNE_KM, RAIL_KM
from app.services.whatif import Levers, _inr_spot, landed_cost

ORIGINS = ["Australia", "United States", "Mozambique", "Russia"]  # coking-grade origins (Indonesia is mainly thermal)
DEFAULT_DEMAND_KT = {"Bhilai": 420, "Bokaro": 280, "Rourkela": 280, "Durgapur": 220, "IISCO (Burnpur)": 200}  # kt per month, assumed
DEFAULT_PORT_CAP_KT = {"Haldia": 250, "Paradip": 500, "Dhamra": 300, "Visakhapatnam": 350, "Gangavaram": 350}  # kt per month for SAIL, assumed
DEFAULT_MAX_SHARE = {"Australia": 0.60, "United States": 0.25, "Mozambique": 0.15, "Russia": 0.20}  # assumed supply and concentration caps
BASELINE_MIX = {"Australia": 0.55, "United States": 0.15, "Mozambique": 0.13, "Russia": 0.12}  # assumed current mix


def _lane_costs(db: Session, vessel_class: str) -> dict[tuple[str, str], float]:
    """Sea landed cost per tonne in INR for each origin and port (75,000 t Panamax parcel; Haldia includes lightering)."""
    inr = _inr_spot(db)
    out = {}
    for o in ORIGINS:
        for p in DEFAULT_PORT_CAP_KT:
            try:
                r = landed_cost(db, Levers(origin=o, port=p, cargo_tonnes=75000, vessel_class=vessel_class))
            except ValueError:
                continue
            out[(o, p)] = r.total_usd / 75000 * inr + PORT_HANDLING_USD_PER_TONNE * inr
    return out


def optimise(db: Session, demand_kt: dict[str, float] | None = None, port_cap_kt: dict[str, float] | None = None, max_share: dict[str, float] | None = None,
             vessel_class: str = "Panamax") -> dict:
    demand = demand_kt or DEFAULT_DEMAND_KT
    cap = port_cap_kt or DEFAULT_PORT_CAP_KT
    share = max_share or DEFAULT_MAX_SHARE
    sea = _lane_costs(db, vessel_class)
    plants = [k for k in demand if any(k in RAIL_KM[p] for p in RAIL_KM)]
    total = sum(demand[k] for k in plants)
    var = [(o, p, k) for (o, p) in sea if p in cap for k in plants if k in RAIL_KM.get(p, {})]
    cost = np.array([sea[(o, p)] + RAIL_KM[p][k] * RAIL_INR_PER_TONNE_KM for o, p, k in var])  # INR per tonne
    idx = {v: i for i, v in enumerate(var)}
    n = len(var)
    A_eq, b_eq = [], []
    for k in plants:
        row = np.zeros(n)
        for v, i in idx.items():
            if v[2] == k:
                row[i] = 1
        A_eq.append(row); b_eq.append(demand[k])
    A_ub, b_ub, labels = [], [], []
    for p in cap:
        row = np.zeros(n)
        for v, i in idx.items():
            if v[1] == p:
                row[i] = 1
        A_ub.append(row); b_ub.append(cap[p]); labels.append(("port", p))
    for o in share:
        row = np.zeros(n)
        for v, i in idx.items():
            if v[0] == o:
                row[i] = 1
        A_ub.append(row); b_ub.append(share[o] * total); labels.append(("origin", o))
    res = linprog(cost, A_ub=np.array(A_ub), b_ub=b_ub, A_eq=np.array(A_eq), b_eq=b_eq, bounds=(0, None), method="highs")
    if not res.success:
        return {"feasible": False, "message": "The limits cannot be met together: total port capacity or the origin caps are too tight for the plants' need.", "total_demand_kt": total,
                "total_port_capacity_kt": sum(cap.values()), "max_origin_share_sum": round(sum(share.values()), 2)}
    x = res.x
    alloc = [{"origin": o, "port": p, "plant": k, "kt": round(float(x[i]), 1), "landed_inr_per_t": round(float(cost[i]))} for i, (o, p, k) in enumerate(var) if x[i] > 0.5]
    alloc.sort(key=lambda r: -r["kt"])
    monthly_cr = float(res.fun) * 1000 / 1e7  # x is in kt, cost in INR per tonne -> INR
    # Baseline: the same LP but with the origin mix fixed to the assumed current mix (equality), so the only freedom is routing
    # through ports and plants within the same port capacities. The saving is what freeing the origin mix is worth.
    A_eq2, b_eq2 = list(A_eq), list(b_eq)
    mix_total = sum(BASELINE_MIX.values())
    for o, sh in BASELINE_MIX.items():
        row = np.zeros(n)
        for v, i in idx.items():
            if v[0] == o:
                row[i] = 1
        A_eq2.append(row); b_eq2.append(sh / mix_total * total)  # shares normalised to sum to one
    A_ub2 = [r for r, lab in zip(A_ub, labels) if lab[0] == "port"]
    b_ub2 = [v for v, lab in zip(b_ub, labels) if lab[0] == "port"]
    bres = linprog(cost, A_ub=np.array(A_ub2), b_ub=b_ub2, A_eq=np.array(A_eq2), b_eq=b_eq2, bounds=(0, None), method="highs")
    base = float(bres.fun) if bres.success else float("nan")
    base_cr = base * 1000 / 1e7
    by_o, by_p = {}, {}
    for a in alloc:
        by_o[a["origin"]] = by_o.get(a["origin"], 0) + a["kt"]
        by_p[a["port"]] = by_p.get(a["port"], 0) + a["kt"]
    shares = np.array([v / total for v in by_o.values()])
    duals = res.ineqlin.marginals
    binding = []
    for (kind, name), d, rhs, used in zip(labels, duals, b_ub, [float((np.array(A_ub[i]) * x).sum()) for i in range(len(labels))]):
        if used >= rhs - 0.5 and abs(d) > 1e-6:
            # one more kt of capacity (or of allowed share) changes the monthly cost by d INR per tonne x 1,000 t
            binding.append({"limit": f"{kind} {name}", "kind": kind, "name": name, "used_kt": round(used, 1), "limit_kt": round(rhs, 1),
                            "saving_inr_lakh_per_extra_kt_per_month": round(float(-d) * 1000 / 1e5, 2)})
    binding.sort(key=lambda r: -r["saving_inr_lakh_per_extra_kt_per_month"])
    saving = base_cr - monthly_cr
    return {
        "feasible": True, "vessel_class": vessel_class, "total_demand_kt": total, "monthly_cost_inr_crore": round(monthly_cr, 2), "baseline_cost_inr_crore": None if base_cr != base_cr else round(base_cr, 2),
        "saving_inr_crore_per_month": round(saving, 2), "saving_pct": round(saving / base_cr * 100, 1) if base_cr == base_cr and base_cr else 0.0, "saving_inr_crore_per_year": round(saving * 12, 1),
        "avg_landed_inr_per_t": round(monthly_cr * 1e7 / (total * 1000)), "allocation": alloc, "by_origin_kt": {k: round(v, 1) for k, v in sorted(by_o.items(), key=lambda t: -t[1])},
        "by_port_kt": {k: round(v, 1) for k, v in sorted(by_p.items(), key=lambda t: -t[1])},
        "hhi": round(float((shares ** 2).sum()), 3), "binding_limits": binding,
        "assumptions": {"plant_demand_kt_per_month": demand, "port_capacity_kt_per_month": cap, "max_origin_share": share, "baseline_mix": BASELINE_MIX,
                        "rail_inr_per_tonne_km": RAIL_INR_PER_TONNE_KM, "handling_usd_per_t": PORT_HANDLING_USD_PER_TONNE},
        "method": "Linear program (HiGHS) minimising sea + port + rail cost per tonne. Baseline keeps the assumed current origin mix and routes it as cheaply as the same port capacities allow; the saving is what freeing the origin mix is worth. Coal quality, price differences between origins and contract volumes are NOT modelled: this finds the cheapest logistics, not the cheapest coal. Every input is an assumption to replace with SAIL's own.",
    }
