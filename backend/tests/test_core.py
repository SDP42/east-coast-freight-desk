"""Fast unit tests that need no seeded database or network."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import login_guard
from app.db.session import Base
from app.ml.intent import classify, extract_entities, model_info
from app.schemas.user import UserCreate, check_password_policy
from app.services import ledger
from app.services.alerts import validate_webhook_url
from app.services.voyage import cii_reference


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, future=True)()
    yield session
    session.close()


def test_password_policy_rejects_weak_and_accepts_good():
    for bad in ("short1", "onlyletters", "12345678"):
        with pytest.raises(ValueError):
            check_password_policy(bad)
    assert check_password_policy("Harbor2026") == "Harbor2026"


def test_admin_role_cannot_be_self_registered():
    with pytest.raises(ValueError):
        UserCreate(email="a@b.co", password="Harbor2026", role="admin")


def test_login_guard_locks_after_five_failures_and_clears():
    keys = ("email:test-guard@example.com",)
    login_guard.clear(*keys)
    for _ in range(login_guard.MAX_FAILURES):
        assert login_guard.retry_after(*keys) == 0
        login_guard.record_failure(*keys)
    assert login_guard.retry_after(*keys) > 0
    login_guard.clear(*keys)
    assert login_guard.retry_after(*keys) == 0


def test_intent_routing_and_entities():
    assert classify("what will capesize do in the next 10 days")[0][0] == "forecast"
    assert classify("cheapest origin for 75,000 t to vizag")[0][0] == "recommend_origin"
    e = extract_entities("cheapest origin for 75,000 t to vizag")
    assert e.port == "Visakhapatnam" and e.cargo_tonnes == 75000
    assert extract_entities("forecast the ocean rate for 3 months").index_name == "OCEAN_GULF_JAPAN"


def test_intent_model_reports_honest_accuracy():
    info = model_info()
    assert 0.6 < info["cv_accuracy_mean"] <= 1.0
    assert "not an external benchmark" in info["note"]


def test_ledger_chain_detects_tampering(db):
    row = dict(fixture_date=date(2024, 1, 5), vessel_name="MV Test", origin_country="Australia", destination_port="Paradip",
               cargo_tonnes=70000, charter_type="spot", rate_usd_per_tonne=15.0, notes=None, is_sample=False)
    for i in range(3):
        ledger.add_entry(db, {**row, "vessel_name": f"MV Test {i}"}, user_id=None)
    assert ledger.verify_chain(db)["valid"] is True
    entry = db.query(ledger.LedgerEntry).filter_by(id=2).one()
    entry.rate_usd_per_tonne = 1.0
    db.commit()
    result = ledger.verify_chain(db)
    assert result["valid"] is False and result["first_broken_id"] == 2


def test_ledger_detects_deleted_entry(db):
    row = dict(fixture_date=date(2024, 1, 5), vessel_name="MV Test", origin_country="Australia", destination_port="Paradip",
               cargo_tonnes=70000, charter_type="spot", rate_usd_per_tonne=15.0, notes=None, is_sample=False)
    for i in range(3):
        ledger.add_entry(db, {**row, "vessel_name": f"MV Test {i}"}, user_id=None)
    db.query(ledger.LedgerEntry).filter_by(id=2).delete()
    db.commit()
    assert ledger.verify_chain(db)["valid"] is False


def test_cii_reference_line_and_capacity_cap():
    assert cii_reference(80_000) == pytest.approx(4745 * 80_000 ** -0.622)
    assert cii_reference(400_000) == cii_reference(279_000)


@pytest.mark.parametrize("url", ["http://example.com/x", "https://127.0.0.1/x", "https://localhost/x", "https://10.0.0.5/x"])
def test_webhook_guard_blocks_unsafe_targets(url):
    with pytest.raises(ValueError):
        validate_webhook_url(url)


def test_role_permissions_and_port_scope():
    from types import SimpleNamespace

    from app.core.permissions import can_see_port, has, port_scope

    finance = SimpleNamespace(role="finance_head", assigned_ports=None)
    analyst = SimpleNamespace(role="chartering_analyst", assigned_ports=None)
    officer = SimpleNamespace(role="port_ops", assigned_ports='["Haldia"]')
    unassigned = SimpleNamespace(role="port_ops", assigned_ports=None)
    viewer = SimpleNamespace(role="viewer", assigned_ports=None)
    assert has(finance, "treasury:read") and not has(analyst, "treasury:read")
    assert has(analyst, "ledger:read_own") and not has(analyst, "ledger:read_all")
    assert not has(officer, "market:read") and has(officer, "ports:read")
    assert port_scope(finance) is None and port_scope(officer) == ["Haldia"] and port_scope(unassigned) == []
    assert can_see_port(officer, "Haldia") and not can_see_port(officer, "Paradip") and not can_see_port(unassigned, "Haldia")
    assert has(viewer, "market:read") and not has(viewer, "ports:read")


def test_unknown_role_falls_back_to_viewer():
    from types import SimpleNamespace

    from app.core.permissions import has

    ghost = SimpleNamespace(role="superuser", assigned_ports=None)
    assert has(ghost, "market:read") and not has(ghost, "admin:users")


def test_intent_recognises_permission_sensitive_questions():
    assert classify("show my fixtures")[0][0] == "ledger"
    assert classify("what can I access?")[0][0] == "my_access"
    assert classify("how many users have accounts?")[0][0] == "users_admin"
