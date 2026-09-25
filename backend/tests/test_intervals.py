"""Calibrated forecast bands."""

import numpy as np

from app.ml.intervals import calibrated_halfwidth


def test_wider_horizon_gives_wider_band():
    v = np.cumsum(np.random.default_rng(1).normal(0, 2, 200)) + 100
    assert calibrated_halfwidth(v, 6) > calibrated_halfwidth(v, 1) > 0


def test_higher_level_gives_wider_band():
    v = np.cumsum(np.random.default_rng(2).normal(0, 2, 200)) + 100
    assert calibrated_halfwidth(v, 3, 0.95) >= calibrated_halfwidth(v, 3, 0.80)


def test_band_covers_close_to_nominal_on_a_random_walk():
    rng = np.random.default_rng(3)
    v = np.cumsum(rng.normal(0, 2, 400)) + 200
    hits = [abs(v[o + 2] - v[o - 1]) <= calibrated_halfwidth(v[:o], 3, 0.95) for o in range(100, 395)]
    assert 0.88 <= np.mean(hits) <= 1.0


def test_too_little_history_returns_none():
    assert calibrated_halfwidth(np.arange(10.0), 3) is None


def test_market_factor_is_bounded_and_defaults_to_one():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.db.session import Base
    from app.models import FreightRate
    from app.services.recommendation import MARKET_FACTOR_BOUNDS, _MF_CACHE, market_factor
    from datetime import date

    _MF_CACHE.clear()
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[FreightRate.__table__])
    db = sessionmaker(bind=eng)()
    assert market_factor(db) == 1.0  # no data
    for i in range(80):  # flat 50, then a spike to 500
        db.add(FreightRate(rate_date=date(2015 + i // 12, i % 12 + 1, 1), index_name="OCEAN_GULF_JAPAN", value=50.0 if i < 79 else 500.0, unit="u", source="s"))
    db.commit()
    _MF_CACHE.clear()
    assert market_factor(db) == MARKET_FACTOR_BOUNDS[1]
    _MF_CACHE.clear()
