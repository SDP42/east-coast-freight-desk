"""Composite Route Risk Score — feature #6 in FEATURES.md. Combines three
independent signals into one 0-10 score with a breakdown, rather than
presenting a single unexplained number:

1. Disruption exposure — the 4 real documented events seeded in Section 3
   (Red Sea/Suez, Panama Canal, Cyclone Koji, Russia sanctions), weighted by
   relevance to the specific origin country and by recency.
2. Port congestion — derived from the destination port's real researched
   turnaround-time/tidal-restriction data (Section 3 seed).
3. Short-term freight volatility — the coefficient of variation of the last
   90 days of the relevant Baltic sub-index, computed directly from real
   ingested data (not a model fit, so this is fast enough for a live request,
   unlike the full ARIMA backtest in Section 5/6).
"""

from dataclasses import dataclass
from datetime import date

import numpy as np
from sqlalchemy.orm import Session

from app.models import DisruptionEvent, Port
from app.services.freight_data import load_series

NATIONAL_AVG_TURNAROUND_HOURS = 49.5  # our own research compendium, Section 3.3
GLOBAL_SPILLOVER_CATEGORIES = {"geopolitical", "canal_strait"}
GLOBAL_SPILLOVER_WEIGHT = 0.3
DIRECT_MATCH_WEIGHT = 1.0

TODAY = date(2026, 9, 18)


@dataclass
class RiskFactor:
    name: str
    score: float  # 0-10
    weight: float
    detail: str


@dataclass
class RelevantEvent:
    title: str
    category: str
    region: str
    start_date: date
    impact_score: float
    relevance_weight: float


@dataclass
class RouteRiskResult:
    origin_country: str
    destination_port_name: str
    composite_score: float
    risk_label: str
    factors: list[RiskFactor]
    relevant_events: list[RelevantEvent]


def _recency_factor(event_date: date) -> float:
    years_ago = (TODAY - event_date).days / 365.25
    if years_ago <= 2:
        return 1.0
    if years_ago <= 4:
        return 0.6
    return 0.3


def _disruption_score(db: Session, origin_country: str) -> tuple[float, list[RelevantEvent]]:
    events = db.query(DisruptionEvent).all()
    relevant: list[RelevantEvent] = []
    total = 0.0

    for e in events:
        weight = 0.0
        if origin_country.lower() in e.region.lower():
            weight = DIRECT_MATCH_WEIGHT
        elif e.category in GLOBAL_SPILLOVER_CATEGORIES:
            weight = GLOBAL_SPILLOVER_WEIGHT

        if weight == 0.0:
            continue

        recency = _recency_factor(e.start_date)
        contribution = float(e.impact_score or 0) * weight * recency
        total += contribution
        relevant.append(
            RelevantEvent(
                title=e.title, category=e.category, region=e.region,
                start_date=e.start_date, impact_score=float(e.impact_score or 0),
                relevance_weight=round(weight * recency, 2),
            )
        )

    return min(total, 10.0), relevant


def _congestion_score(port: Port) -> tuple[float, str]:
    if port.avg_turnaround_hours:
        hours = float(port.avg_turnaround_hours)
        score = max(0.0, min(10.0, (hours - 30) / 4))
        detail = f"{port.name} avg. turnaround {hours}h vs. national avg {NATIONAL_AVG_TURNAROUND_HOURS}h"
    elif port.tidal_restricted:
        score, detail = 6.0, f"{port.name} turnaround data unavailable; tide-restricted port defaults to elevated congestion risk"
    else:
        score, detail = 3.0, f"{port.name} turnaround data unavailable; defaulted to moderate risk"
    return score, detail


def _volatility_score(db: Session, index_name: str = "BDI") -> tuple[float, str]:
    series = load_series(db, index_name)
    if series.empty or len(series) < 90:
        return 3.0, f"Insufficient {index_name} history for volatility estimate; defaulted to moderate risk"

    recent = series.iloc[-90:]
    cv_pct = float(recent.std() / recent.mean() * 100) if recent.mean() else 0.0
    score = max(0.0, min(10.0, cv_pct / 3))  # ~30% CV maps to a 10/10 score
    return score, f"{index_name} 90-day coefficient of variation: {cv_pct:.1f}%"


def _label(score: float) -> str:
    if score < 3:
        return "Low"
    if score < 5.5:
        return "Moderate"
    if score < 7.5:
        return "High"
    return "Severe"


def compute_route_risk(db: Session, origin_country: str, destination_port: Port) -> RouteRiskResult:
    disruption_score, relevant_events = _disruption_score(db, origin_country)
    congestion_score, congestion_detail = _congestion_score(destination_port)
    volatility_score, volatility_detail = _volatility_score(db)

    factors = [
        RiskFactor(name="disruption_exposure", score=round(disruption_score, 2), weight=0.4,
                   detail=f"{len(relevant_events)} relevant documented disruption event(s) affecting {origin_country} or global tonnage"),
        RiskFactor(name="port_congestion", score=round(congestion_score, 2), weight=0.3, detail=congestion_detail),
        RiskFactor(name="freight_volatility", score=round(volatility_score, 2), weight=0.3, detail=volatility_detail),
    ]
    composite = sum(f.score * f.weight for f in factors)

    return RouteRiskResult(
        origin_country=origin_country,
        destination_port_name=destination_port.name,
        composite_score=round(composite, 2),
        risk_label=_label(composite),
        factors=factors,
        relevant_events=relevant_events,
    )
