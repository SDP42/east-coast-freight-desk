"""What-if and urgent-fixture engine. One deterministic landed-cost model with named levers, reused for scenario
comparison, one-at-a-time sensitivity (tornado), break-even solving and the last-minute fixture desk. Every assumed
parameter is returned with the result. Costs are illustrative estimates, not quotes."""

from dataclasses import dataclass, field, asdict
from datetime import date, timedelta

import time

import numpy as np
from sqlalchemy.orm import Session

from app.models import Port, Route, VesselClass
from app.services.compatibility import check_compatibility
from app.services.financial import DEMURRAGE_RATE_USD_PER_DAY
from app.services.freight_data import load_series
from app.services.recommendation import BASE_RATE_USD_PER_TONNE_PER_1000NM, VESSEL_CLASS_COST_MULTIPLIER
from app.services.signals import cyclone_eta_risk
from app.services import lab as lab_service

BUNKER_SHARE_OF_FREIGHT = 0.35      # assumed share of voyage freight that is fuel
BASE_SPEED_KNOTS = 12.0
LIGHTERING_USD_PER_TONNE = 3.5      # assumed floating-crane and barge cost at Sagar
PREP_DAYS = 3.0                     # assumed loading and documentation before sailing
BASE_URGENCY_PREMIUM_PCT = 4.0      # assumed spot premium for a normal booking
DEFAULT_LAYTIME_DAYS = 2.5


@dataclass
class Levers:
    origin: str = "Australia"
    port: str = "Haldia"
    cargo_tonnes: float = 75000
    vessel_class: str = "Panamax"
    freight_shock_pct: float = 0.0      # change in the freight rate
    inr_shock_pct: float = 0.0          # change in INR per USD (positive = rupee weaker)
    bunker_shock_pct: float = 0.0       # change in fuel price
    port_delay_days: float = 0.0        # extra waiting at the discharge port
    storm_delay_days: float = 0.0       # extra weather delay
    reroute_nm: float = 0.0             # extra sailing distance (e.g. Red Sea diversion)
    speed_knots: float = BASE_SPEED_KNOTS
    laytime_days: float = DEFAULT_LAYTIME_DAYS
    urgency_premium_pct: float = 0.0    # premium paid to secure a ship at short notice


@dataclass
class Outcome:
    levers: dict
    freight_usd: float = 0.0
    fuel_adjustment_usd: float = 0.0
    urgency_premium_usd: float = 0.0
    lightering_usd: float = 0.0
    demurrage_usd: float = 0.0
    total_usd: float = 0.0
    total_inr_crore: float = 0.0
    inr_per_usd: float = 0.0
    sailing_days: float = 0.0
    port_days: float = 0.0
    lightering_days: float = 0.0
    total_days: float = 0.0
    demurrage_days: float = 0.0
    freight_usd_per_t: float = 0.0
    notes: list[str] = field(default_factory=list)


_inr_cache: dict = {"t": 0.0, "v": 85.0}


def _inr_spot(db: Session) -> float:
    """Latest INR per USD, cached for ten minutes (the series has ~13,000 rows and is read for every option costed)."""
    if time.time() - _inr_cache["t"] > 600:
        s = load_series(db, "INR")
        _inr_cache.update(t=time.time(), v=float(s.iloc[-1]) if not s.empty else 85.0)
    return _inr_cache["v"]


def _route(db: Session, origin: str, port: Port) -> Route:
    r = db.query(Route).join(Port, Route.origin_port_id == Port.id).filter(Port.country == origin, Route.destination_port_id == port.id).first()
    if not r or not r.distance_nm:
        raise ValueError(f"No priced route from {origin} to {port.name}")
    return r


