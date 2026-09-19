"""What-If and Urgent Desk tests. They read the seeded local database, so they are skipped when it is empty."""

import pytest

from app.db.session import SessionLocal
from app.models import Port
from app.services.whatif import Levers, breakeven, sensitivity, urgent_desk, what_if


@pytest.fixture(scope="module")
def db():
    s = SessionLocal()
    if not s.query(Port).filter(Port.name == "Haldia").first():
        pytest.skip("database not seeded")
    yield s
    s.close()


def base(**kw):
    return Levers(origin="Australia", port="Haldia", cargo_tonnes=75000, **kw)


def test_zero_levers_change_nothing(db):
    r = what_if(db, base())
    assert r["delta_pct"] == 0 and r["delta_days"] == 0


def test_freight_shock_raises_cost(db):
    assert what_if(db, base(freight_shock_pct=30))["delta_pct"] > 0


def test_rupee_fall_costs_more_in_inr_not_days(db):
    r = what_if(db, base(inr_shock_pct=6))
    assert r["delta_pct"] == pytest.approx(6.0, abs=0.5)
    assert abs(r["delta_days"]) < 0.05


def test_reroute_adds_days_and_cost(db):
    r = what_if(db, base(reroute_nm=3500))
    assert r["delta_days"] > 5 and r["delta_pct"] > 30


def test_sensitivity_is_sorted_by_swing(db):
    rows = sensitivity(db, base())["rows"]
    swings = [x["swing"] for x in rows]
    assert swings == sorted(swings, reverse=True)


def test_breakeven_runs(db):
    assert breakeven(db, base(), Levers(origin="Mozambique", port="Haldia", cargo_tonnes=75000))


def test_urgent_relaxed_deadline_has_safe_option(db):
    r = urgent_desk(db, "Paradip", 60000, 20)
    assert r["feasible_count"] > 0
    assert r["best"]["p_on_time"] >= 0.8 and r["best"]["fits_berth"] and r["best"]["coking_grade"]
    assert r["best"]["origin"] != "Indonesia"


def test_urgent_impossible_deadline_recommends_nothing(db):
    r = urgent_desk(db, "Haldia", 60000, 12)
    assert r["feasible_count"] == 0 and not r["best"]
