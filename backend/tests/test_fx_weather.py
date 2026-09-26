"""Live currency rate and port weather: parsing, fallbacks and the working-risk rule, with no network."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import FreightRate
from app.services import fx, weather


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


def test_working_risk_rule():
    assert weather.working_risk(20, 0.5) == "Low"
    assert weather.working_risk(45, 0.5) == "Moderate"
    assert weather.working_risk(20, 1.6) == "Moderate"
    assert weather.working_risk(60, 0.5) == "High"
    assert weather.working_risk(10, 2.6) == "High"
    assert weather.working_risk(None, None) == "Low"


def test_weather_build_combines_wind_rain_and_waves(monkeypatch):
    fc = [{"current": {"time": "2026-09-26T13:45", "temperature_2m": 30.4, "wind_speed_10m": 23.4, "wind_gusts_10m": 44.3, "weather_code": 63, "precipitation": 1.2},
           "daily": {"time": ["2026-09-26", "2026-09-27"], "wind_gusts_10m_max": [44.3, 60.0], "precipitation_sum": [5.0, 0.0], "weather_code": [63, 0]}}]
    mar = [{"daily": {"wave_height_max": [0.9, 0.5]}}]
    monkeypatch.setattr(weather, "fetch_weather", lambda c: fc)
    monkeypatch.setattr(weather, "fetch_marine", lambda c: mar)
    out = weather.build([("Haldia", 22.03, 88.07)])
    p = out["ports"][0]
    assert p["now"]["summary"] == "Rain" and p["now"]["working_risk"] == "Moderate"
    assert p["days"][1]["working_risk"] == "High" and p["worst_day"]["date"] == "2026-09-27"
    assert p["days"][0]["wave_max_m"] == 0.9


def test_weather_still_answers_when_the_marine_service_fails(monkeypatch):
    fc = [{"current": {"wind_gusts_10m": 10}, "daily": {"time": ["2026-09-26"], "wind_gusts_10m_max": [10], "precipitation_sum": [0], "weather_code": [0]}}]
    monkeypatch.setattr(weather, "fetch_weather", lambda c: fc)

    def down(c):
        raise OSError("marine down")

    monkeypatch.setattr(weather, "fetch_marine", down)
    p = weather.build([("Paradip", 20.26, 86.68)])["ports"][0]
    assert p["days"][0]["wave_max_m"] is None and p["now"]["working_risk"] == "Low"


def test_unavailable_answer_carries_coordinates_for_the_browser_fallback():
    r = weather._unavailable([("Haldia", 22.03, 88.07)], "down", "HTTPError: HTTP Error 429")
    assert r["available"] is False and r["coords"] == [{"port": "Haldia", "latitude": 22.03, "longitude": 88.07}]
    assert r["limits"] == weather.LIMITS and "429" in r["error"]
