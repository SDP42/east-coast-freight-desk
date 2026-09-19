"""Multi-origin comparative routing — feature #5 in FEATURES.md: ranks
Australia/US/Mozambique/Russia/Indonesia simultaneously for one cargo
requirement, combining Section 7's Port–Vessel Compatibility Engine, Section
5/6's freight forecasts, and the route/distance data seeded in Section 3.
No competitor platform we reviewed (Veson, Xeneta, Signal Ocean, Windward)
does a single-cargo, multi-origin comparison this way — each treats
forecasting and routing as separate problems.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.ml.arima_model import fit_best_arima, forecast
from app.models import Port, Route, VesselClass
from app.services.compatibility import CompatibilityResult, check_compatibility
from app.services.freight_data import load_series

# Illustrative cost model, not a live freight quote: ~$2.5 per tonne per 1,000
# nautical miles is the rule-of-thumb bulk shipping cost benchmark cited in
# our own research compendium (Thunder Said Energy, ref [11]). Vessel-class
# multipliers reflect real economies of scale in dry bulk shipping (larger
# vessels are cheaper per tonne) — approximate, clearly labeled as such.
BASE_RATE_USD_PER_TONNE_PER_1000NM = 2.5
VESSEL_CLASS_COST_MULTIPLIER = {
    "Capesize": 0.85,
    "Panamax": 1.00,
    "Supramax": 1.15,
    "Handysize": 1.35,
}

# Maps a vessel class to the Baltic sub-index that prices it, so the
# recommendation can cite the actual forecasted market direction for that
# class, not just a static cost estimate.
VESSEL_CLASS_TO_INDEX = {
    "Capesize": "OCEAN_GULF_JAPAN",  # one public-domain freight proxy for every class
    "Panamax": "OCEAN_GULF_JAPAN",
    "Supramax": "OCEAN_GULF_JAPAN",
    "Handysize": "OCEAN_GULF_JAPAN",
}


def pick_vessel_class(vessel_classes: list[VesselClass], cargo_tonnes: float) -> VesselClass:
    """Smallest class that can carry the full cargo in one parcel; falls back
    to the largest available class if the cargo exceeds all of them."""
    fitting = [vc for vc in vessel_classes if float(vc.dwt_max) >= cargo_tonnes]
    if fitting:
        return min(fitting, key=lambda vc: float(vc.dwt_max))
    return max(vessel_classes, key=lambda vc: float(vc.dwt_max))


@dataclass
class MarketSignal:
    index_name: str
    forecast_value: float | None
    change_pct: float | None


def get_market_signal(db: Session, index_name: str) -> MarketSignal:
    """1-day-ahead ARIMA forecast direction for the sub-index pricing this
    vessel class — reuses Section 5's model rather than a fresh cost lookup."""
    series = load_series(db, index_name)
    if series.empty or len(series) < 60:
        return MarketSignal(index_name=index_name, forecast_value=None, change_pct=None)

    try:
        best = fit_best_arima(series)
        forecast_values = forecast(best, 1)
        forecast_value = float(forecast_values.iloc[0])
        last_actual = float(series.iloc[-1])
        change_pct = round((forecast_value - last_actual) / last_actual * 100, 3) if last_actual else None
        return MarketSignal(index_name=index_name, forecast_value=round(forecast_value, 2), change_pct=change_pct)
    except Exception:
        return MarketSignal(index_name=index_name, forecast_value=None, change_pct=None)


@dataclass
class OriginResult:
    origin_country: str
    route: Route | None
    vessel_class: VesselClass
    compatibility: CompatibilityResult
    estimated_freight_usd_per_tonne: float | None
    estimated_total_cost_usd: float | None
    market_signal: MarketSignal
    notes: list[str]