def landed_cost(db: Session, lv: Levers) -> Outcome:
    port = db.query(Port).filter(Port.name == lv.port, Port.is_destination.is_(True)).first()
    if not port:
        raise ValueError(f"Unknown port {lv.port}")
    if lv.vessel_class not in VESSEL_CLASS_COST_MULTIPLIER:
        raise ValueError(f"Unknown vessel class {lv.vessel_class}")
    route = _route(db, lv.origin, port)
    spot = _inr_spot(db)

    distance = float(route.distance_nm) + lv.reroute_nm
    base_rate = BASE_RATE_USD_PER_TONNE_PER_1000NM * distance / 1000 * VESSEL_CLASS_COST_MULTIPLIER[lv.vessel_class]
    rate = base_rate * (1 + lv.freight_shock_pct / 100)
    freight = rate * lv.cargo_tonnes

    # Fuel: the bunker share reacts to fuel price and to speed (burn per day scales with speed cubed, days with 1/speed).
    speed_factor = (lv.speed_knots / BASE_SPEED_KNOTS) ** 2  # cost per nm scales with speed squared
    fuel_part = freight * BUNKER_SHARE_OF_FREIGHT
    fuel_adj = fuel_part * ((1 + lv.bunker_shock_pct / 100) * speed_factor - 1)

    sailing_days = distance / (lv.speed_knots * 24) if lv.speed_knots else 0.0
    turnaround_days = float(port.avg_turnaround_hours or 49.5) / 24
    port_days = turnaround_days + lv.port_delay_days + lv.storm_delay_days

    ceiling = 35000.0  # assumed practical Haldia cargo ceiling (see lightering planner)
    lightering_usd, lightering_days, notes = 0.0, 0.0, []
    if port.name == "Haldia" and lv.cargo_tonnes > ceiling:
        excess = lv.cargo_tonnes - ceiling
        lightering_usd = excess * LIGHTERING_USD_PER_TONNE
        lightering_days = float(np.ceil(excess / 6000)) * 1.2 / 2
        notes.append(f"Haldia takes about {ceiling:,.0f} t per vessel, so {excess:,.0f} t is lightened at Sagar.")

    demurrage_days = max(0.0, port_days - lv.laytime_days)
    dem_rate = DEMURRAGE_RATE_USD_PER_DAY.get(lv.vessel_class, 8000)
    demurrage = demurrage_days * dem_rate
    premium = (freight + fuel_adj) * lv.urgency_premium_pct / 100

    total_usd = (freight + fuel_adj + premium) + lightering_usd + demurrage
    inr_rate = spot * (1 + lv.inr_shock_pct / 100)
    return Outcome(
        levers=asdict(lv), freight_usd=round(freight), fuel_adjustment_usd=round(fuel_adj), urgency_premium_usd=round(premium), lightering_usd=round(lightering_usd),
        demurrage_usd=round(demurrage), total_usd=round(total_usd), total_inr_crore=round(total_usd * inr_rate / 1e7, 3), inr_per_usd=round(inr_rate, 2),
        sailing_days=round(sailing_days, 1), port_days=round(port_days, 1), lightering_days=round(lightering_days, 1),
        total_days=round(PREP_DAYS + sailing_days + lightering_days + port_days, 1), demurrage_days=round(demurrage_days, 2), freight_usd_per_t=round(rate, 2), notes=notes,
    )


def what_if(db: Session, lv: Levers, base: Levers | None = None) -> dict:
    base = base or Levers(origin=lv.origin, port=lv.port, cargo_tonnes=lv.cargo_tonnes, vessel_class=lv.vessel_class)
    b, s = landed_cost(db, base), landed_cost(db, lv)
    parts = ("freight_usd", "fuel_adjustment_usd", "urgency_premium_usd", "lightering_usd", "demurrage_usd")
    return {"base": asdict(b), "scenario": asdict(s), "delta_usd": s.total_usd - b.total_usd, "delta_pct": round((s.total_inr_crore / b.total_inr_crore - 1) * 100, 1) if b.total_inr_crore else None,
            "delta_inr_crore": round(s.total_inr_crore - b.total_inr_crore, 3), "delta_days": round(s.total_days - b.total_days, 1),
            "breakdown": [{"part": p.replace("_usd", "").replace("_", " "), "base": getattr(b, p), "scenario": getattr(s, p)} for p in parts],
            "assumptions": {"bunker_share_of_freight": BUNKER_SHARE_OF_FREIGHT, "lightering_usd_per_t": LIGHTERING_USD_PER_TONNE, "prep_days": PREP_DAYS, "base_speed_knots": BASE_SPEED_KNOTS},
            "note": "Illustrative distance-based estimates, not quotes. Freight moves are applied to the route's illustrative rate; use them to compare scenarios, not to price a fixture."}


