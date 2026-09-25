"""'Ask the Freight Desk': routes a question to one of the platform's engines and answers in a short
broker-style briefing with the numbers used. No free-text generation and no external service: the
intent comes from the local classifier in app.ml.intent, the figures from the same services the
dashboard uses."""

import re

from dataclasses import dataclass, field

import numpy as np
from sqlalchemy.orm import Session

from app.core.permissions import PERMISSION_LABELS, ROLES, assigned_ports, has, permissions_of, port_scope, role_of
from app.ml.intent import Entities, classify, extract_entities
from app.models import AlertEvent, AlertRule, AuditLog, LedgerEntry, Port, User, VesselClass
from app.services import whatif as whatif_service
from app.services.compatibility import check_compatibility
from app.services.freight_data import load_series
from app.services.quick_forecast import quick_forecast
from app.services.recommendation import MarketSignal, compare_origins
from app.services.audit import record
from app.services.risk import _congestion_score, compute_route_risk

CONFIDENCE_FLOOR = 0.35
DEFAULT_ORIGINS = ["Australia", "United States", "Mozambique", "Russia", "Indonesia"]
INDEX_LABEL = {"OCEAN_GULF_JAPAN": "the USDA grain ocean rate, US Gulf to Japan", "OCEAN_PNW_JAPAN": "the USDA grain ocean rate, Pacific NW to Japan"}
CLASS_INDEX: dict[str, str] = {}
PRIMARY = "OCEAN_GULF_JAPAN"
HALDIA_FACTS = {"lock_length_m": 330, "lock_width_m": 39, "sandheads_distance_km": 130, "transit_hours_sandheads_to_jetty": 6, "coal_berth_4a_unloaders": 2, "coal_berth_4a_rate_t_per_day": 14000, "cargo_ceiling_t": 35000}

SUGGESTIONS = [
    "What will the ocean freight rate do over the next 3 months?",
    "Cheapest origin for 75,000 t to Paradip?",
    "How risky is Australia to Haldia?",
    "Can a Capesize berth at Haldia?",
    "Which port is most congested?",
    "Should we use a COA or stay spot?",
    "How does the lock at Haldia work?",
    "How much coking coal does SAIL import?",
]


@dataclass
class Answer:
    intent: str
    confidence: float
    alternatives: list[tuple[str, float]]
    entities: dict
    text: str
    figures: list[tuple[str, str]] = field(default_factory=list)
    links: list[tuple[str, str]] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    denied: bool = False
    scope: str = ""


class AccessDenied(Exception):
    pass


def _port(db: Session, name: str | None, assumptions: list[str], default: str = "Haldia", user=None) -> Port:
    scope = port_scope(user) if user is not None else None
    if scope is not None:
        if not scope:
            raise AccessDenied("No ports are assigned to your account yet, so there is nothing port-specific I can show. Ask an administrator to assign your ports.")
        if name and name not in scope:
            raise AccessDenied(f"{name} is outside the ports assigned to your account ({', '.join(scope)}), so I cannot show it.")
        if not name:
            default = scope[0]
    chosen = name or default
    if not name:
        assumptions.append(f"No port named, so I assumed {default}" + (" (your assigned port)." if scope else "."))
    return db.query(Port).filter(Port.name == chosen, Port.is_destination.is_(True)).one()


def _stale(idx: str, last_date: str) -> str:
    return f" Note: our {idx} series ends {last_date}, so this is not today's market." if last_date < "2026-01-01" else ""


def _pct(x: float) -> str:
    return f"{x:+.1f}%"


