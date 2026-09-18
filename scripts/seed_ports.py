"""Seed real port, berth, and vessel-class reference data from our own
research compendium (Table 1: East Coast port draft/LOA/capacity, and the
vessel class spec table) into the database.

Run from the backend venv: ../backend/.venv/bin/python3 seed_ports.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models import Port, VesselClass  # noqa: E402

CITATION = "SIH2026_Research_and_References.docx, Table 1 & Section 2"

# India East Coast destination ports — real figures from our compiled research.
EAST_COAST_PORTS = [
    dict(name="Paradip", country="India", is_destination=True, max_draft_m=16.5, max_loa_m=300,
         max_beam_m=48, tidal_restricted=False, annual_capacity_mtpa=150.41, avg_turnaround_hours=41.61,
         notes="Two dedicated coal berths (~20 MTPA); first Capesize berthed Sept 2026 at 16.5m draft.",
         source=CITATION),
    dict(name="Visakhapatnam", country="India", is_destination=True, max_draft_m=18.1, max_loa_m=390,
         max_beam_m=50, tidal_restricted=False, annual_capacity_mtpa=82.62, avg_turnaround_hours=None,
         notes="Outer harbour handles Capesize; Adani coal terminal (EQ1) limited to 14.5m draft.",
         source=CITATION),
    dict(name="Gangavaram", country="India", is_destination=True, max_draft_m=18.0, max_loa_m=None,
         max_beam_m=None, tidal_restricted=False, annual_capacity_mtpa=64.0, avg_turnaround_hours=None,
         notes="Capesize to 200,000 DWT; two mechanised coal berths (~20 MTPA).", source=CITATION),
    dict(name="Dhamra", country="India", is_destination=True, max_draft_m=18.0, max_loa_m=None,
         max_beam_m=None, tidal_restricted=False, annual_capacity_mtpa=100.0, avg_turnaround_hours=None,
         notes="18m channel; Capesize up to ~180,000 DWT; capacity expanded 4x (announced).",
         source=CITATION),
    dict(name="Gopalpur", country="India", is_destination=True, max_draft_m=14.2, max_loa_m=290,
         max_beam_m=45, tidal_restricted=False, annual_capacity_mtpa=20.0, avg_turnaround_hours=None,
         notes="Handysize/Supramax only — draft-limited. ~6 MT actual vs. 20 MTPA design capacity.",
         source=CITATION),
    dict(name="Sagar / Sandheads", country="India", is_destination=True, max_draft_m=10.5, max_loa_m=None,
         max_beam_m=None, tidal_restricted=True, max_vessels_per_tide=None, annual_capacity_mtpa=17.03,
         avg_turnaround_hours=None,
         notes="Anchorage draft 9.5-10.5m; river berths 7.1-9m. Larger vessels transload via barge to Haldia.",
         source=CITATION),
    dict(name="Haldia", country="India", is_destination=True, max_draft_m=None, max_loa_m=240,
         max_beam_m=32.26, tidal_restricted=True, max_vessels_per_tide=3, annual_capacity_mtpa=46.99,
         avg_turnaround_hours=None,
         notes="Tidal lock limits transits to 3 vessels/tide; Panamax can only partial-load per tide.",
         source=CITATION),
]

# Origin (loading) ports/countries named in the problem statement — coordinates
# are country-representative major coal export terminals, not exhaustive.
ORIGIN_PORTS = [
    dict(name="Hay Point / Dalrymple Bay", country="Australia", is_destination=False, source=CITATION),
    dict(name="US Gulf Coast (generic)", country="United States", is_destination=False, source=CITATION),
    dict(name="Nacala / Beira (generic)", country="Mozambique", is_destination=False, source=CITATION),
    dict(name="Ust-Luga / Vostochny (generic)", country="Russia", is_destination=False, source=CITATION),
    dict(name="Kalimantan (generic)", country="Indonesia", is_destination=False, source=CITATION),
]

VESSEL_CLASSES = [
    dict(name="Handysize", dwt_min=15000, dwt_max=39999, typical_loa_m=170, typical_beam_m=27, typical_draft_m=10.0),
    dict(name="Supramax", dwt_min=40000, dwt_max=64999, typical_loa_m=190, typical_beam_m=32, typical_draft_m=12.0),
    dict(name="Panamax", dwt_min=65000, dwt_max=89999, typical_loa_m=229, typical_beam_m=32.2, typical_draft_m=12.04),
    dict(name="Capesize", dwt_min=90000, dwt_max=200000, typical_loa_m=290, typical_beam_m=45, typical_draft_m=17.0),
]


def main() -> None:
    db = SessionLocal()

    if db.query(Port).count() or db.query(VesselClass).count():
        print("Ports/vessel classes already seeded — skipping (clear the tables first to re-run).")
        db.close()
        return

    for spec in EAST_COAST_PORTS + ORIGIN_PORTS:
        db.add(Port(**spec))
    for spec in VESSEL_CLASSES:
        db.add(VesselClass(**spec))

    db.commit()
    print(f"Seeded {len(EAST_COAST_PORTS)} East Coast ports, {len(ORIGIN_PORTS)} origin ports, "
          f"{len(VESSEL_CLASSES)} vessel classes.")
    db.close()


if __name__ == "__main__":
    main()