SENSITIVITY_STEPS = [
    ("Freight rate", "freight_shock_pct", -25.0, 25.0, "±25%"), ("Rupee vs dollar", "inr_shock_pct", -8.0, 8.0, "±8%"), ("Fuel price", "bunker_shock_pct", -30.0, 30.0, "±30%"),
    ("Port delay", "port_delay_days", 0.0, 5.0, "0 to +5 days"), ("Storm delay", "storm_delay_days", 0.0, 4.0, "0 to +4 days"), ("Reroute (Red Sea)", "reroute_nm", 0.0, 3500.0, "0 to +3,500 nm"),
    ("Urgency premium", "urgency_premium_pct", 0.0, 15.0, "0 to +15%"), ("Speed", "speed_knots", 10.0, 14.0, "10 to 14 knots"),
]


def sensitivity(db: Session, lv: Levers) -> dict:
    base = landed_cost(db, lv)
    rows = []
    for label, field_name, lo, hi, span in SENSITIVITY_STEPS:
        outs = []
        for v in (lo, hi):
            d = asdict(lv)
            d[field_name] = getattr(lv, field_name) + v if field_name not in ("speed_knots",) else v
            outs.append(landed_cost(db, Levers(**d)))
        lo_c, hi_c = outs[0].total_inr_crore, outs[1].total_inr_crore
        rows.append({"lever": label, "span": span, "low_inr_crore": round(lo_c - base.total_inr_crore, 3), "high_inr_crore": round(hi_c - base.total_inr_crore, 3),
                     "swing": round(abs(hi_c - lo_c), 3), "low_days": round(outs[0].total_days - base.total_days, 1), "high_days": round(outs[1].total_days - base.total_days, 1)})
    rows.sort(key=lambda r: -r["swing"])
    return {"base_inr_crore": base.total_inr_crore, "base_days": base.total_days, "rows": rows,
            "method": "Each lever is moved alone across its range while the others stay at your inputs; the bar shows the change in landed cost (INR crore). The longest bar is what matters most for this cargo."}


def breakeven(db: Session, a: Levers, b: Levers) -> dict:
    """Freight-rate change (applied to option A) at which A and B cost the same, by bisection."""
    cb = landed_cost(db, b).total_usd
    lo, hi = -80.0, 200.0
    f = lambda x: landed_cost(db, Levers(**{**asdict(a), "freight_shock_pct": x})).total_usd - cb  # noqa: E731
    if f(lo) > 0 or f(hi) < 0:
        return {"possible": False, "text": "No freight change within -80% to +200% makes the two options equal."}
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
    return {"possible": True, "freight_change_pct": round((lo + hi) / 2, 1),
            "text": f"Option A ({a.origin}) costs the same as option B ({b.origin}) if A's freight rate moves {round((lo + hi) / 2, 1):+}%."}


PLAYBOOKS = [
    {"key": "red_sea", "title": "Red Sea closes", "blurb": "Suez-bound cargoes divert around Africa; rates and distance jump.", "levers": {"reroute_nm": 3500, "freight_shock_pct": 12, "bunker_shock_pct": 8}},
    {"key": "cyclone", "title": "Cyclone off the coast", "blurb": "Weather closes the port for days; vessels queue and demurrage runs.", "levers": {"storm_delay_days": 4, "port_delay_days": 2}},
    {"key": "port_strike", "title": "Port strike", "blurb": "Berths idle for most of a week.", "levers": {"port_delay_days": 5}},
    {"key": "rupee", "title": "Rupee falls 6%", "blurb": "Dollar costs get more expensive in rupees overnight.", "levers": {"inr_shock_pct": 6}},
    {"key": "rate_spike", "title": "Freight spikes 30%", "blurb": "A 2021-style run-up in dry-bulk rates.", "levers": {"freight_shock_pct": 30}},
    {"key": "urgent", "title": "Need it in two weeks", "blurb": "A blast furnace is about to run short of coal: pay up for a ship and speed.", "levers": {"urgency_premium_pct": 10, "speed_knots": 13.5}},
    {"key": "perfect_storm", "title": "Perfect storm", "blurb": "Red Sea, fuel spike, weaker rupee and port congestion at once.", "levers": {"reroute_nm": 3500, "freight_shock_pct": 20, "bunker_shock_pct": 20, "inr_shock_pct": 5, "port_delay_days": 3}},
]


