"""'Ask the Freight Desk': routes a question to one of the platform's engines and answers in a short
broker-style briefing with the numbers used. No free-text generation and no external service: the
intent comes from the local classifier in app.ml.intent, the figures from the same services the
dashboard uses."""

from dataclasses import dataclass, field

import numpy as np
from sqlalchemy.orm import Session

from app.ml.intent import Entities, classify, extract_entities
from app.models import Port, VesselClass
from app.services import haldia as haldia_service
from app.services.compatibility import check_compatibility
from app.services.freight_data import load_series
from app.services.quick_forecast import quick_forecast
from app.services.recommendation import MarketSignal, compare_origins
from app.services.risk import _congestion_score, compute_route_risk

CONFIDENCE_FLOOR = 0.35
DEFAULT_ORIGINS = ["Australia", "United States", "Mozambique", "Russia", "Indonesia"]
INDEX_LABEL = {"BDI": "Baltic Dry Index", "BCI": "Capesize (BCI)", "BPI": "Panamax (BPI)", "BSI": "Supramax (BSI)", "BHSI": "Handysize (BHSI)"}
CLASS_INDEX = {"Capesize": "BCI", "Panamax": "BPI", "Supramax": "BSI", "Handysize": "BHSI"}

SUGGESTIONS = [
    "What will the Baltic Dry Index do over the next 14 days?",
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


def _port(db: Session, name: str | None, assumptions: list[str], default: str = "Haldia") -> Port:
    chosen = name or default
    if not name:
        assumptions.append(f"No port named, so I assumed {default}.")
    return db.query(Port).filter(Port.name == chosen, Port.is_destination.is_(True)).one()


def _stale(idx: str, last_date: str) -> str:
    return f" Note: our {idx} series ends {last_date}, so this is not today's market." if last_date < "2026-01-01" else ""


def _pct(x: float) -> str:
    return f"{x:+.1f}%"


def _market_now(db: Session, e: Entities, a: list[str]) -> Answer:
    idx = e.index_name or "BDI"
    s = load_series(db, idx)
    if s.empty:
        return Answer("market_now", 0, [], {}, f"I have no data for {idx}.")
    last, d = float(s.iloc[-1]), s.index[-1].date()
    wk = (last / float(s.iloc[-6]) - 1) * 100 if len(s) > 6 else 0.0
    mo = (last / float(s.iloc[-22]) - 1) * 100 if len(s) > 22 else 0.0
    pctile = float((s < last).mean() * 100)
    cv = float(s.iloc[-90:].std() / s.iloc[-90:].mean() * 100)
    regime = "cheap by its own history" if pctile < 30 else "expensive by its own history" if pctile > 70 else "mid-range for its history"
    text = (f"{INDEX_LABEL.get(idx, idx)} last printed {last:,.0f} on {d}. That is {_pct(wk)} over a week and {_pct(mo)} over a month, "
            f"and {regime} (higher than {pctile:.0f}% of {len(s):,} daily readings). The last 90 days swung {cv:.0f}% around their mean.")
    if str(d) < "2026-01-01":
        text += f" Note: our {idx} series stops on {d}, so this is not today's print."
    return Answer("market_now", 0, [], {}, text,
                  [("Last", f"{last:,.0f}"), ("1 week", _pct(wk)), ("1 month", _pct(mo)), ("History percentile", f"{pctile:.0f}%")],
                  [("Open the live board", "/app/markets")])


def _forecast(db: Session, e: Entities, a: list[str]) -> Answer:
    idx = e.index_name or "BDI"
    h = e.horizon_days or 14
    if not e.horizon_days:
        a.append("No horizon given, so I used 14 days.")
    f = quick_forecast(db, idx, h)
    if f is None:
        return Answer("forecast", 0, [], {}, f"Not enough {idx} history to forecast.")
    span = (f.upper - f.lower) / 2 / f.last_value * 100
    direction = "drift up" if f.change_pct > 1 else "drift down" if f.change_pct < -1 else "stay roughly flat"
    text = (f"ARIMA(2,1,2) has {INDEX_LABEL.get(idx, idx)} going from {f.last_value:,.0f} ({f.last_date}) to about {f.forecast_end:,.0f} in {h} days, "
            f"a move of {_pct(f.change_pct)}: it should {direction}. The 95% band runs {f.lower:,.0f} to {f.upper:,.0f} (about ±{span:.0f}%), so treat direction with caution")
    text += ". On the real BDI our 7-day backtest error is about 3% and 14-day about 4.5%." if idx == "BDI" else "."
    text += _stale(idx, f.last_date)
    return Answer("forecast", 0, [], {}, text,
                  [("Now", f"{f.last_value:,.0f}"), (f"In {h}d", f"{f.forecast_end:,.0f}"), ("Change", _pct(f.change_pct)), ("95% band", f"{f.lower:,.0f}–{f.upper:,.0f}")],
                  [("Full forecast with backtest", "/app/forecast")], a)


def _recommend(db: Session, e: Entities, a: list[str]) -> Answer:
    port = _port(db, e.port, a, "Paradip")
    cargo = e.cargo_tonnes or 75_000
    if not e.cargo_tonnes:
        a.append("No cargo size given, so I used 75,000 t.")
    origins = [e.origin] if False else DEFAULT_ORIGINS
    cls = db.query(VesselClass).all()
    sig = MarketSignal("BDI", None, None)
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


def _port_fit(db: Session, e: Entities, a: list[str]) -> Answer:
    port = _port(db, e.port, a)
    classes = db.query(VesselClass).order_by(VesselClass.dwt_min).all()
    ok, no = [], []
    for vc in classes:
        (ok if check_compatibility(port, vc).compatible else no).append(vc.name)
    draft_txt = f"allows up to {port.max_draft_m} m draft" if port.max_draft_m else "has no fixed draft on file (it is tide-dependent) and"
    text = f"{port.name} {draft_txt} allows up to {port.max_loa_m} m LOA. Classes that pass all checks: {', '.join(ok) or 'none'}. "
    if no:
        text += f"Do not fit as designed: {', '.join(no)}."
    figs = [("Max draft", f"{port.max_draft_m} m" if port.max_draft_m else "tide-dependent"), ("Max LOA", f"{port.max_loa_m} m"), ("Accepted", ", ".join(ok) or "none")]
    if port.name == "Haldia":
        h = haldia_service.summary(db)["observed"]
        text += (f" In practice, coal vessels observed at Haldia carried a median {h['median_cargo_t']:,.0f} t on {h['median_draft_m']} m draft "
                 f"({h['vessels']} vessels, {h['period_start']} to {h['period_end']}), because larger ships are lightened before the river.")
    if e.index_name and e.index_name in CLASS_INDEX.values():
        pass
    return Answer("port_fit", 0, [], {}, text, figs, [("Open the berth-fit checker", "/app/ports")], a)


def _risk(db: Session, e: Entities, a: list[str]) -> Answer:
    port = _port(db, e.port, a)
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


def _congestion(db: Session, e: Entities, a: list[str]) -> Answer:
    ports = db.query(Port).filter(Port.is_destination.is_(True)).all()
    scored = sorted(((_congestion_score(p, db), p) for p in ports), key=lambda t: -t[0][0])
    if e.port:
        (s, detail), p = next(t for t in scored if t[1].name == e.port)
        return Answer("congestion", 0, [], {}, f"{p.name} congestion scores {s:.1f}/10. {detail}.", [("Score", f"{s:.1f}/10")], [("Ports and berths", "/app/ports")], a)
    (s0, d0), p0 = scored[0]
    (s1, _), p1 = scored[-1]
    text = (f"{p0.name} is the most congested at {s0:.1f}/10 ({d0}). {p1.name} is the calmest at {s1:.1f}/10. "
            "Scores blend official average turnaround with recent IMF PortWatch dry-bulk call counts; ports without official turnaround data get a default.")
    return Answer("congestion", 0, [], {}, text, [(p.name, f"{sc[0]:.1f}") for sc, p in scored[:5]], [("Open the port map", "/app/map")], a)


def _haldia(db: Session, e: Entities, a: list[str]) -> Answer:
    d = haldia_service.summary(db)
    f, o = d["facts"], d["observed"]
    text = (f"Haldia is an impounded dock: ships pass a {f['lock_length_m']} m by {f['lock_width_m']} m lock. It sits about {f['sandheads_distance_km']} km from Sandheads and "
            f"{f['sagar_pilotage_upstream_km']} km above the Sagar pilot station, roughly {f['transit_hours_sandheads_to_jetty']} hours' passage. Big ships are lightened by floating cranes at Sagar or Sandheads. "
            f"Berth 4A has {f['coal_berth_4a_unloaders']} grab unloaders at about {f['coal_berth_4a_rate_t_per_day']:,} t/day. In the port trust's daily reports we found {o['vessels']} coal vessels "
            f"({o['by_importer'].get('SAIL', 0)} for SAIL) with a median cargo of {o['median_cargo_t']:,.0f} t and expected draft {o['min_draft_m']}–{o['max_draft_m']} m.")
    return Answer("haldia", 0, [], {}, text,
                  [("Vessels seen", str(o["vessels"])), ("Median cargo", f"{o['median_cargo_t']:,.0f} t"), ("Median draft", f"{o['median_draft_m']} m")],
                  [("Back to the Haldia scene", "/")], a)


def _coa(db: Session, e: Entities, a: list[str]) -> Answer:
    idx = e.index_name or "BDI"
    s = load_series(db, idx)
    f = quick_forecast(db, idx, 30)
    cv = float(s.iloc[-90:].std() / s.iloc[-90:].mean() * 100) if len(s) > 90 else 0
    if f is None:
        return Answer("coa_vs_spot", 0, [], {}, "Not enough history to compare.")
    lean = "lean towards locking a contract" if (f.change_pct > 2 or cv > 25) else "spot is reasonable for now"
    text = (f"Rule of thumb from the data: {INDEX_LABEL.get(idx, idx)} is projected {_pct(f.change_pct)} over 30 days and its 90-day swing is {cv:.0f}% of the mean, so I would {lean}. "
            "A contract of affreightment fixes the rate for several voyages, which pays when the market is expected to rise or is very volatile, and costs you if it falls. "
            "The Financial Tools page simulates the exact savings with your cargo and interval." + _stale(idx, str(s.index[-1].date())))
    return Answer("coa_vs_spot", 0, [], {}, text, [("30d outlook", _pct(f.change_pct)), ("90d volatility", f"{cv:.0f}%")], [("Run the COA vs spot simulator", "/app/financial")], a)


def _demand(db: Session, e: Entities, a: list[str]) -> Answer:
    text = ("From SAIL's annual reports, clean coking coal use was 19.37 MT in FY24 with 16.92 MT imported (about 87%), and 18.74 MT in FY25 with 16.32 MT imported. "
            "SAIL's Q1 FY27 crude steel was 4.757 MT, so roughly 4 MT of imported coking coal a quarter, or about 120 lots of 33,000 t a quarter if it all moved in Haldia-sized parcels. "
            "The CAG audit found 94% of imported coal arrived under long-term agreements (FY17-FY23) through Visakhapatnam, Gangavaram, Paradip, Dhamra and Haldia.")
    return Answer("demand", 0, [], {}, text, [("Imported share", "~87%"), ("FY25 imported", "16.32 MT"), ("Q1 FY27 crude steel", "4.757 MT")], [], a)


def _sources(db: Session, e: Entities, a: list[str]) -> Answer:
    text = ("Real: Baltic Dry Index daily 2006 to Feb 2026, Baltic sub-indices to Jul 2019, coal, iron ore, FX and equity series, IMF PortWatch port calls and chokepoint transits, "
            "the Ministry of Ports turnaround figures, and 90+ coal vessels parsed from SMP Kolkata's daily Haldia reports. Simulated and labelled: vessel positions on the map, "
            "anchorage queues, and cost figures (illustrative, not quotes). Forecast accuracy on the real BDI: ARIMA about 3.1% MAPE at 7 days; the ARIMA+XGBoost ensemble is not significantly better than ARIMA.")
    return Answer("data_sources", 0, [], {}, text, [], [("Model details", "/app/forecast")], a)


def _help(db: Session, e: Entities, a: list[str]) -> Answer:
    return Answer("help", 0, [], {}, "I can answer questions about the freight market and forecasts, origin comparison, berth fit, route risk, port congestion, Haldia operations, "
                  "COA versus spot, SAIL's coal demand and where our data comes from. Try one of the suggestions.", [], [])


HANDLERS = {
    "market_now": _market_now, "forecast": _forecast, "recommend_origin": _recommend, "port_fit": _port_fit, "risk": _risk, "congestion": _congestion,
    "haldia": _haldia, "coa_vs_spot": _coa, "demand": _demand, "data_sources": _sources, "help": _help,
}


def ask(db: Session, question: str) -> Answer:
    q = question.strip()
    ranked = classify(q, top_k=3)
    intent, conf = ranked[0]
    ents = extract_entities(q)
    ent_dict = {k: v for k, v in ents.__dict__.items() if v is not None}
    if conf < CONFIDENCE_FLOOR:
        alt = ", ".join(f"'{i}'" for i, _ in ranked[:2])
        return Answer("unclear", conf, ranked, ent_dict,
                      f"I am not sure what you mean (my best guesses are {alt}, but only at {conf:.0%} confidence). Try naming an index, port or origin, or pick a suggestion.")
    assumptions: list[str] = []
    ans = HANDLERS[intent](db, ents, assumptions)
    ans.confidence, ans.alternatives, ans.entities = conf, ranked, ent_dict
    ans.assumptions = assumptions
    _ = np
    return ans
