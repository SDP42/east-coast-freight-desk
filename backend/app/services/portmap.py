"""Data for the port map — feature #19 (AIS-lite congestion view).

Ports, their berth-fit and their congestion score are real (Sections 3 and 7,
9). Vessel positions and anchorage queue counts are SIMULATED: real AIS is a
paid feed we don't have, so synthetic vessels (flagged `is_synthetic` in the
database since Section 3) sail along hand-placed sea-lane waypoints, and the
response says so explicitly. Only origins whose sea lanes stay in the Indian
Ocean / Bay of Bengal frame are animated (Australia, Indonesia, Mozambique);
Russia and US routes run via Suez or the Cape and fall outside the map."""

import math
import time
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Port, Vessel, VesselClass
from app.services.compatibility import check_compatibility
from app.services.risk import _congestion_score

# Sea-lane waypoints (lat, lon), origin end first; the destination port is appended.
LANES = {
    "Australia": [(-21.28, 149.30), (-10.60, 142.00), (-9.00, 125.00), (-9.00, 112.00), (-6.00, 100.00), (4.00, 92.00)],
    "Indonesia": [(-3.32, 114.59), (-3.50, 109.00), (1.30, 104.00), (5.50, 98.00), (8.00, 92.00)],
    "Mozambique": [(-14.50, 40.70), (-8.00, 55.00), (-1.00, 68.00), (5.50, 80.00), (11.00, 86.00)],
}
LANE_TRANSIT_DAYS = {"Australia": 16.3, "Indonesia": 9.4, "Mozambique": 10.4}
LANE_DESTINATIONS = ["Paradip", "Visakhapatnam", "Dhamra", "Haldia", "Gangavaram", "Gopalpur"]
ORIGIN_COUNTRIES = list(LANES)

# One real second of wall-clock = this many simulated days, so a 9-day voyage
# takes about a minute to watch instead of nine days.
SIM_DAYS_PER_REAL_SECOND = 0.125
MAX_VESSELS = 15


@dataclass
class PortPin:
    id: int
    name: str
    latitude: float
    longitude: float
    is_destination: bool
    country: str
    max_draft_m: float | None
    max_loa_m: float | None
    tidal_restricted: bool
    annual_capacity_mtpa: float | None
    avg_turnaround_hours: float | None
    congestion_score: float
    congestion_label: str
    classes_accepted: list[str]
    simulated_queue: int


def _label(score: float) -> str:
    return "Low" if score < 3 else "Moderate" if score < 5.5 else "High" if score < 7.5 else "Severe"


def _simulated_queue(port: Port, now: float) -> int:
    """Vessels notionally waiting at anchorage: scales with port throughput and
    tidal restriction, drifting slowly over time. Illustrative only."""
    base = (float(port.annual_capacity_mtpa or 20) / 25) + (2 if port.tidal_restricted else 0)
    wobble = 1.2 * math.sin(now / 45 + port.id) + 0.6 * math.sin(now / 17 + port.id * 2)
    return max(0, round(base + wobble))


def build_map_overview(db: Session, scope: list[str] | None = None) -> dict:
    now = time.time()
    vessel_classes = db.query(VesselClass).order_by(VesselClass.dwt_min).all()
    ports = db.query(Port).filter(Port.latitude.isnot(None)).all()
    if scope is not None:
        ports = [p for p in ports if p.name in scope]

    pins: list[PortPin] = []
    for p in ports:
        score, _ = _congestion_score(p, db) if p.is_destination else (0.0, "")
        accepted = [vc.name for vc in vessel_classes if check_compatibility(p, vc).compatible] if p.is_destination else []
        pins.append(
            PortPin(
                id=p.id, name=p.name, latitude=float(p.latitude), longitude=float(p.longitude),
                is_destination=p.is_destination, country=p.country,
                max_draft_m=float(p.max_draft_m) if p.max_draft_m else None,
                max_loa_m=float(p.max_loa_m) if p.max_loa_m else None,
                tidal_restricted=bool(p.tidal_restricted),
                annual_capacity_mtpa=float(p.annual_capacity_mtpa) if p.annual_capacity_mtpa else None,
                avg_turnaround_hours=float(p.avg_turnaround_hours) if p.avg_turnaround_hours else None,
                congestion_score=round(score, 1), congestion_label=_label(score) if p.is_destination else "",
                classes_accepted=accepted,
                simulated_queue=_simulated_queue(p, now) if p.is_destination else 0,
            )
        )

    dest_by_name = {p.name: p for p in ports if p.is_destination}
    routes = []
    for country in ORIGIN_COUNTRIES:
        for dest_name in LANE_DESTINATIONS:
            dest = dest_by_name.get(dest_name)
            if not dest:
                continue
            routes.append({
                "key": f"{country}->{dest_name}", "origin_country": country, "destination": dest_name,
                "transit_days": LANE_TRANSIT_DAYS[country],
                "waypoints": [list(w) for w in LANES[country]] + [[float(dest.latitude), float(dest.longitude)]],
            })

    vessels_db = db.query(Vessel).order_by(Vessel.id).limit(MAX_VESSELS).all()
    allowed_routes = {r["key"] for r in routes}
    classes_by_id = {vc.id: vc.name for vc in vessel_classes}
    vessels = []
    for i, v in enumerate(vessels_db):
        country = ORIGIN_COUNTRIES[i % len(ORIGIN_COUNTRIES)]
        dest_name = LANE_DESTINATIONS[(i // len(ORIGIN_COUNTRIES) + i) % len(LANE_DESTINATIONS)]
        route_key = f"{country}->{dest_name}"
        if route_key not in allowed_routes:
            continue
        transit_real_seconds = LANE_TRANSIT_DAYS[country] / SIM_DAYS_PER_REAL_SECOND
        progress = ((now / transit_real_seconds) + i * 0.137) % 1.0
        vessels.append({
            "id": v.id, "name": v.name, "vessel_class": classes_by_id.get(v.vessel_class_id, "Unknown"),
            "route_key": route_key, "progress": round(progress, 4),
            "progress_per_second": round(1 / transit_real_seconds, 6),
        })

    return {
        "ports": [p.__dict__ for p in pins],
        "routes": routes,
        "vessels": vessels,
        "simulated": True,
        "note": (
            "Ports, berth fit and congestion scores are real. Vessel positions and anchorage queues are SIMULATED "
            "(real AIS is a paid feed): synthetic vessels sail hand-placed sea lanes at accelerated speed. "
            "Russia and US routes run via Suez or the Cape and fall outside this map."
        ),
    }