# ------------------------------------------------------------------ urgent fixture desk
def _availability(db: Session, port_name: str, cargo_tonnes: float, deadline_days: float) -> dict | None:
    """Open ships from the user's uploaded broker lists that could carry this cargo in time; None if no list has been uploaded."""
    from app.services import tonnage

    try:
        m = tonnage.match(db, port_name, cargo_tonnes, deadline_days)
    except ValueError:
        return None
    if not m["total_on_lists"]:
        return None
    return {"suitable_count": m["suitable_count"], "total_on_lists": m["total_on_lists"], "summary": m["summary"], "lists_stale": m["lists_stale"], "any_sample": m["any_sample"],
            "top": [{k: r[k] for k in ("vessel", "dwt", "class", "open_port", "eta", "status")} for r in m["matches"][:3]]}


def _size_ok(vc, cargo_tonnes: float) -> bool:
    """A parcel must suit the ship: not so small that a large ship sails part-empty, not more than the ship can carry."""
    return 0.75 * float(vc.dwt_min) <= cargo_tonnes <= 0.95 * float(vc.dwt_max)


def _berth_fit(port: Port, vc, cargo_tonnes: float) -> dict:
    """Fully-laden fit, or a part-laden call whose estimated capacity still covers the cargo."""
    r = check_compatibility(port, vc)
    if r.compatible:
        return {"fits": True, "part_laden": False, "note": ""}
    if r.partial_load_ok:
        cap = (float(vc.dwt_min) + float(vc.dwt_max)) / 2 * r.max_load_fraction * 0.95
        if cargo_tonnes <= cap:
            return {"fits": True, "part_laden": True, "note": f"part-laden (about {r.max_load_fraction:.0%} of deadweight)"}
        return {"fits": False, "part_laden": True, "note": f"part-laden capacity about {cap:,.0f} t is below the cargo"}
    return {"fits": False, "part_laden": False, "note": "draft or length too large for this port"}


