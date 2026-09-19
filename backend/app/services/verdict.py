"""One plain-language call: when to charter, and which ship.

This is decision support built from transparent rules over current data, NOT a trained model, and the weights below are
judgement, not fitted values. Each signal casts a vote from -1 (wait) to +1 (charter now); the call is the weighted average.
No signal claims to know today's exact freight rate (there is no free live index); the walk-away price is the desk's
cost model, not a market quote.
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Port
from app.services import pulse, signals, whatif

NOW_AT, WAIT_AT = 0.25, -0.20
SOON_DAYS = 7
RECHECK_DAYS = 5


def _vote(name: str, weight: float, vote: float, reading: str, why: str) -> dict:
    return {"signal": name, "weight": weight, "vote": round(max(-1.0, min(1.0, vote)), 2), "reading": reading, "why": why}


def build(db: Session, port_name: str, cargo_tonnes: float, need_by_days: float = 45.0) -> dict:
    port = db.query(Port).filter(Port.name == port_name).first()
    if port is None:
        raise ValueError(f"Unknown port {port_name}")
    desk = whatif.urgent_desk(db, port_name, cargo_tonnes, need_by_days)
    ship = desk["best"] or desk["cheapest_feasible"] or desk["fastest"]
    notes: list[str] = []
    split = None
    if not desk["best"] and ship and ship["p_on_time"] >= 0.8 and not (ship["fits_berth"] and ship["size_ok"]):
        # The date is reachable but no single ship can carry the parcel into this port: try two half-parcels.
        half = whatif.urgent_desk(db, port_name, cargo_tonnes / 2, need_by_days)
        if half["best"]:
            split = half["best"]
    votes: list[dict] = []

    # 1. Time pressure: how much room is left between the fastest safe ship and the date the plant needs the coal.
    if desk["best"]:
        slack = need_by_days - desk["best"]["days"]
        if slack < 5:
            votes.append(_vote("Time pressure", 3.0, 1.0, f"{slack:.0f} days of slack", "Very little room: any wait risks missing the date."))
        elif slack < 12:
            votes.append(_vote("Time pressure", 3.0, 0.3, f"{slack:.0f} days of slack", "Some room, but not enough to wait for long."))
        else:
            votes.append(_vote("Time pressure", 3.0, -0.4, f"{slack:.0f} days of slack", "Plenty of room; waiting costs nothing in time."))
    else:
        votes.append(_vote("Time pressure", 3.0, 1.0, "no safe option by the date", "Nothing safe arrives in time, so acting today is the only way to improve the position."))

    # 2. Ship availability from the user's uploaded broker lists.
    from app.services import tonnage

    avail = tonnage.match(db, port_name, cargo_tonnes, need_by_days)
    if avail["total_on_lists"]:
        n = avail["suitable_count"]
        v = 0.9 if n == 0 else 0.5 if n == 1 else -0.3 if n >= 3 else 0.0
        votes.append(_vote("Open ships on your lists", 2.0, v, f"{n} of {avail['total_on_lists']} listed ships could carry it by day {need_by_days:g}",
                           "No listed ship fits: book early or ask brokers for more positions." if n == 0 else "Only one suitable ship is on the lists: it may go quickly." if n == 1 else "Several suitable ships are on the lists, so there is choice." if n >= 3 else "Two suitable ships are on the lists."))
        if avail["lists_stale"]:
            notes.append("The uploaded broker lists are more than a week old, so ship availability may have changed.")
        if avail["any_sample"]:
            notes.append("Ship availability here uses the illustrative SAMPLE list (invented ships). Upload real broker lists for a real answer.")
    else:
        notes.append("No broker open-tonnage list has been uploaded, so ship availability was not scored.")

    # 3. Season: is the arrival window riskier if we wait two weeks?
    transit = ship["days"] if ship else 20
    today = date.today()
    now_r = signals.cyclone_eta_risk(db, port_name, today, today + timedelta(days=6), transit)
    later_r = signals.cyclone_eta_risk(db, port_name, today + timedelta(days=14), today + timedelta(days=20), transit)
    dp = later_r["probability_storm_in_window"] - now_r["probability_storm_in_window"]
    votes.append(_vote("Storm season", 1.5, dp * 6, f"storm chance {now_r['probability_storm_in_window']:.0%} now vs {later_r['probability_storm_in_window']:.0%} if fixed in two weeks",
                       "Waiting moves the arrival into a stormier period." if dp > 0.02 else "Waiting moves the arrival into a calmer period." if dp < -0.02 else "Storm risk is about the same either way."))

    # 4-6. Current market context (US-government and Federal Reserve series).
    p = pulse.market_pulse(db)
    cards = {c["series"]: c for c in p["cards"]}
    if "OCEAN_GULF_JAPAN" in cards and cards["OCEAN_GULF_JAPAN"]["change_3m_pct"] is not None:
        ch = cards["OCEAN_GULF_JAPAN"]["change_3m_pct"]
        votes.append(_vote("Dry-bulk freight momentum", 1.5, ch / 15, f"USDA grain ocean rate {ch:+.1f}% over 3 months (to {cards['OCEAN_GULF_JAPAN']['as_of']})",
                           "Rising dry-bulk rates mean a dearer ship later: rent sooner. Momentum has only a weak record (see the evidence below), so it carries a modest weight."))
    if "BRENT" in cards and cards["BRENT"]["change_3m_pct"] is not None:
        ch = cards["BRENT"]["change_3m_pct"]
        votes.append(_vote("Fuel price momentum", 1.0, ch / 20, f"Brent crude {ch:+.1f}% over 3 months", "Bunker fuel is a large part of freight; a rising oil price pushes rates up."))
    if "COAL_PPI" in cards and cards["COAL_PPI"]["change_3m_pct"] is not None:
        ch = cards["COAL_PPI"]["change_3m_pct"]
        votes.append(_vote("Coal price momentum", 0.5, ch / 15, f"US coal price index {ch:+.1f}% over 3 months", "Rising coal prices lift demand for ships. A weak, indirect signal."))
    if "INR" in cards and cards["INR"]["change_3m_pct"] is not None:
        ch = cards["INR"]["change_3m_pct"]
        votes.append(_vote("Rupee trend", 1.0, ch / 6, f"rupee {ch:+.1f}% per dollar over 3 months", "A weaker rupee makes a dollar freight bill dearer each week you wait."))

    score = sum(v["weight"] * v["vote"] for v in votes) / sum(v["weight"] for v in votes)
    if split is not None:
        verdict, act = "SPLIT INTO TWO PARCELS", today
    elif not desk["best"] and desk["feasible_count"] == 0:
        verdict, act = "CANNOT MEET THE DATE SAFELY", today
    elif score >= NOW_AT:
        verdict, act = "RENT NOW", today
    elif score <= WAIT_AT:
        verdict, act = "WAIT AND RECHECK", today + timedelta(days=RECHECK_DAYS)
    else:
        verdict, act = "RENT WITHIN A WEEK", today + timedelta(days=SOON_DAYS)

    agree = sum(1 for v in votes if (v["vote"] > 0.05) == (score > 0) and abs(v["vote"]) > 0.05)
    lean = sum(1 for v in votes if abs(v["vote"]) > 0.05)
    confidence = "High" if lean and agree / lean >= 0.75 and abs(score) >= 0.3 else "Medium" if lean and agree / lean >= 0.55 else "Low"
    notes.append("There is no free live freight index. The freight signal is the USDA grain ocean rate, a public-domain dry-bulk proxy, so treat the timing as guidance, not a rate forecast.")

    if ship:
        cls = f"{ship['vessel_class']} from {ship['origin']} at {ship['speed_knots']:g} knots"
        part = " (part-laden at this port)" if ship.get("part_laden") else ""
        ship_line = f"{cls}{part}: about {ship['days']:.0f} days, {ship['p_on_time']:.0%} chance of arriving by day {need_by_days:g}, roughly ₹{ship['total_inr_crore']:.2f} crore"
    else:
        ship_line = "no ship option found"
    if split is not None:
        ship = split
        ship_line = (f"two parcels of {cargo_tonnes / 2:,.0f} t, each {split['vessel_class']} from {split['origin']} at {split['speed_knots']:g} knots: about {split['days']:.0f} days, "
                     f"{split['p_on_time']:.0%} on time, roughly ₹{split['total_inr_crore']:.2f} crore each")
        notes.append(f"No single ship can carry {cargo_tonnes:,.0f} t into {port_name} (berth draft or ship size), so the parcel is split.")
    headline = {
        "SPLIT INTO TWO PARCELS": f"Split the cargo and rent both now: {ship_line}.",
        "RENT NOW": f"Rent now. {ship_line}.",
        "RENT WITHIN A WEEK": f"Rent within a week (by {act:%d %b}). {ship_line}.",
        "WAIT AND RECHECK": f"Wait, and recheck on {act:%d %b}. If you fixed today it would be: {ship_line}.",
        "CANNOT MEET THE DATE SAFELY": f"No ship reaches {port_name} safely by day {need_by_days:g}. Fastest is {ship_line}. Consider a part cargo, another source, or a later date.",
    }[verdict]

    flips = []
    if verdict != "RENT NOW":
        flips.append("Slack under 5 days (the plant date moves earlier or the ship is delayed) turns this into RENT NOW.")
        flips.append("Fewer open ships matching your cargo on the broker lists turns it towards RENT NOW.")
    if verdict != "WAIT AND RECHECK":
        flips.append("Two weeks of falling freight and oil prices and a stronger rupee would turn this towards WAIT.")
    from app.services import verdict_eval
    try:
        ev = verdict_eval.evidence(db)
    except Exception:  # noqa: BLE001
        ev = None
    return {
        "evidence": ev,
        "availability": {k: avail[k] for k in ("total_on_lists", "suitable_count", "summary", "lists_stale")},
        "verdict": verdict, "headline": headline, "score": round(score, 2), "confidence": confidence, "act_by": act.isoformat(),
        "port": port_name, "cargo_tonnes": cargo_tonnes, "need_by_days": need_by_days,
        "ship": ship, "walk_away_usd_per_t": desk["walk_away_usd_per_t"], "safe_options": desk["feasible_count"], "options_evaluated": desk["options_evaluated"],
        "signals": votes, "what_would_change_it": flips, "notes": notes,
        "method": f"Weighted average of {len(votes)} signal votes (-1 wait to +1 charter now): RENT NOW at or above {NOW_AT}, WAIT at or below {WAIT_AT}. Weights are judgement, not fitted. Ship choice comes from the Urgent Desk (60 options, 2,000 simulated arrivals each).",
    }