def _market_now(db: Session, e: Entities, a: list[str], user=None) -> Answer:
    idx = e.index_name or PRIMARY
    s = load_series(db, idx)
    if s.empty:
        return Answer("market_now", 0, [], {}, f"I have no data for {idx}.")
    last, d = float(s.iloc[-1]), s.index[-1].date()
    m1 = (last / float(s.iloc[-2]) - 1) * 100 if len(s) > 2 else 0.0
    m3 = (last / float(s.iloc[-4]) - 1) * 100 if len(s) > 4 else 0.0
    pctile = float((s < last).mean() * 100)
    cv = float(s.iloc[-12:].std() / s.iloc[-12:].mean() * 100)
    regime = "cheap by its own history" if pctile < 30 else "expensive by its own history" if pctile > 70 else "mid-range for its history"
    label = INDEX_LABEL.get(idx, idx)
    text = (f"{label[0].upper() + label[1:]} was ${last:,.2f} a tonne in {d:%B %Y}. That is {_pct(m1)} over a month and {_pct(m3)} over three months, "
            f"and {regime} (higher than {pctile:.0f}% of {len(s):,} monthly readings). The last 12 months swung {cv:.0f}% around their mean. It is a public-domain dry-bulk proxy (US grain routes), not a coal rate.")
    return Answer("market_now", 0, [], {}, text,
                  [("Latest", f"${last:,.2f}/t"), ("1 month", _pct(m1)), ("3 months", _pct(m3)), ("History percentile", f"{pctile:.0f}%")],
                  [("Open the live board", "/app/markets")])


def _forecast(db: Session, e: Entities, a: list[str], user=None) -> Answer:
    idx = e.index_name or PRIMARY
    h = max(1, round(e.horizon_days / 30)) if e.horizon_days else 3
    if not e.horizon_days:
        a.append("No horizon given, so I used 3 months.")
    f = quick_forecast(db, idx, h)
    if f is None:
        return Answer("forecast", 0, [], {}, f"Not enough {idx} history to forecast.")
    span = (f.upper - f.lower) / 2 / f.last_value * 100
    direction = "drift up" if f.change_pct > 1 else "drift down" if f.change_pct < -1 else "stay roughly flat"
    text = (f"ARIMA(2,1,2) has {INDEX_LABEL.get(idx, idx)} going from ${f.last_value:,.2f} ({f.last_date}) to about ${f.forecast_end:,.2f} in {h} month(s), "
            f"a move of {_pct(f.change_pct)}: it should {direction}. The 95% band ({f.band_method}) runs ${f.lower:,.2f} to ${f.upper:,.2f} (about ±{span:.0f}%). "
            "Tests show no model reliably beats assuming no change, so treat direction with caution.")
    return Answer("forecast", 0, [], {}, text,
                  [("Now", f"${f.last_value:,.2f}"), (f"In {h} mo", f"${f.forecast_end:,.2f}"), ("Change", _pct(f.change_pct)), ("95% band", f"${f.lower:,.0f}–${f.upper:,.0f}")],
                  [("Full forecast with backtest", "/app/forecast")], a)


def _recommend(db: Session, e: Entities, a: list[str], user=None) -> Answer:
    port = _port(db, e.port, a, "Paradip", user)
    cargo = e.cargo_tonnes or 75_000
    if not e.cargo_tonnes:
        a.append("No cargo size given, so I used 75,000 t.")
    origins = [e.origin] if False else DEFAULT_ORIGINS
    cls = db.query(VesselClass).all()
    sig = MarketSignal("OCEAN_GULF_JAPAN", None, None)
    res = compare_origins(db, port, cargo, origins, market_signal=sig)
    ranked = [r for r in res if r.estimated_freight_usd_per_tonne is not None]
    if not ranked:
        return Answer("recommend_origin", 0, [], {}, "No priced routes to that port yet.")
    best = ranked[0]
    lines = ", ".join(f"{r.origin_country} ${r.estimated_freight_usd_per_tonne:.0f}/t" for r in ranked[:4])
    fit = "and the vessel fits the berth" if best.compatibility.compatible else "but the vessel does NOT fit that port as is, so plan lightering or a smaller class"
    text = (f"For {cargo:,.0f} t into {port.name}, {best.origin_country} ranks first at about ${best.estimated_freight_usd_per_tonne:.0f}/t on a {best.vessel_class.name}, {fit}. "
            f"Ranking: {lines}. This ranks freight only, from illustrative distance-based estimates rather than live quotes. "
            "Cargo quality matters as much: Indonesian coal is mostly thermal (India's 2024 import value was about $77/t versus $229/t from Australia), so it rarely substitutes for coking coal.")
    _ = cls
    return Answer("recommend_origin", 0, [], {}, text,
                  [("Best origin", best.origin_country), ("Vessel", best.vessel_class.name), ("Est. freight", f"${best.estimated_freight_usd_per_tonne:.0f}/t")],
                  [("Compare origins in full", "/app/recommendation")], a)


