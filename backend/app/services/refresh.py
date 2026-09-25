"""Live refresh of the public market series.

Pulls the latest observations from the same free, public-domain sources the ingest scripts use (FRED serving US-government series,
and the USDA Grain Transportation Report) and appends only rows newer than what is stored. No account, key or payment is involved.
A failed source leaves its series untouched and is reported, so one outage never blocks the others.

'Live' here means as current as each publisher makes it: Brent and the exchange rates update daily on business days, the BLS indices
and the USDA ocean rate monthly. No free source publishes minute-level freight prices."""

import io
import logging
import re
import threading
import urllib.request
from datetime import date, datetime, timezone

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import FreightRate

log = logging.getLogger("app.refresh")
UA = {"User-Agent": "Mozilla/5.0 (freight-desk research prototype)"}
TIMEOUT = 30

# (series name, FRED id, unit, source text)
FRED_SERIES = [
    ("BRENT", "DCOILBRENTEU", "usd_per_barrel", "US EIA Brent crude spot price, via FRED"),
    ("DEEPSEA_PPI", "WPU30130101", "index_points", "US BLS PPI: deep-sea freight, via FRED"),
    ("COAL_PPI", "WPU051", "index_points", "US BLS PPI: coal, via FRED"),
    ("DXY", "DTWEXBGS", "index_points", "FRED (Federal Reserve Bank of St. Louis)"),
    ("INR", "DEXINUS", "inr_per_usd", "FRED (Federal Reserve Bank of St. Louis)"),
    ("AUD", "DEXUSAL", "usd_per_aud", "FRED (Federal Reserve Bank of St. Louis)"),
    ("ZAR", "DEXSFUS", "zar_per_usd", "FRED (Federal Reserve Bank of St. Louis)"),
]
USDA_URL = "https://www.ams.usda.gov/sites/default/files/media/GTRFigure20.xlsx"
USDA_SOURCE = "USDA AMS Grain Transportation Report, Figure 20 (rates by O'Neil Commodity Consulting)"
MONTHS = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}

_lock = threading.Lock()
_state: dict = {"running": False, "last_run": None, "last_ok": None, "results": []}


def _get(url: str) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=TIMEOUT).read()


def fetch_fred(fred_id: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(_get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={fred_id}").decode()))
    df.columns = ["date", "value"]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def _parse_month(cell) -> date | None:
    s = str(cell).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        t = pd.to_datetime(s[:10])
        return date(2019 if t.year == 1919 else t.year, t.month, 1)
    m = re.match(r"^(\d\d)-([A-Za-z]+)$", s)
    if m:
        yy, mon = int(m.group(1)), m.group(2)
    else:
        m = re.match(r"^([A-Za-z]+)\.?\s*'?(\d\d)$", s)
        if not m:
            return None
        mon, yy = m.group(1), int(m.group(2))
    month = MONTHS.get(mon.lower()[:3])
    return date(1900 + yy if yy >= 90 else 2000 + yy, month, 1) if month else None


def fetch_usda() -> dict[str, dict[date, float]]:
    df = pd.read_excel(io.BytesIO(_get(USDA_URL)), sheet_name="Data", header=None)
    out: dict[str, dict[date, float]] = {"OCEAN_GULF_JAPAN": {}, "OCEAN_PNW_JAPAN": {}}
    for r in df.iloc[6:].itertuples(index=False):
        d = _parse_month(r[0])
        if d is None:
            continue
        for name, col in (("OCEAN_GULF_JAPAN", 1), ("OCEAN_PNW_JAPAN", 3)):
            try:
                v = float(r[col])
            except (TypeError, ValueError):
                continue
            if v == v and v > 0:
                out[name][d] = v
    return out


def _append(db: Session, name: str, points: dict[date, float], unit: str, source: str) -> dict:
    latest = db.query(func.max(FreightRate.rate_date)).filter(FreightRate.index_name == name).scalar()
    new = [(d, v) for d, v in sorted(points.items()) if latest is None or d > latest]
    if new:
        db.bulk_save_objects([FreightRate(rate_date=d, index_name=name, value=float(v), unit=unit, source=source) for d, v in new])
        db.commit()
    now_latest = max(points) if points else latest
    return {"series": name, "status": "ok", "added": len(new), "latest": str(now_latest) if now_latest else None, "error": None}


def refresh_all(db: Session) -> dict:
    """Run every source once. Safe to call concurrently: a second caller gets the current state instead of starting another run."""
    if not _lock.acquire(blocking=False):
        return status()
    try:
        _state["running"] = True
        results = []
        for name, fred_id, unit, source in FRED_SERIES:
            try:
                df = fetch_fred(fred_id)
                results.append(_append(db, name, dict(zip(df["date"], df["value"])), unit, source))
            except Exception as e:  # noqa: BLE001
                db.rollback()
                log.warning("refresh %s failed: %s", name, e)
                results.append({"series": name, "status": "failed", "added": 0, "latest": None, "error": str(e)[:160]})
        try:
            for name, pts in fetch_usda().items():
                results.append(_append(db, name, pts, "usd_per_tonne", USDA_SOURCE))
        except Exception as e:  # noqa: BLE001
            db.rollback()
            log.warning("refresh USDA failed: %s", e)
            results.append({"series": "OCEAN_*", "status": "failed", "added": 0, "latest": None, "error": str(e)[:160]})
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        _state.update(last_run=now, results=results)
        if any(r["status"] == "ok" for r in results):
            _state["last_ok"] = now
        log.info("refresh finished: %d new rows, %d failed", sum(r["added"] for r in results), sum(r["status"] == "failed" for r in results))
        return status()
    finally:
        _state["running"] = False
        _lock.release()


def status() -> dict:
    res = _state["results"]
    return {**{k: _state[k] for k in ("running", "last_run", "last_ok")}, "results": res,
            "added_total": sum(r["added"] for r in res), "failed": sum(r["status"] == "failed" for r in res)}
