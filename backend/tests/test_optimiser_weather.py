"""Optimiser, weather window and embedding-routing tests (offline: weather and embeddings are mocked or skipped)."""

import pytest

from app.db.session import SessionLocal
from app.models import Port
from app.services import optimiser, verdict_eval, weather


@pytest.fixture(scope="module")
def db():
    s = SessionLocal()
    if not s.query(Port).filter(Port.name == "Paradip").first():
        pytest.skip("database not seeded")
    yield s
    s.close()


def test_optimiser_meets_demand_and_respects_limits(db):
    r = optimiser.optimise(db)
    assert r["feasible"]
    shipped = sum(a["kt"] for a in r["allocation"])
    assert shipped == pytest.approx(r["total_demand_kt"], abs=1.0)
    for port, kt in r["by_port_kt"].items():
        assert kt <= optimiser.DEFAULT_PORT_CAP_KT[port] + 0.6
    for origin, kt in r["by_origin_kt"].items():
        assert kt <= optimiser.DEFAULT_MAX_SHARE[origin] * r["total_demand_kt"] + 0.6


def test_optimum_is_never_dearer_than_the_fixed_mix(db):
    r = optimiser.optimise(db)
    assert r["saving_inr_crore_per_month"] >= -1e-6


def test_impossible_limits_are_reported_not_hidden(db):
    r = optimiser.optimise(db, port_cap_kt={p: 50 for p in optimiser.DEFAULT_PORT_CAP_KT})
    assert r["feasible"] is False and "cannot be met" in r["message"]


def test_shadow_prices_are_positive_for_binding_limits(db):
    r = optimiser.optimise(db)
    assert r["binding_limits"] and all(b["saving_inr_lakh_per_extra_kt_per_month"] > 0 for b in r["binding_limits"])


def test_weather_window_classifies_days(db, monkeypatch):
    weather._cache.clear()
    calls = iter([
        {"daily": {"time": ["2026-09-19", "2026-09-20", "2026-09-21"], "wave_height_max": [1.0, 2.0, 3.0], "wave_period_max": [10, 9, 8]}},
        {"daily": {"time": ["2026-09-19", "2026-09-20", "2026-09-21"], "wind_gusts_10m_max": [10, 26, 20], "wind_speed_10m_max": [8, 15, 12], "precipitation_sum": [0, 0, 120]}},
    ])
    monkeypatch.setattr(weather, "_get", lambda url: next(calls))
    w = weather.window(db, "Paradip")
    assert [d["status"] for d in w["days"]] == ["green", "amber", "red"] and w["red_days"] == ["2026-09-21"]
    assert w["days"][2]["why"] and w["lost_working_days"] > 0.9


def test_verdict_evidence_reports_both_series(db):
    ev = verdict_eval.evidence(db)
    assert {t["series"] for t in ev["tests"]} == {"USDA grain ocean rate", "Baltic Panamax index"}


def test_intent_routing_works_with_and_without_embeddings(monkeypatch):
    from app.ml import intent
    assert intent.classify("should we rent a ship now or wait for paradip")[0][0] in {"verdict", "urgent"}
    intent._embed_model.cache_clear()
    monkeypatch.setattr(intent, "_embed_model", lambda: None)  # force the TF-IDF fallback
    assert intent.classify("cheapest origin for paradip")[0][0] == "recommend_origin"
