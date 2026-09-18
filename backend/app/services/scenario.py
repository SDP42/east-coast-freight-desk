"""Scenario / stress-testing engine — feature #12 in FEATURES.md. Re-runs the
Section 8 multi-origin comparison under user-defined shocks and reports what
changed: each origin's cost and rank, whether the best pick flipped, and — for
a port closure — which alternative discharge port would have been cheaper.

Shock types:
- freight_spike: multiplies all freight costs (e.g. "what if BDI spikes 50%").
- port_closure: the destination port is unavailable for N days; delay is priced
  at the vessel class's demurrage rate (Section 10 benchmarks) and other ports
  are ranked as reroute alternatives.
- origin_disruption / red_sea_closure: adds sailing distance to specific origins
  (Red Sea closure adds ~3,500nm via the Cape of Good Hope to Suez-routed
  origins — Russia and the US — per the documented case study in Section 3).
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models import Port, VesselClass
from app.services.financial import DEMURRAGE_RATE_USD_PER_DAY
from app.services.recommendation import (
    VESSEL_CLASS_TO_INDEX,
    OriginResult,
    compare_origins,
    get_market_signal,
    pick_vessel_class,
)

RED_SEA_EXTRA_NM = 3500.0
RED_SEA_AFFECTED_ORIGINS = ["Russia", "United States"]


@dataclass
class Shock:
    type: str
    pct: float | None = None
    days: float | None = None
    origin_country: str | None = None
    extra_distance_nm: float | None = None


@dataclass
class OriginDelta:
    origin_country: str
    baseline_cost_usd: float | None
    scenario_cost_usd: float | None
    delta_usd: float | None
    delta_pct: float | None
    baseline_rank: int
    scenario_rank: int
    compatible: bool


@dataclass
class ReroutePort:
    port_name: str
    best_origin: str
    estimated_total_cost_usd: float
    savings_vs_scenario_best_usd: float


@dataclass
class ScenarioResult:
    destination_port_name: str
    cargo_tonnes: float
    vessel_class_name: str
    shocks_applied: list[str]
    origins: list[OriginDelta]
    baseline_best_origin: str | None
    scenario_best_origin: str | None
    best_origin_changed: bool
    reroute_alternatives: list[ReroutePort] = field(default_factory=list)
    summary: str = ""


def _ranked_costs(results: list[OriginResult]) -> dict[str, tuple[int, float | None, bool]]:
    return {
        r.origin_country: (rank, r.estimated_total_cost_usd, r.compatibility.compatible)
        for rank, r in enumerate(results, start=1)
    }


def run_scenario(
    db: Session,
    destination_port: Port,
    cargo_tonnes: float,
    origin_countries: list[str],
    shocks: list[Shock],
) -> ScenarioResult:
    vessel_classes = db.query(VesselClass).order_by(VesselClass.dwt_min).all()
    vessel_class = pick_vessel_class(vessel_classes, cargo_tonnes)
    market_signal = get_market_signal(db, VESSEL_CLASS_TO_INDEX.get(vessel_class.name, "BDI"))

    freight_multiplier = 1.0
    delay_days = 0.0
    extra_distance: dict[str, float] = {}
    shock_labels: list[str] = []

    for s in shocks:
        if s.type == "freight_spike" and s.pct is not None:
            freight_multiplier *= 1 + s.pct / 100
            shock_labels.append(f"Freight rates {'+' if s.pct >= 0 else ''}{s.pct:.0f}%")
        elif s.type == "port_closure" and s.days:
            delay_days += s.days
            shock_labels.append(f"{destination_port.name} closed {s.days:.0f} days")
        elif s.type == "red_sea_closure":
            for c in RED_SEA_AFFECTED_ORIGINS:
                extra_distance[c] = extra_distance.get(c, 0.0) + RED_SEA_EXTRA_NM
            shock_labels.append(f"Red Sea closure (+{RED_SEA_EXTRA_NM:.0f}nm for {', '.join(RED_SEA_AFFECTED_ORIGINS)})")
        elif s.type == "origin_disruption" and s.origin_country and s.extra_distance_nm:
            extra_distance[s.origin_country] = extra_distance.get(s.origin_country, 0.0) + s.extra_distance_nm
            shock_labels.append(f"{s.origin_country} route +{s.extra_distance_nm:.0f}nm")

    baseline = compare_origins(db, destination_port, cargo_tonnes, origin_countries, market_signal=market_signal)
    scenario = compare_origins(
        db, destination_port, cargo_tonnes, origin_countries,
        market_signal=market_signal, extra_distance_nm=extra_distance,
    )

    demurrage_rate = DEMURRAGE_RATE_USD_PER_DAY.get(vessel_class.name, 8_000)
    delay_cost = delay_days * demurrage_rate

    def apply_shocks(cost: float | None) -> float | None:
        if cost is None:
            return None
        return round(cost * freight_multiplier + delay_cost, 2)

    for r in scenario:
        r.estimated_total_cost_usd = apply_shocks(r.estimated_total_cost_usd)
    scenario.sort(
        key=lambda r: (0 if r.compatibility.compatible else 1, r.estimated_total_cost_usd if r.estimated_total_cost_usd is not None else float("inf"))
    )

    base_map, scen_map = _ranked_costs(baseline), _ranked_costs(scenario)
    deltas: list[OriginDelta] = []
    for country in origin_countries:
        b_rank, b_cost, _ = base_map[country]
        s_rank, s_cost, s_compat = scen_map[country]
        delta = round(s_cost - b_cost, 2) if s_cost is not None and b_cost is not None else None
        delta_pct = round(delta / b_cost * 100, 1) if delta is not None and b_cost else None
        deltas.append(OriginDelta(country, b_cost, s_cost, delta, delta_pct, b_rank, s_rank, s_compat))
    deltas.sort(key=lambda d: d.scenario_rank)

    baseline_best = baseline[0].origin_country if baseline and baseline[0].compatibility.compatible else None
    scenario_best = scenario[0].origin_country if scenario and scenario[0].compatibility.compatible else None
    scenario_best_cost = scenario[0].estimated_total_cost_usd if scenario_best else None

    # Reroute alternatives only matter when the destination port itself is closed.
    reroutes: list[ReroutePort] = []
    if delay_days > 0 and scenario_best_cost is not None:
        other_ports = db.query(Port).filter(Port.is_destination.is_(True), Port.id != destination_port.id).all()
        for port in other_ports:
            alt = compare_origins(db, port, cargo_tonnes, origin_countries, market_signal=market_signal, extra_distance_nm=extra_distance)
            compatible = [a for a in alt if a.compatibility.compatible and a.estimated_total_cost_usd is not None]
            if not compatible:
                continue
            best = compatible[0]
            alt_cost = round(best.estimated_total_cost_usd * freight_multiplier, 2)
            reroutes.append(
                ReroutePort(
                    port_name=port.name, best_origin=best.origin_country,
                    estimated_total_cost_usd=alt_cost,
                    savings_vs_scenario_best_usd=round(scenario_best_cost - alt_cost, 2),
                )
            )
        reroutes.sort(key=lambda r: r.estimated_total_cost_usd)
        reroutes = reroutes[:3]

    if baseline_best and scenario_best:
        b_cost, s_cost = baseline[0].estimated_total_cost_usd, scenario_best_cost
        change = f"Best origin {'changed from ' + baseline_best + ' to ' + scenario_best if baseline_best != scenario_best else 'stays ' + scenario_best}"
        if b_cost and s_cost:
            change += f"; best-case cost moves from ${b_cost:,.0f} to ${s_cost:,.0f} ({(s_cost - b_cost) / b_cost * 100:+.1f}%)."
        summary = change
    else:
        summary = "No physically compatible origin under this scenario."

    return ScenarioResult(
        destination_port_name=destination_port.name,
        cargo_tonnes=cargo_tonnes,
        vessel_class_name=vessel_class.name,
        shocks_applied=shock_labels,
        origins=deltas,
        baseline_best_origin=baseline_best,
        scenario_best_origin=scenario_best,
        best_origin_changed=baseline_best != scenario_best,
        reroute_alternatives=reroutes,
        summary=summary,
    )
