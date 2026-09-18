"""Financial modeling module — Section 10, features #7 (COA-vs-Spot), #8
(idle-time/ballast minimizer), #9 (demurrage estimator), plus an ROI
calculator. All cost figures are explicitly labeled illustrative — built from
real ingested freight-index data and real researched benchmarks (our
compendium's demurrage-rate ranges, port turnaround data), not live quotes,
consistent with every other financial estimate in this project.
"""

from dataclasses import dataclass, field
from datetime import date

import numpy as np
from sqlalchemy.orm import Session

from app.ml.arima_model import fit_best_arima, forecast
from app.models import Port, Route, VesselClass
from app.services.freight_data import load_series

# Real researched demurrage benchmarks (SIH2026 research compendium, Section
# 3.6): Panamax/Kamsarmax ~$8,000-15,000/day, Capesize >$30,000/day during
# congestion. Supramax/Handysize figures are not directly cited in our
# research and are extrapolated proportionally — flagged as such.
DEMURRAGE_RATE_USD_PER_DAY = {
    "Capesize": 30_000,
    "Panamax": 11_500,
    "Supramax": 8_000,
    "Handysize": 5_500,
}

NATIONAL_AVG_TURNAROUND_HOURS = 49.5


# ---------------------------------------------------------------------------
# COA vs Spot Simulator
# ---------------------------------------------------------------------------

@dataclass
class FixtureProjection:
    fixture_number: int
    date: date
    forecast_index_value: float
    projected_spot_rate_usd_per_tonne: float


@dataclass
class CoaVsSpotResult:
    index_name: str
    current_index_value: float
    current_rate_usd_per_tonne: float
    coa_rate_usd_per_tonne: float
    fixtures: list[FixtureProjection]
    total_coa_cost_usd: float
    total_spot_cost_usd: float
    spot_cost_std_usd: float
    expected_savings_usd: float
    recommendation: str
    rationale: str


def simulate_coa_vs_spot(
    db: Session,
    index_name: str,
    current_rate_usd_per_tonne: float,
    cargo_tonnes_per_fixture: float,
    num_fixtures: int,
    interval_days: int,
) -> CoaVsSpotResult:
    series = load_series(db, index_name)
    if series.empty or len(series) < 200:
        raise ValueError(f"Not enough history for {index_name} to run this simulation")

    current_index_value = float(series.iloc[-1])
    horizon = num_fixtures * interval_days
    best = fit_best_arima(series)
    forecast_values = forecast(best, horizon)

    # Historical daily volatility, used to size the uncertainty band around
    # each projected spot fixture — real data, not an assumption.
    daily_returns = series.pct_change().dropna().iloc[-180:]
    daily_vol = float(daily_returns.std())

    fixtures: list[FixtureProjection] = []
    spot_costs: list[float] = []
    for i in range(num_fixtures):
        day_offset = (i + 1) * interval_days - 1
        idx_value = float(forecast_values.iloc[min(day_offset, horizon - 1)])
        projected_rate = current_rate_usd_per_tonne * (idx_value / current_index_value)
        fixtures.append(
            FixtureProjection(
                fixture_number=i + 1,
                date=forecast_values.index[min(day_offset, horizon - 1)].date(),
                forecast_index_value=round(idx_value, 2),
                projected_spot_rate_usd_per_tonne=round(projected_rate, 2),
            )
        )
        spot_costs.append(projected_rate * cargo_tonnes_per_fixture)

    coa_rate = current_rate_usd_per_tonne
    total_coa_cost = coa_rate * cargo_tonnes_per_fixture * num_fixtures
    total_spot_cost = float(sum(spot_costs))

    # Propagate index volatility into a $ cost std-dev estimate for the spot
    # path — an approximation (index vol scaled onto the $/tonne conversion),
    # not a full Monte Carlo, but grounded in real historical volatility.
    spot_cost_std = float(
        current_rate_usd_per_tonne * daily_vol * np.sqrt(interval_days) * cargo_tonnes_per_fixture * np.sqrt(num_fixtures)
    )

    savings = total_spot_cost - total_coa_cost
    if abs(savings) < 0.03 * total_coa_cost:
        recommendation = "Marginal — either approach is reasonable"
    elif savings > 0:
        recommendation = "Lock in COA"
    else:
        recommendation = "Stay spot"

    rationale = (
        f"Model forecasts {index_name} moving from {current_index_value:.0f} to "
        f"~{fixtures[-1].forecast_index_value:.0f} over the next {horizon} days "
        f"({'up' if fixtures[-1].forecast_index_value > current_index_value else 'down'} "
        f"{abs(fixtures[-1].forecast_index_value / current_index_value - 1) * 100:.1f}%). "
        f"Locking today's rate ({coa_rate:.2f}/t) for all {num_fixtures} fixtures "
        f"{'avoids' if savings > 0 else 'forgoes'} an estimated ${abs(savings):,.0f} "
        f"vs. staying spot at the model's forecasted path, with spot exposed to "
        f"±${spot_cost_std:,.0f} of historical-volatility-driven uncertainty that COA eliminates."
    )

    return CoaVsSpotResult(
        index_name=index_name,
        current_index_value=round(current_index_value, 2),
        current_rate_usd_per_tonne=current_rate_usd_per_tonne,
        coa_rate_usd_per_tonne=round(coa_rate, 2),
        fixtures=fixtures,
        total_coa_cost_usd=round(total_coa_cost, 2),
        total_spot_cost_usd=round(total_spot_cost, 2),
        spot_cost_std_usd=round(spot_cost_std, 2),
        expected_savings_usd=round(savings, 2),
        recommendation=recommendation,
        rationale=rationale,
    )


