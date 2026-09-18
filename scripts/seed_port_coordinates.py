"""Add approximate coordinates to the seeded ports so they can be drawn on the
map. These are well-known port locations rounded to two decimals — good enough
to place a marker, not survey-grade. Origin entries are representative export
terminals for each country, matching the generic origin ports seeded earlier.

Run from the backend venv: ../backend/.venv/bin/python3 seed_port_coordinates.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models import Port  # noqa: E402

COORDINATES = {
    "Paradip": (20.26, 86.67),
    "Visakhapatnam": (17.69, 83.29),
    "Gangavaram": (17.62, 83.23),
    "Dhamra": (20.79, 86.97),
    "Gopalpur": (19.27, 84.90),
    "Sagar / Sandheads": (21.05, 88.15),
    "Haldia": (22.03, 88.07),
    "Hay Point / Dalrymple Bay": (-21.28, 149.30),
    "US Gulf Coast (generic)": (29.00, -89.40),
    "Nacala / Beira (generic)": (-14.50, 40.70),
    "Ust-Luga / Vostochny (generic)": (59.68, 28.40),
    "Kalimantan (generic)": (-3.32, 114.59),
}


def main() -> None:
    db = SessionLocal()
    updated = 0
    for name, (lat, lon) in COORDINATES.items():
        port = db.query(Port).filter(Port.name == name).first()
        if port is None:
            print(f"  not found: {name}")
            continue
        port.latitude, port.longitude = lat, lon
        updated += 1
    db.commit()
    print(f"Set coordinates on {updated}/{len(COORDINATES)} ports.")
    db.close()


if __name__ == "__main__":
    main()
