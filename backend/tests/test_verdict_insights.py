"""Verdict, sourcing resilience and programme tests. They read the seeded local database and skip if it is empty."""

import pytest

from app.db.session import SessionLocal
from app.models import Port
from app.services import insights, verdict


@pytest.fixture(scope="module")
def db():
    s = SessionLocal()
    if not s.query(Port).filter(Port.name == "Paradip").first():
        pytest.skip("database not seeded")
    yield s
    s.close()


VALID = {"RENT NOW", "RENT WITHIN A WEEK", "WAIT AND RECHECK", "CANNOT MEET THE DATE SAFELY", "SPLIT INTO TWO PARCELS"}


def test_verdict_has_a_valid_call_and_reasons(db):
    v = verdict.build(db, "Paradip", 60000, 20)
    assert v["verdict"] in VALID and v["headline"] and v["signals"] and v["confidence"] in {"High", "Medium", "Low"}
    assert -1 <= v["score"] <= 1


def test_tight_date_never_says_wait(db):
    assert verdict.build(db, "Paradip", 60000, 16)["verdict"] != "WAIT AND RECHECK"


def test_impossible_date_is_flagged(db):
    assert verdict.build(db, "Haldia", 60000, 12)["verdict"] == "CANNOT MEET THE DATE SAFELY"


def test_parcel_too_big_for_one_ship_is_split(db):
    assert verdict.build(db, "Paradip", 150000, 40)["verdict"] == "SPLIT INTO TWO PARCELS"


def test_a_capesize_is_not_recommended_for_a_small_parcel(db):
    best = verdict.build(db, "Paradip", 60000, 45)["ship"]
    assert best["vessel_class"] != "Capesize"


def test_hhi_of_equal_mix_and_of_single_source(db):
    eq = insights.resilience(db, {"Australia": 1, "United States": 1, "Mozambique": 1, "Russia": 1})
    assert eq["hhi"] == pytest.approx(0.25, abs=0.001) and eq["effective_suppliers"] == pytest.approx(4.0, abs=0.01)
    one = insights.resilience(db, {"Australia": 1})
    assert one["hhi"] == 1.0 and one["label"] == "Concentrated"


def test_programme_range_brackets_the_base(db):
    r = insights.programme_plan(db, [{"origin": "Australia", "port": "Paradip", "cargo_tonnes": 75000, "vessel_class": "Panamax", "count": 4}])
    b = r["budget_range_inr_crore"]
    assert b["p5"] < b["p50"] < b["p95"] and b["p5"] < r["base_inr_crore"] < b["p95"] * 1.2


def test_admin_analytics_shape(db):
    a = insights.admin_analytics(db, 30)
    assert {"events", "denied", "by_role", "top_refusals"} <= set(a)


def test_current_models_report_results_honestly(db):
    from app.services import current
    c = current.current_models(db)
    assert c["data_through"] >= "2026-01-01" and c["verdicts"] and "random walk" in c["caveat"]
    assert all(h["models"]["naive"]["mae_usd_per_t"] > 0 for h in c["forecast_tests"])


def test_verdict_uses_the_current_freight_signal(db):
    names = [s["signal"] for s in verdict.build(db, "Paradip", 60000, 30)["signals"]]
    assert "Dry-bulk freight momentum" in names