def compare_origins(
    db: Session,
    destination_port: Port,
    cargo_tonnes: float,
    origin_countries: list[str],
    market_signal: MarketSignal | None = None,
    extra_distance_nm: dict[str, float] | None = None,
) -> list[OriginResult]:
    """`market_signal` can be passed in so callers comparing many ports/scenarios
    fit the ARIMA model once instead of per call; `extra_distance_nm` maps an
    origin country to added sailing distance (used by the scenario engine to
    model rerouting, e.g. a Red Sea closure)."""
    vessel_classes = db.query(VesselClass).order_by(VesselClass.dwt_min).all()
    vessel_class = pick_vessel_class(vessel_classes, cargo_tonnes)
    if market_signal is None:
        market_signal = get_market_signal(db, VESSEL_CLASS_TO_INDEX.get(vessel_class.name, "OCEAN_GULF_JAPAN"))
    extra_distance_nm = extra_distance_nm or {}

    results: list[OriginResult] = []
    for country in origin_countries:
        notes: list[str] = []
        route = (
            db.query(Route)
            .join(Port, Route.origin_port_id == Port.id)
            .filter(Port.country == country, Route.destination_port_id == destination_port.id)
            .first()
        )

        compatibility = check_compatibility(destination_port, vessel_class, cargo_tonnes)
        # The ship must also fit where it loads: check the origin terminal's published limits.
        origin_port = route.origin_port if False else (route and db.query(Port).filter(Port.id == route.origin_port_id).first())
        if origin_port is not None and origin_port.max_draft_m is not None:
            oc = check_compatibility(origin_port, vessel_class, cargo_tonnes)
            if oc.compatible:
                notes.append(f"Fits the loading terminal ({origin_port.name}, {float(origin_port.max_draft_m):g} m draft).")
            elif oc.partial_load_ok:
                notes.append(f"At {origin_port.name} ({float(origin_port.max_draft_m):g} m draft) a {vessel_class.name} can only load part-laden, about {oc.max_load_fraction:.0%} of full deadweight.")
            else:
                notes.append(f"A {vessel_class.name} does not fit the loading terminal {origin_port.name} ({float(origin_port.max_draft_m):g} m draft): use a smaller class or a different terminal.")

        cost_per_tonne = None
        total_cost = None
        if route and route.distance_nm:
            multiplier = VESSEL_CLASS_COST_MULTIPLIER.get(vessel_class.name, 1.0)
            distance = float(route.distance_nm) + extra_distance_nm.get(country, 0.0)
            cost_per_tonne = round(
                BASE_RATE_USD_PER_TONNE_PER_1000NM * (distance / 1000) * multiplier, 2
            )
            total_cost = round(cost_per_tonne * cargo_tonnes, 2)
            notes.append(
                f"Illustrative cost estimate (not a live quote): ${BASE_RATE_USD_PER_TONNE_PER_1000NM}/t per "
                f"1,000nm × {distance:.0f}nm × {vessel_class.name} multiplier {multiplier}."
            )
        else:
            notes.append(f"No route data found for {country} → {destination_port.name}.")

        if not compatibility.compatible:
            notes.append(f"{vessel_class.name} does not fit {destination_port.name} — see compatibility.checks.")

        results.append(
            OriginResult(
                origin_country=country,
                route=route,
                vessel_class=vessel_class,
                compatibility=compatibility,
                estimated_freight_usd_per_tonne=cost_per_tonne,
                estimated_total_cost_usd=total_cost,
                market_signal=market_signal,
                notes=notes,
            )
        )

    # Rank by total cost ascending; incompatible or cost-unknown origins sort last.
    def sort_key(r: OriginResult) -> tuple:
        return (0 if r.compatibility.compatible else 1, r.estimated_total_cost_usd if r.estimated_total_cost_usd is not None else float("inf"))

    results.sort(key=sort_key)
    return results


def pareto_rank(db: Session, destination_port: Port, cargo_tonnes: float, origins: list[str], weights: tuple[float, float, float] = (0.5, 0.25, 0.25)) -> dict:
    """Multi-objective ranking (#26): cost, transit time and route risk are all minimised. Returns each
    origin's three objectives, whether it is Pareto-optimal, who dominates it, and a weighted top three."""
    from app.services.risk import compute_route_risk

    results = compare_origins(db, destination_port, cargo_tonnes, origins, market_signal=MarketSignal("OCEAN_GULF_JAPAN", None, None))
    rows = []
    for r in results:
        if r.estimated_freight_usd_per_tonne is None or not r.route or not r.route.typical_transit_days:
            continue
        risk = compute_route_risk(db, r.origin_country, destination_port).composite_score
        rows.append({"origin": r.origin_country, "cost": float(r.estimated_freight_usd_per_tonne), "days": float(r.route.typical_transit_days), "risk": float(risk),
                     "vessel_class": r.vessel_class.name, "fits_berth": r.compatibility.compatible})
    for a in rows:
        a["dominated_by"] = [b["origin"] for b in rows if b is not a and all(b[k] <= a[k] for k in ("cost", "days", "risk")) and any(b[k] < a[k] for k in ("cost", "days", "risk"))]
        a["pareto"] = not a["dominated_by"]
    if rows:
        lo = {k: min(r[k] for r in rows) for k in ("cost", "days", "risk")}
        hi = {k: max(r[k] for r in rows) for k in ("cost", "days", "risk")}
        wc, wd, wr = weights
        for a in rows:
            n = {k: (a[k] - lo[k]) / (hi[k] - lo[k]) if hi[k] > lo[k] else 0.0 for k in lo}
            a["score"] = round(wc * n["cost"] + wd * n["days"] + wr * n["risk"], 3)
        rows.sort(key=lambda a: a["score"])
        for i, a in enumerate(rows, 1):
            a["rank"] = i
    return {"port": destination_port.name, "cargo_tonnes": cargo_tonnes, "weights": {"cost": weights[0], "time": weights[1], "risk": weights[2]}, "options": rows,
            "note": "Cost is the illustrative distance-based estimate; time is the route's typical transit; risk is the composite route risk (0-10). Lower is better on all three. Scores are min-max normalised across these origins, so they rank only within this set."}