def _port_fit(db: Session, e: Entities, a: list[str], user=None) -> Answer:
    port = _port(db, e.port, a, "Haldia", user)
    classes = db.query(VesselClass).order_by(VesselClass.dwt_min).all()
    ok, no = [], []
    for vc in classes:
        (ok if check_compatibility(port, vc).compatible else no).append(vc.name)
    draft_txt = f"allows up to {port.max_draft_m} m draft and" if port.max_draft_m else "has no fixed draft on file (it is tide-dependent) and"
    text = f"{port.name} {draft_txt} up to {port.max_loa_m} m LOA. Classes that pass all checks: {', '.join(ok) or 'none'}. "
    if no:
        text += f"Do not fit as designed: {', '.join(no)}."
    figs = [("Max draft", f"{port.max_draft_m} m" if port.max_draft_m else "tide-dependent"), ("Max LOA", f"{port.max_loa_m} m"), ("Accepted", ", ".join(ok) or "none")]
    if port.name == "Haldia":
        text += f" In practice a vessel carries about {HALDIA_FACTS['cargo_ceiling_t']:,} t up the river (an assumed planning ceiling), because larger ships are lightened at Sagar first."
    return Answer("port_fit", 0, [], {}, text, figs, [("Open the berth-fit checker", "/app/ports")], a)


def _risk(db: Session, e: Entities, a: list[str], user=None) -> Answer:
    port = _port(db, e.port, a, "Haldia", user)
    origin = e.origin or "Australia"
    if not e.origin:
        a.append("No origin named, so I assumed Australia.")
    r = compute_route_risk(db, origin, port)
    top = max(r.factors, key=lambda f: f.score * f.weight)
    text = (f"{origin} to {port.name} scores {r.composite_score:.1f}/10, {r.risk_label.lower()}. The biggest contributor is {top.name.replace('_', ' ')} "
            f"({top.score:.1f}/10): {top.detail}.")
    if r.relevant_events:
        ev = r.relevant_events[0]
        text += f" Most relevant documented event: {ev.title}."
    return Answer("risk", 0, [], {}, text,
                  [("Composite", f"{r.composite_score:.1f}/10"), ("Label", r.risk_label)] + [(f.name.replace("_", " "), f"{f.score:.1f}") for f in r.factors],
                  [("See the full risk breakdown", "/app/risk")], a)


def _congestion(db: Session, e: Entities, a: list[str], user=None) -> Answer:
    ports = db.query(Port).filter(Port.is_destination.is_(True)).all()
    scope = port_scope(user) if user is not None else None
    if scope is not None:
        ports = [p for p in ports if p.name in scope]
        if not ports:
            raise AccessDenied("No ports are assigned to your account yet.")
        if e.port and e.port not in scope:
            raise AccessDenied(f"{e.port} is outside the ports assigned to your account ({', '.join(scope)}).")
    scored = sorted(((_congestion_score(p, db), p) for p in ports), key=lambda t: -t[0][0])
    if e.port and any(t[1].name == e.port for t in scored):
        (s, detail), p = next(t for t in scored if t[1].name == e.port)
        return Answer("congestion", 0, [], {}, f"{p.name} congestion scores {s:.1f}/10. {detail}.", [("Score", f"{s:.1f}/10")], [("Ports and berths", "/app/ports")], a)
    (s0, d0), p0 = scored[0]
    (s1, _), p1 = scored[-1]
    if len(scored) == 1:
        return Answer("congestion", 0, [], {}, f"{p0.name} congestion scores {s0:.1f}/10. {d0}.", [("Score", f"{s0:.1f}/10")], [("Port signals", "/app/signals")], a)
    text = (f"{p0.name} is the most congested at {s0:.1f}/10 ({d0}). {p1.name} is the calmest at {s1:.1f}/10. "
            "Scores use the Ministry of Ports' average turnaround; ports without official turnaround data get a default.")
    return Answer("congestion", 0, [], {}, text, [(p.name, f"{sc[0]:.1f}") for sc, p in scored[:5]], [("Open the port map", "/app/map")], a)


