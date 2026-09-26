"""Live USD to INR rate: parsing, fallbacks and the converter, with no network."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import FreightRate
from app.services import fx


@pytest.fixture()
def db():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[FreightRate.__table__])
    s = sessionmaker(bind=eng)()
    s.add(FreightRate(rate_date=date(2026, 9, 11), index_name="INR", value=95.55, unit="inr_per_usd", source="FRED"))
    s.commit()
    yield s
    s.close()


def test_live_rate_is_used_and_compared_with_the_model_rate(db, monkeypatch):
    monkeypatch.setattr(fx, "fetch_latest", lambda: (95.82, "2026-09-25"))
    monkeypatch.setattr(fx, "fetch_history", lambda days=30: [{"date": "2026-09-24", "inr_per_usd": 95.7}])
    r = fx._build(db)
    assert r["live"] is True and r["rate"] == 95.82 and r["rate_date"] == "2026-09-25"
    assert r["model_rate"]["rate"] == 95.55 and r["difference_vs_model_pct"] == 0.28
    assert len(r["history"]) == 1


def test_falls_back_to_the_stored_rate_and_says_so(db, monkeypatch):
    def down():
        raise OSError("no network")

    monkeypatch.setattr(fx, "fetch_latest", down)
    r = fx._build(db)
    assert r["live"] is False and r["rate"] == 95.55 and r["rate_date"] == "2026-09-11" and "stored" in r["note"]


def test_missing_history_does_not_hide_the_live_rate(db, monkeypatch):
    monkeypatch.setattr(fx, "fetch_latest", lambda: (96.0, "2026-09-25"))

    def down(days=30):
        raise OSError("timeout")

    monkeypatch.setattr(fx, "fetch_history", down)
    r = fx._build(db)
    assert r["live"] is True and r["history"] == []


def test_convert_both_ways_and_rejects_bad_input():
    assert fx.convert(1000, "usd", 95.82)["result"] == 95820.0
    assert fx.convert(95820, "INR", 95.82)["result"] == 1000.0
    with pytest.raises(ValueError):
        fx.convert(1, "EUR", 95)
    with pytest.raises(ValueError):
        fx.convert(1, "USD", 0)