# ---------------------------------------------------------------------------
# Idle-time / ballast-leg minimizer
# ---------------------------------------------------------------------------

@dataclass
class BallastOption:
    origin_country: str
    destination_port_name: str
    estimated_ballast_days: float
    laycan_wait_days: float
    total_idle_days: float
    notes: str


def rank_ballast_options(
    db: Session,
    candidates: list[tuple[str, int, date | None]],  # (origin_country, destination_port_id, laycan_start)
) -> list[BallastOption]:
    today = date(2026, 9, 18)
    options: list[BallastOption] = []

    for origin_country, destination_port_id, laycan_start in candidates:
        destination = db.query(Port).filter(Port.id == destination_port_id).first()
        route = (
            db.query(Route)
            .join(Port, Route.origin_port_id == Port.id)
            .filter(Port.country == origin_country, Route.destination_port_id == destination_port_id)
            .first()
        )
        if not destination or not route or not route.typical_transit_days:
            continue

        # Simplifying assumption (clearly flagged): ballast transit time to
        # reach the loading port approximates the laden transit time on the
        # reverse leg — we don't have separate ballast-route distance data.
        ballast_days = float(route.typical_transit_days)
        laycan_wait = max(0.0, (laycan_start - today).days) if laycan_start else 0.0
        total_idle = ballast_days + laycan_wait

        options.append(
            BallastOption(
                origin_country=origin_country,
                destination_port_name=destination.name,
                estimated_ballast_days=round(ballast_days, 1),
                laycan_wait_days=round(laycan_wait, 1),
                total_idle_days=round(total_idle, 1),
                notes="Ballast leg approximated from the laden-route transit time (no separate ballast-route distance data available).",
            )
        )

    options.sort(key=lambda o: o.total_idle_days)
    return options


# ---------------------------------------------------------------------------
# Demurrage risk estimator
# ---------------------------------------------------------------------------

@dataclass
class DemurrageEstimate:
    port_name: str
    vessel_class_name: str
    actual_turnaround_days: float
    laytime_allowed_days: float
    demurrage_days: float
    demurrage_rate_usd_per_day: float
    expected_demurrage_usd: float
    notes: list[str] = field(default_factory=list)


def estimate_demurrage(port: Port, vessel_class: VesselClass, laytime_allowed_days: float) -> DemurrageEstimate:
    notes = []
    if port.avg_turnaround_hours:
        actual_days = float(port.avg_turnaround_hours) / 24
    else:
        actual_days = NATIONAL_AVG_TURNAROUND_HOURS / 24
        notes.append(f"{port.name} has no turnaround data on file; defaulted to the national average ({NATIONAL_AVG_TURNAROUND_HOURS}h).")

    demurrage_days = max(0.0, actual_days - laytime_allowed_days)
    rate = DEMURRAGE_RATE_USD_PER_DAY.get(vessel_class.name, 8_000)
    if vessel_class.name not in ("Capesize", "Panamax"):
        notes.append(f"{vessel_class.name} demurrage rate is extrapolated, not directly cited in our research (only Panamax/Capesize benchmarks were found).")

    return DemurrageEstimate(
        port_name=port.name,
        vessel_class_name=vessel_class.name,
        actual_turnaround_days=round(actual_days, 2),
        laytime_allowed_days=laytime_allowed_days,
        demurrage_days=round(demurrage_days, 2),
        demurrage_rate_usd_per_day=rate,
        expected_demurrage_usd=round(demurrage_days * rate, 2),
        notes=notes,
    )


# ---------------------------------------------------------------------------
# ROI calculator
# ---------------------------------------------------------------------------

@dataclass
class RoiEstimate:
    index_name: str
    historical_coefficient_of_variation_pct: float
    annual_cargo_tonnes: float
    assumed_freight_usd_per_tonne: float
    captured_pct: float
    estimated_annual_savings_usd: float
    notes: str


def estimate_roi(
    db: Session,
    index_name: str,
    annual_cargo_tonnes: float,
    assumed_freight_usd_per_tonne: float,
    captured_pct: float = 20.0,
) -> RoiEstimate:
    series = load_series(db, index_name)
    if series.empty:
        raise ValueError(f"No data for {index_name}")

    recent = series.iloc[-365:] if len(series) >= 365 else series
    cv_pct = float(recent.std() / recent.mean() * 100) if recent.mean() else 0.0

    # The historical spread (CV%) represents the cost variance a purely
    # reactive, un-timed procurement process is exposed to; "captured_pct" is
    # a conservative, user-adjustable assumption for how much of that spread
    # better timing recovers — not a guarantee, explicitly labeled illustrative.
    avoidable_cost_pct = cv_pct * (captured_pct / 100)
    savings = annual_cargo_tonnes * assumed_freight_usd_per_tonne * (avoidable_cost_pct / 100)

    return RoiEstimate(
        index_name=index_name,
        historical_coefficient_of_variation_pct=round(cv_pct, 2),
        annual_cargo_tonnes=annual_cargo_tonnes,
        assumed_freight_usd_per_tonne=assumed_freight_usd_per_tonne,
        captured_pct=captured_pct,
        estimated_annual_savings_usd=round(savings, 2),
        notes=(
            f"Illustrative, not a guarantee: {index_name}'s real historical volatility (CV={cv_pct:.1f}%) "
            f"is the raw cost-variance opportunity; assumes better-timed chartering captures "
            f"{captured_pct:.0f}% of that spread as avoided cost."
        ),
    )