def _haldia(db: Session, e: Entities, a: list[str], user=None) -> Answer:
    f = HALDIA_FACTS
    text = (f"Haldia is an impounded dock: ships pass a {f['lock_length_m']} m by {f['lock_width_m']} m lock. It sits about {f['sandheads_distance_km']} km from Sandheads, "
            f"roughly {f['transit_hours_sandheads_to_jetty']} hours' passage. Big ships are lightened by floating cranes at Sagar or Sandheads, so a vessel reaches the dock with about {f['cargo_ceiling_t']:,} t (an assumed ceiling). "
            f"Berth 4A has {f['coal_berth_4a_unloaders']} grab unloaders at about {f['coal_berth_4a_rate_t_per_day']:,} t/day.")
    return Answer("haldia", 0, [], {}, text, [("Lock", f"{f['lock_length_m']} x {f['lock_width_m']} m"), ("Cargo ceiling", f"{f['cargo_ceiling_t']:,} t"), ("Berth 4A", f"{f['coal_berth_4a_rate_t_per_day']:,} t/day")], [("Back to the Haldia scene", "/")], a)


def _coa(db: Session, e: Entities, a: list[str], user=None) -> Answer:
    idx = e.index_name or PRIMARY
    s = load_series(db, idx)
    f = quick_forecast(db, idx, 3)
    cv = float(s.iloc[-12:].std() / s.iloc[-12:].mean() * 100) if len(s) > 12 else 0
    if f is None:
        return Answer("coa_vs_spot", 0, [], {}, "Not enough history to compare.")
    lean = "lean towards locking a contract" if (f.change_pct > 2 or cv > 25) else "spot is reasonable for now"
    text = (f"Rule of thumb from the data: {INDEX_LABEL.get(idx, idx)} is projected {_pct(f.change_pct)} over 3 months and its 12-month swing is {cv:.0f}% of the mean, so I would {lean}. "
            "A contract of affreightment fixes the rate for several voyages, which pays when the market is expected to rise or is very volatile, and costs you if it falls. "
            "The Financial Tools page simulates the exact savings with your cargo and interval." + _stale(idx, str(s.index[-1].date())))
    return Answer("coa_vs_spot", 0, [], {}, text, [("3-month outlook", _pct(f.change_pct)), ("12-month volatility", f"{cv:.0f}%")], [("Run the COA vs spot simulator", "/app/financial")], a)


def _demand(db: Session, e: Entities, a: list[str], user=None) -> Answer:
    text = ("From SAIL's annual reports, clean coking coal use was 19.37 MT in FY24 with 16.92 MT imported (about 87%), and 18.74 MT in FY25 with 16.32 MT imported. "
            "SAIL's Q1 FY27 crude steel was 4.757 MT, so roughly 4 MT of imported coking coal a quarter, or about 120 lots of 33,000 t a quarter if it all moved in Haldia-sized parcels. "
            "The CAG audit found 94% of imported coal arrived under long-term agreements (FY17-FY23) through Visakhapatnam, Gangavaram, Paradip, Dhamra and Haldia.")
    return Answer("demand", 0, [], {}, text, [("Imported share", "~87%"), ("FY25 imported", "16.32 MT"), ("Q1 FY27 crude steel", "4.757 MT")], [], a)


def _sources(db: Session, e: Entities, a: list[str], user=None) -> Answer:
    text = ("Only public-domain data, fetched free with no accounts or keys: the USDA monthly grain ocean rates (a dry-bulk freight proxy), US BLS deep-sea freight and coal price indices, US EIA Brent crude, "
            "Federal Reserve exchange rates and dollar index, NOAA IBTrACS cyclone tracks, and the Ministry of Ports turnaround figures. Ship availability comes from broker open-tonnage lists you upload. "
            "Simulated and labelled: vessel positions on the map and cost figures (illustrative, not quotes). See the Forecast and Model Lab pages for measured forecast accuracy.")
    return Answer("data_sources", 0, [], {}, text, [], [("Model details", "/app/forecast")], a)


def _help(db: Session, e: Entities, a: list[str], user=None) -> Answer:
    return Answer("help", 0, [], {}, "I can answer questions about the freight market and forecasts, origin comparison, berth fit, route risk, port congestion, Haldia operations, ship availability, "
                  "COA versus spot, SAIL's coal demand and where our data comes from. Try one of the suggestions.", [], [])