def urgent_desk(db: Session, port_name: str, cargo_tonnes: float, deadline_days: float, seed: int = 5) -> dict:
    port = db.query(Port).filter(Port.name == port_name, Port.is_destination.is_(True)).first()
    if not port:
        raise ValueError(f"Unknown port {port_name}")
    rng = np.random.default_rng(seed)
    origins = ["Australia", "Indonesia", "Mozambique", "Russia", "United States"]
    vc_objs = {v.name: v for v in db.query(VesselClass).all()}
    classes = [c for c in ("Handysize", "Supramax", "Panamax", "Capesize") if c in VESSEL_CLASS_COST_MULTIPLIER and c in vc_objs]
    cyc = cyclone_eta_risk(db, port_name, date.today() + timedelta(days=int(deadline_days) - 3), date.today() + timedelta(days=int(deadline_days) + 3), 0)
    turn = float(port.avg_turnaround_hours or 49.5) / 24
    options = []
    for origin in origins:
        try:
            _route(db, origin, port)
        except ValueError:
            continue
        origin_port = db.query(Port).filter(Port.country == origin, Port.is_destination.is_(False)).first()  # the loading terminal
        for vc in classes:
            for speed in (12.0, 13.0, 14.0):
                fit = _berth_fit(port, vc_objs[vc], cargo_tonnes)
                if origin_port is not None and origin_port.max_draft_m is not None:
                    lf = _berth_fit(origin_port, vc_objs[vc], cargo_tonnes)  # the ship must also fit where it loads
                    fit = {"fits": fit["fits"] and lf["fits"], "part_laden": fit["part_laden"] or lf["part_laden"],
                           "note": "; ".join(x for x in (fit["note"], (f"at {origin_port.name}: " + lf["note"]) if lf["note"] else "") if x)}
                base = landed_cost(db, Levers(origin=origin, port=port_name, cargo_tonnes=cargo_tonnes, vessel_class=vc, speed_knots=speed))
                slack = deadline_days - base.total_days
                premium_pct = BASE_URGENCY_PREMIUM_PCT + max(0.0, 3.0 * (10 - slack)) if slack < 10 else BASE_URGENCY_PREMIUM_PCT
                out = landed_cost(db, Levers(origin=origin, port=port_name, cargo_tonnes=cargo_tonnes, vessel_class=vc, speed_knots=speed, urgency_premium_pct=round(min(premium_pct, 30.0), 1)))
                # Monte Carlo of arrival: port wait (lognormal around the real average) plus storm days.
                wait = rng.lognormal(np.log(turn), 0.35, 2000) + rng.poisson(cyc["expected_storm_days"] * 3, 2000) * 0.5
                arrival = out.total_days - out.port_days + wait
                p_on_time = float((arrival <= deadline_days).mean())
                options.append({
                    "origin": origin, "vessel_class": vc, "speed_knots": speed, "days": out.total_days, "slack_days": round(deadline_days - out.total_days, 1),
                    "p_on_time": round(p_on_time, 3), "total_inr_crore": out.total_inr_crore, "total_usd": out.total_usd, "freight_usd_per_t": out.freight_usd_per_t,
                    "urgency_premium_pct": out.levers["urgency_premium_pct"], "premium_usd": out.urgency_premium_usd, "demurrage_usd": out.demurrage_usd, "lightering_usd": out.lightering_usd,
                    "feasible": out.total_days <= deadline_days,
                    "fits_berth": fit["fits"], "part_laden": fit["part_laden"], "berth_note": fit["note"], "size_ok": _size_ok(vc_objs[vc], cargo_tonnes),
                    "coking_grade": origin != "Indonesia",
                })
    usable = lambda o: o["feasible"] and o["p_on_time"] >= 0.8 and o["fits_berth"] and o["coking_grade"] and o["size_ok"]  # noqa: E731
    feasible = [o for o in options if usable(o)]
    for o in options:
        o["score"] = round(o["total_inr_crore"] * (1 + (1 - o["p_on_time"]) * 2), 3)  # cost inflated by the risk of missing the date
    options.sort(key=lambda o: (not (o["fits_berth"] and o["coking_grade"] and o["size_ok"]), o["score"]))
    fastest = min([o for o in options if o["fits_berth"] and o["coking_grade"] and o["size_ok"]] or options, key=lambda o: o["days"])
    cheapest = min(feasible, key=lambda o: o["total_inr_crore"]) if feasible else None
    best = next((o for o in options if usable(o)), None)
    base_cost = min((o["total_usd"] for o in options), default=0)
    walk_away = None
    if best:
        walk_away = round(best["freight_usd_per_t"] * 1.12, 2)
    if best:
        verdict = (f"Best risk-adjusted option: {best['vessel_class']} from {best['origin']} at {best['speed_knots']:.0f} knots, arriving in about {best['days']} days "
                   f"({best['slack_days']} days of slack, {best['p_on_time']:.0%} chance on time) for ₹{best['total_inr_crore']} crore. Do not pay more than about ${walk_away}/t.")
    elif options:
        verdict = (f"No option reaches {port_name} within {deadline_days:g} days with an 80% chance. The fastest is {fastest['vessel_class']} from {fastest['origin']} at {fastest['speed_knots']:.0f} knots in {fastest['days']} days "
                   f"({fastest['p_on_time']:.0%} on time). Consider a partial cargo, stock from another source, or a later date.")
    else:
        verdict = "No priced routes to this port."
    return {"port": port_name, "cargo_tonnes": cargo_tonnes, "deadline_days": deadline_days, "storm_chance_in_window": cyc["probability_storm_in_window"], "verdict": verdict,
            "fastest": fastest, "cheapest_feasible": cheapest, "best": best, "walk_away_usd_per_t": walk_away, "options": options[:12], "options_evaluated": len(options), "feasible_count": len(feasible), "open_tonnage": _availability(db, port_name, cargo_tonnes, deadline_days),
            "method": "Every origin, vessel class and speed (12, 13, 14 knots) is costed with the What-If engine. The urgency premium is an assumed 4% plus 3 points for each day of slack below ten. On-time probability comes from 2,000 simulated arrivals (port wait lognormal around the real average turnaround, plus cyclone delay). Score = cost inflated by twice the chance of being late. Options whose vessel does not fit the berth, or whose origin ships mainly thermal coal (Indonesia), are listed but never recommended. The walk-away price is 12% above the recommended option's rate.",
            "_lab": bool(lab_service)}
