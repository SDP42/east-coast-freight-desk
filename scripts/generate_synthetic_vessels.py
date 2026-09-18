"""Generate synthetic vessels for the map/demo UI (feature #13 — real AIS data
is paid, so this creates clearly-labeled `is_synthetic=True` vessels sized
consistently with each vessel class's real DWT/LOA/beam/draft bands).

Run from the backend venv: ../backend/.venv/bin/python3 generate_synthetic_vessels.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models import Vessel, VesselClass  # noqa: E402

VESSELS_PER_CLASS = 5
NAME_PREFIXES = ["MV", "Ocean", "Cape", "Star", "Bulk"]
NAME_SUFFIXES = ["Trader", "Voyager", "Pioneer", "Endeavour", "Navigator", "Horizon", "Pathfinder"]
FLAGS = ["Panama", "Marshall Islands", "Liberia", "Hong Kong", "Singapore", "India"]


def random_name(rng: random.Random) -> str:
    return f"{rng.choice(NAME_PREFIXES)} {rng.choice(NAME_SUFFIXES)}"


def main() -> None:
    rng = random.Random(42)  # deterministic — reproducible demo data
    db = SessionLocal()

    if db.query(Vessel).count():
        print("Vessels already generated — skipping.")
        db.close()
        return

    classes = db.query(VesselClass).all()
    if not classes:
        print("Vessel classes not seeded yet — run seed_ports.py first.")
        db.close()
        return

    count = 0
    for vc in classes:
        for i in range(VESSELS_PER_CLASS):
            dwt = rng.uniform(float(vc.dwt_min), float(vc.dwt_max))
            db.add(
                Vessel(
                    imo=f"SYN{vc.id}{i:03d}",
                    name=random_name(rng),
                    vessel_class_id=vc.id,
                    dwt=round(dwt, 1),
                    loa_m=vc.typical_loa_m,
                    beam_m=vc.typical_beam_m,
                    draft_m=vc.typical_draft_m,
                    flag=rng.choice(FLAGS),
                    built_year=rng.randint(2008, 2024),
                    is_synthetic=True,
                )
            )
            count += 1

    db.commit()
    print(f"Generated {count} synthetic vessels across {len(classes)} vessel classes "
          f"(clearly flagged is_synthetic=True — real AIS data is a paid upgrade path).")
    db.close()


if __name__ == "__main__":
    main()
