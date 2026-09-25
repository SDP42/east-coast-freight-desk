"""Live refresh: appends only newer rows, isolates failures, and never runs twice at once."""

from datetime import date

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import FreightRate
from app.services import refresh


@pytest.fixture()
def db():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng, tables=[FreightRate.__table__])
    s = sessionmaker(bind=eng)()
    yield s
    s.close()


def test_only_newer_rows_are_added(db):
    db.add(FreightRate(rate_date=date(2026, 1, 1), index_name="X", value=1.0, unit="u", source="s"))
    db.commit()
    r = refresh._append(db, "X", {date(2026, 1, 1): 1.0, date(2026, 1, 2): 2.0, date(2026, 1, 3): 3.0}, "u", "s")
    assert r["added"] == 2 and r["latest"] == "2026-01-03"
    assert refresh._append(db, "X", {date(2026, 1, 3): 3.0}, "u", "s")["added"] == 0


def test_one_failed_source_does_not_stop_the_rest(db, monkeypatch):
    def fred(fid):
        if fid == "DCOILBRENTEU":
            raise OSError("network down")
        return pd.DataFrame({"date": [date(2026, 2, 1)], "value": [10.0]})

    monkeypatch.setattr(refresh, "fetch_fred", fred)
    monkeypatch.setattr(refresh, "fetch_usda", lambda: {"OCEAN_GULF_JAPAN": {date(2026, 2, 1): 70.0}})
    out = refresh.refresh_all(db)
    by = {r["series"]: r for r in out["results"]}
    assert by["BRENT"]["status"] == "failed" and "network down" in by["BRENT"]["error"]
    assert by["INR"]["status"] == "ok" and by["INR"]["added"] == 1
    assert by["OCEAN_GULF_JAPAN"]["added"] == 1
    assert out["failed"] == 1 and out["last_ok"]


def test_usda_month_labels_parse():
    assert refresh._parse_month("Aug '26") == date(2026, 8, 1)
    assert refresh._parse_month("26-Aug") == date(2026, 8, 1)
    assert refresh._parse_month("nonsense") is None