def _ledger(db: Session, e: Entities, a: list[str], user=None) -> Answer:
    q = db.query(LedgerEntry)
    all_rows = has(user, "ledger:read_all")
    if not all_rows:
        q = q.filter(LedgerEntry.created_by == user.id)  # row-level scope in the query itself
    rows = q.order_by(LedgerEntry.fixture_date.desc()).all()
    if not rows:
        return Answer("ledger", 0, [], {}, "There are no fixtures in the ledger that you can see. Add one on the Fixture Ledger page.", [], [("Open the ledger", "/app/ledger")], a,
                      scope="every entry" if all_rows else "only entries you created")
    rated = [float(r.rate_usd_per_tonne) for r in rows if r.rate_usd_per_tonne is not None]
    latest = rows[0]
    text = (f"You can see {len(rows)} fixture(s) ({'every entry in the ledger' if all_rows else 'only the ones you created'}), covering {sum(float(r.cargo_tonnes) for r in rows):,.0f} t. "
            f"The latest is {latest.vessel_name} on {latest.fixture_date}, {latest.origin_country} to {latest.destination_port}"
            + (f". Rates average ${sum(rated) / len(rated):.2f}/t across {len(rated)} priced fixtures." if rated else "."))
    return Answer("ledger", 0, [], {}, text, [("Fixtures", str(len(rows))), ("Tonnes", f"{sum(float(r.cargo_tonnes) for r in rows):,.0f}")] + ([("Avg rate", f"${sum(rated) / len(rated):.2f}/t")] if rated else []),
                  [("Open the ledger", "/app/ledger")], a, scope="every entry" if all_rows else "only entries you created")


def _alerts_mine(db: Session, e: Entities, a: list[str], user=None) -> Answer:
    rules = db.query(AlertRule).filter(AlertRule.user_id == user.id).all()
    events = db.query(AlertEvent).filter(AlertEvent.user_id == user.id).order_by(AlertEvent.id.desc()).limit(3).all()
    unread = db.query(AlertEvent).filter(AlertEvent.user_id == user.id, AlertEvent.is_read.is_(False)).count()
    text = f"You have {len(rules)} alert rule(s) and {unread} unread alert(s)."
    if events:
        text += " Most recent: " + "; ".join(ev.message for ev in events) + "."
    return Answer("alerts_mine", 0, [], {}, text, [("Rules", str(len(rules))), ("Unread", str(unread))], [("Open alerts", "/app/alerts")], a, scope="only your own rules")


def _my_access(db: Session, e: Entities, a: list[str], user=None) -> Answer:
    r = role_of(user)
    perms = sorted(permissions_of(user))
    missing = [k for k in PERMISSION_LABELS if k not in perms]
    scope = port_scope(user)
    text = f"You are signed in as {r['label']} (authority level {r['level']} of 5). {r['summary']}"
    if scope is not None:
        text += f" Your ports: {', '.join(scope) if scope else 'none assigned yet'}."
    if missing:
        text += f" You cannot access: {'; '.join(PERMISSION_LABELS[k] for k in missing[:4])}{'…' if len(missing) > 4 else ''}. An administrator can change your role."
    return Answer("my_access", 0, [], {}, text, [("Role", r["label"]), ("Level", f"{r['level']}/5"), ("Permissions", str(len(perms)))], [("See the full access matrix", "/app/access")], a)


def _users_admin(db: Session, e: Entities, a: list[str], user=None) -> Answer:
    rows = db.query(User).all()
    by_role: dict[str, int] = {}
    for u in rows:
        by_role[u.role] = by_role.get(u.role, 0) + 1
    active = sum(1 for u in rows if u.is_active)
    denied = db.query(AuditLog).filter(AuditLog.allowed.is_(False)).count()
    text = (f"There are {len(rows)} accounts ({active} active): " + ", ".join(f"{n} {ROLES.get(k, {'label': k})['label']}" for k, n in sorted(by_role.items(), key=lambda t: -t[1]))
            + f". The audit log holds {denied} denied request(s).")
    return Answer("users_admin", 0, [], {}, text, [("Accounts", str(len(rows))), ("Active", str(active)), ("Denied requests", str(denied))], [("Manage users and the audit log", "/app/access")], a)


