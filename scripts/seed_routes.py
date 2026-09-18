"""Seed origin->destination trade lane routes linking the 5 origin countries
to the 7 East Coast destination ports.

Distances here are order-of-magnitude approximations (typical sailing
distances for the origin region to India's East Coast), not port-pair-exact
routing distances — good enough for a hackathon prototype's relative
comparisons (e.g. "Indonesia is much closer than the US"), but should be
replaced with exact great-circle/routing distances (e.g. via searoutes.com or
a routing API) before treating absolute numbers as authoritative.

Run from the backend venv: ../backend/.venv/bin/python3 seed_routes.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models import Port, Route  # noqa: E402

# (origin country, approx distance to India East Coast in nautical miles, approx transit days at 12 knots)
ORIGIN_DISTANCES = {
    "Australia": 4700,
    "United States": 11500,
    "Mozambique": 3000,
    "Russia": 10500,
    "Indonesia": 2700,
}


def main() -> None:
    db = SessionLocal()

    if db.query(Route).count():
        print("Routes already seeded — skipping.")
        db.close()
        return

    origins = db.query(Port).filter(Port.is_destination.is_(False)).all()
    destinations = db.query(Port).filter(Port.is_destination.is_(True)).all()

    if not origins or not destinations:
        print("Ports not seeded yet — run seed_ports.py first.")
        db.close()
        return

    count = 0
    for origin in origins:
        distance = ORIGIN_DISTANCES.get(origin.country)
        if distance is None:
            continue
        for dest in destinations:
            db.add(
                Route(
                    origin_port_id=origin.id,
                    destination_port_id=dest.id,
                    distance_nm=distance,
                    typical_transit_days=round(distance / (12 * 24), 1),  # 12 knots, rough
                    primary_commodity="coking_coal" if origin.country in ("Australia", "Mozambique", "United States") else "thermal_coal",
                )
            )
            count += 1

    db.commit()
    print(f"Seeded {count} origin-destination routes ({len(origins)} origins x {len(destinations)} destinations).")
    db.close()


if __name__ == "__main__":
    main()
