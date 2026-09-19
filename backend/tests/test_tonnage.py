"""Open-tonnage import and matching tests (the ship-availability module)."""

from datetime import date, timedelta

import pytest

from app.db.session import SessionLocal
from app.models import OpenTonnage, Port
from app.services import tonnage

CSV = b"""Vessel,DWT,Open Port,Open Date,Draft,LOA
MV Alpha,82000,Hay Point,2026-09-22,14.2,229
MV Beta,180000,Hay Point,2026-09-22,18.1,292
MV Gamma,76000,Atlantis,2026-09-22,,
MV Bad,5,Hay Point,2026-09-22,,
,70000,Hay Point,2026-09-22,,
"""


@pytest.fixture()
def db():
    s = SessionLocal()
    if not s.query(Port).filter(Port.name == "Paradip").first():
        pytest.skip("database not seeded")
    saved = s.query(OpenTonnage).all()
    for r in saved:
        s.expunge(r)
    s.query(OpenTonnage).delete()
    s.commit()
    yield s
    s.query(OpenTonnage).delete()
    s.commit()
    s.close()


def test_upload_reads_loose_headers_and_reports_bad_rows():
    rows, errors = tonnage.parse_upload(CSV, "list.csv")
    assert [r["vessel_name"] for r in rows] == ["MV Alpha", "MV Beta", "MV Gamma"]
    assert {e["line"] for e in errors} == {5, 6}  # the deadweight of 5 t and the missing name


def test_upload_needs_the_required_columns():
    with pytest.raises(ValueError, match="needs columns"):
        tonnage.parse_upload(b"a,b\n1,2\n", "x.csv")


def test_no_list_means_no_answer_not_a_fake_one(db):
    m = tonnage.match(db, "Paradip", 60000, 30)
    assert m["total_on_lists"] == 0 and "No open-tonnage list" in m["summary"]


def test_matching_sizes_fits_and_times_ships(db):
    today = date(2026, 9, 19)
    tonnage.add_rows(db, [
        {"vessel_name": "Right size", "dwt": 76000, "open_port": "Hay Point", "open_date": today + timedelta(days=2), "draft_m": 13.9, "loa_m": 225.0, "speed_knots": 12.5},
        {"vessel_name": "Too big", "dwt": 180000, "open_port": "Hay Point", "open_date": today + timedelta(days=2)},
        {"vessel_name": "Too late", "dwt": 76000, "open_port": "Hay Point", "open_date": today + timedelta(days=40)},
        {"vessel_name": "Unknown port", "dwt": 76000, "open_port": "Atlantis", "open_date": today + timedelta(days=2)},
    ], None)
    m = tonnage.match(db, "Paradip", 60000, 30, today=today)
    by = {r["vessel"]: r for r in m["matches"]}
    assert by["Right size"]["status"] == "suitable" and by["Right size"]["eta"] is not None
    assert by["Too big"]["status"] == "not suitable" and any("55%" in x for x in by["Too big"]["reasons"])
    assert by["Too late"]["status"] == "not suitable" and any("deadline" in x for x in by["Too late"]["reasons"])
    assert by["Unknown port"]["status"] == "unknown timing"
    assert m["matches"][0]["vessel"] == "Right size"


def test_stale_and_sample_lists_are_flagged(db):
    tonnage.add_rows(db, tonnage.sample_rows(), None, is_sample=True)
    m = tonnage.match(db, "Paradip", 60000, 30)
    assert m["any_sample"] is True and m["total_on_lists"] == 10 and m["suitable_count"] >= 1