def _what_if(db: Session, e: Entities, a: list[str], user=None) -> Answer:
    t = e.text
    lv = whatif_service.Levers(origin=e.origin or "Australia", port=e.port or "Haldia", cargo_tonnes=e.cargo_tonnes or 75000)
    if not e.origin:
        a.append("No origin named, so I assumed Australia.")
    if not e.port:
        a.append("No port named, so I assumed Haldia.")
    pct = e.percent
    days = float(e.horizon_days) if e.horizon_days else None
    if "red sea" in t or "suez" in t:
        lv.reroute_nm, lv.freight_shock_pct, lv.bunker_shock_pct = 3500, 12, 8
        what = "the Red Sea closes (3,500 nm reroute, freight +12%, fuel +8%)"
    elif any(w in t for w in ("rupee", "inr", "currency", "dollar")):
        lv.inr_shock_pct = -(pct or 5) if any(w in t for w in ("strengthen", "gain", "rise")) and "rupee" in t and "fall" not in t and "weak" not in t else (pct or 5)
        what = f"the rupee moves {lv.inr_shock_pct:+g}% against the dollar"
    elif any(w in t for w in ("fuel", "bunker", "oil")):
        lv.bunker_shock_pct = pct or 20
        what = f"fuel prices change {lv.bunker_shock_pct:+g}%"
    elif any(w in t for w in ("cyclone", "storm", "weather")):
        lv.storm_delay_days = days or 3
        what = f"a cyclone delays the ship {lv.storm_delay_days:g} days"
    elif any(w in t for w in ("strike", "delay", "congest", "queue")):
        lv.port_delay_days = days or 4
        what = f"the port is delayed {lv.port_delay_days:g} days"
    else:
        lv.freight_shock_pct = (pct or 20) * (-1 if any(w in t for w in ("fall", "drop", "down", "decrease", "cheaper")) else 1)
        what = f"freight rates change {lv.freight_shock_pct:+g}%"
    r = whatif_service.what_if(db, lv)
    b, s = r["base"], r["scenario"]
    text = (f"If {what}, the landed cost of {lv.cargo_tonnes:,.0f} t from {lv.origin} to {lv.port} goes from ₹{b['total_inr_crore']} crore to ₹{s['total_inr_crore']} crore ({r['delta_pct']:+}%), "
            + (f"and the trip takes {r['delta_days']:+g} days {'longer' if r['delta_days'] > 0 else 'less'}." if abs(r['delta_days']) >= 0.05 else "and the trip length is unchanged.") + " Illustrative estimates, not quotes.")
    return Answer("what_if", 0, [], {}, text, [("Base", f"₹{b['total_inr_crore']} cr"), ("Scenario", f"₹{s['total_inr_crore']} cr"), ("Change", f"{r['delta_pct']:+}%"), ("Days", f"{r['delta_days']:+g}")],
                  [("Open the What-If Studio", "/app/whatif")], a)


def _urgent(db: Session, e: Entities, a: list[str], user=None) -> Answer:
    port = e.port or "Paradip"
    if not e.port:
        a.append("No port named, so I assumed Paradip.")
    cargo = e.cargo_tonnes or 60000
    days = float(e.horizon_days) if e.horizon_days else 20.0
    if not e.horizon_days:
        a.append("No deadline given, so I assumed 20 days.")
    u = whatif_service.urgent_desk(db, port, cargo, days)
    best = u["best"] or u["fastest"]
    figs = [("Deadline", f"{days:g} d"), ("Options", f"{u['feasible_count']} feasible")]
    if best:
        figs += [("Arrives in", f"{best['days']} d"), ("On time", f"{best['p_on_time']:.0%}"), ("Cost", f"₹{best['total_inr_crore']} cr")]
    return Answer("urgent", 0, [], {}, u["verdict"], figs, [("Open the Urgent Desk", "/app/urgent")], a)


def _verdict(db: Session, e: Entities, a: list[str], user=None) -> Answer:
    from app.services import verdict as verdict_service
    port = e.port or "Paradip"
    if not e.port:
        a.append("No port named, so I assumed Paradip.")
    cargo = e.cargo_tonnes or 60000
    if not e.cargo_tonnes:
        a.append("No cargo size given, so I assumed 60,000 t.")
    days = float(e.horizon_days) if e.horizon_days else 45.0
    if not e.horizon_days:
        a.append("No need-by date given, so I assumed 45 days.")
    v = verdict_service.build(db, port, cargo, days)
    figs = [("Verdict", v["verdict"].title()), ("Act by", v["act_by"]), ("Confidence", v["confidence"])]
    return Answer("verdict", 0, [], {}, v["headline"], figs, [("Open the verdict", "/app/verdict")], a)


