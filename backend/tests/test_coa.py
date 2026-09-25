"""COA versus spot: fixtures must be spaced in real time, not in series steps."""

import pytest

from app.db.session import SessionLocal
from app.models import Port
from app.services.financial import simulate_coa_vs_spot


@pytest.fixture(scope="module")
def db():
    s = SessionLocal()
    if not s.query(Port).first():
        pytest.skip("database not seeded")
    yield s
    s.close()


def test_six_thirty_day_fixtures_span_about_six_months(db):
    r = simulate_coa_vs_spot(db, "OCEAN_GULF_JAPAN", 15.0, 75000, 6, 30)
    first, last = r.fixtures[0].date, r.fixtures[-1].date
    assert (last - first).days <= 200  # was about 15 years when 30 days was counted as 30 monthly steps
    assert r.spot_cost_std_usd < 0.05 * r.total_coa_cost_usd  # monthly volatility over six months, not decades


def test_coa_cost_is_rate_times_tonnes_times_fixtures(db):
    r = simulate_coa_vs_spot(db, "OCEAN_GULF_JAPAN", 15.0, 75000, 6, 30)
    assert r.total_coa_cost_usd == 15.0 * 75000 * 6