PORT_CHOICE_RE = re.compile(r"\b(which|what|best|better|right)\b[^?]*\bport\b|\bport\b[^?]*\b(should i|to use|to choose|is best|is better)\b|\bwhere should (i|we) (discharge|unload|berth)")
VERDICT_RE = re.compile(r"should (i|we) (buy|book|fix|charter|wait|hold|lock|act|order)|buy (coal )?now|book now|good time to|right time to|wait or (buy|book|act|fix)|act now or wait")
FORECAST_RE = re.compile(r"\bforecast\b|\boutlook\b|\bpredict|what will .*(rate|freight|price)|freight (rate )?(trend|next)")
OFF_MAP = re.compile(r"singapore|china|japan|korea|malaysia|thailand|vietnam|dubai|uae|south africa|canada|colombia|brazil|europe|germany|ukraine", re.I)


def _port_choice(db: Session, e: Entities, a: list[str], user=None) -> Answer:
    ports = db.query(Port).filter(Port.is_destination.is_(True)).all()
    scope = port_scope(user) if user is not None else None
    if scope is not None:
        ports = [p for p in ports if p.name in scope]
        if not ports:
            raise AccessDenied("No ports are assigned to your account yet.")
    classes = {vc.name: vc for vc in db.query(VesselClass).all()}
    rows = []
    for p in ports:
        cong = _congestion_score(p, db)[0]
        biggest = next((n for n in ("Capesize", "Panamax", "Supramax", "Handysize") if n in classes and check_compatibility(p, classes[n]).compatible), "none")
        rank = {"Capesize": 0, "Panamax": 1, "Supramax": 2, "Handysize": 3, "none": 4}[biggest]
        rows.append((rank, cong, p.name, biggest))
    rows.sort()
    best = rows[0]
    days = f" within {e.horizon_days} days" if e.horizon_days else ""
    text = (f"For coking coal{days}, {best[2]} is the strongest choice on physical fit: it takes a {best[3]} and its congestion score is {best[1]:.1f}/10. "
            "Ranking (largest ship that berths, then least congestion): " + "; ".join(f"{r[2]} ({r[3]}, {r[1]:.1f}/10)" for r in rows) + ". "
            "This ranks berth fit and queueing only; the Urgent Fixture Desk adds freight cost and on-time probability for a specific deadline.")
    m = OFF_MAP.search(e.text)
    if m:
        a.append(f"{m.group(0).title()} is not one of the modelled coking-coal origins (Australia, United States, Mozambique, Russia, Indonesia), so I ranked ports without an origin.")
    return Answer("port_choice", 0, [], {}, text, [(r[2], f"{r[3]}, {r[1]:.1f}") for r in rows[:4]], [("Urgent Fixture Desk", "/app/urgent"), ("Berth-fit checker", "/app/ports")], a)


HANDLERS = {
    "port_choice": _port_choice,
    "market_now": _market_now, "forecast": _forecast, "recommend_origin": _recommend, "port_fit": _port_fit, "risk": _risk, "congestion": _congestion,
    "haldia": _haldia, "coa_vs_spot": _coa, "ledger": _ledger, "alerts_mine": _alerts_mine, "my_access": _my_access, "users_admin": _users_admin, "what_if": _what_if, "urgent": _urgent, "verdict": _verdict, "demand": _demand, "data_sources": _sources, "help": _help,
}


INTENT_PERMISSION = {
    "market_now": "market:read", "forecast": "market:read", "recommend_origin": "recommend:read", "port_fit": "ports:read", "risk": "risk:read",
    "congestion": "ports:read", "port_choice": "ports:read", "haldia": None, "coa_vs_spot": "financial:read", "demand": "demand:read", "data_sources": None, "help": None,
    "what_if": "financial:read", "urgent": "financial:read", "verdict": "financial:read", "ledger": "ledger:read", "alerts_mine": "alerts:manage", "my_access": None, "users_admin": "admin:users",
}


def _allowed(user, intent: str) -> bool:
    perm = INTENT_PERMISSION.get(intent)
    if perm is None:
        return True
    if perm == "ledger:read":
        return has(user, "ledger:read_all") or has(user, "ledger:read_own")
    return has(user, perm)


def suggestions_for(user) -> list[str]:
    out = []
    for text, intent in SUGGESTION_INTENTS:
        if _allowed(user, intent):
            out.append(text)
    scope = port_scope(user)
    if scope:
        out = [t.replace("Haldia", scope[0]).replace("Paradip", scope[0]) for t in out]
    return out[:8]


SUGGESTION_INTENTS = [
    ("What will Panamax rates do over the next 14 days?", "forecast"),
    ("Cheapest origin for 75,000 t to Paradip?", "recommend_origin"),
    ("How risky is Australia to Haldia?", "risk"),
    ("Can a Capesize berth at Haldia?", "port_fit"),
    ("Which port is most congested?", "congestion"),
    ("Should we use a COA or stay spot?", "coa_vs_spot"),
    ("How much coking coal does SAIL import?", "demand"),
    ("What if freight rises 30%?", "what_if"),
    ("We need 60000 t at Paradip within 20 days", "urgent"),
    ("Should we rent a ship now or wait?", "verdict"),
    ("Show my fixtures", "ledger"),
    ("How does the lock at Haldia work?", "haldia"),
    ("What can I access?", "my_access"),
    ("How many users have accounts?", "users_admin"),
    ("Do I have any alerts?", "alerts_mine"),
]


def ask(db: Session, question: str, user=None) -> Answer:
    q = question.strip()
    ranked = classify(q, top_k=3)
    intent, conf = ranked[0]
    low = q.lower()
    if VERDICT_RE.search(low) and intent != "verdict":
        ranked = [("verdict", 0.9)] + [r for r in ranked if r[0] != "verdict"][:2]
        intent, conf = ranked[0]
    elif FORECAST_RE.search(low) and (conf < CONFIDENCE_FLOOR or intent in ("data_sources", "help", "market_now")) and not PORT_CHOICE_RE.search(low):
        ranked = [("forecast", 0.9)] + [r for r in ranked if r[0] != "forecast"][:2]
        intent, conf = ranked[0]
    if PORT_CHOICE_RE.search(q.lower()) and intent not in ("urgent", "verdict", "port_fit", "congestion", "haldia", "risk"):
        ranked = [("port_choice", 0.9)] + [r for r in ranked if r[0] != "port_choice"][:2]
        intent, conf = ranked[0]
    ents = extract_entities(q)
    ent_dict = {k: v for k, v in ents.__dict__.items() if v is not None}
    if conf < CONFIDENCE_FLOOR:
        alt = ", ".join(f"'{i}'" for i, _ in ranked[:2])
        if user is not None:
            record(db, user, "assistant_query", f"[unclear] {q}")
        return Answer("unclear", conf, ranked, ent_dict,
                      f"I am not sure what you mean (my best guesses are {alt}, but only at {conf:.0%} confidence). Try naming an index, port or origin, or pick a suggestion.")
    if user is not None and not _allowed(user, intent):
        perm = INTENT_PERMISSION[intent]
        need = PERMISSION_LABELS.get(perm, "this data") if perm and perm != "ledger:read" else "the fixture ledger"
        record(db, user, "assistant_query", f"[denied:{intent}] {q}", allowed=False)
        r = role_of(user)
        return Answer(intent, conf, ranked, ent_dict,
                      f"I can't answer that for your account. Your role is {r['label']}, which does not include access to: {need}. "
                      "Someone with a higher role (for example an administrator) can see it, or can change your role. Ask me \"What can I access?\" to see what you can use.",
                      denied=True, scope=r["label"])
    assumptions: list[str] = []
    try:
        ans = HANDLERS[intent](db, ents, assumptions, user)
    except AccessDenied as exc:
        record(db, user, "assistant_query", f"[denied-scope:{intent}] {q}", allowed=False)
        return Answer(intent, conf, ranked, ent_dict, str(exc), denied=True, scope=", ".join(port_scope(user) or []))
    ans.confidence, ans.alternatives, ans.entities = conf, ranked, ent_dict
    ans.assumptions = assumptions
    if not ans.scope and user is not None and port_scope(user) is not None:
        ans.scope = "Your assigned ports: " + (", ".join(port_scope(user)) or "none")
    if user is not None:
        record(db, user, "assistant_query", f"[{intent}] {q}")
    _ = np, assigned_ports, permissions_of
    return ans
