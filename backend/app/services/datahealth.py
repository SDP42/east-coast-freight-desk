"""Data health for the administrator: how fresh each series is, and why an old one is old."""

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AuditLog, CycloneExposure, FreightRate, LedgerEntry, OpenTonnage, User
from app.services.explorer import META

# Expected update rhythm in days. Monthly US-government series publish a few weeks late; FRED's daily series lag by about a week.
RHYTHM = {"OCEAN_GULF_JAPAN": 60, "OCEAN_PNW_JAPAN": 60, "DEEPSEA_PPI": 60, "COAL_PPI": 60, "BRENT": 7, "DXY": 7, "INR": 7, "AUD": 7, "ZAR": 7}
ENDED: dict[str, str] = {}


def data_health(db: Session) -> dict:
    today = date.today()
    series = []
    for name, latest, first, n, source in (
        db.query(FreightRate.index_name, func.max(FreightRate.rate_date), func.min(FreightRate.rate_date), func.count(), func.max(FreightRate.source))
        .group_by(FreightRate.index_name).all()
    ):
        age = (today - latest).days
        rhythm = RHYTHM.get(name, 60)
        status = "fresh" if age <= rhythm * 2 + 5 else ("ended" if name in ENDED else "stale")
        series.append({
            "series": name, "label": META.get(name, (name, ""))[0], "first": first.isoformat(), "latest": latest.isoformat(),
            "age_days": age, "rows": n, "status": status, "source": source, "why": ENDED.get(name) if status != "fresh" else None,
        })
    order = {"stale": 0, "ended": 1, "fresh": 2}
    series.sort(key=lambda s: (order[s["status"]], s["series"]))
    tonnage_latest = db.query(func.max(OpenTonnage.uploaded_at)).scalar()
    feeds = [
        {"feed": "NOAA IBTrACS cyclone exposure (by port and month)", "latest": None, "rows": db.query(CycloneExposure).count()},
        {"feed": "Open tonnage lists uploaded by users", "latest": tonnage_latest.date().isoformat() if tonnage_latest else None, "rows": db.query(OpenTonnage).count()},
    ]
    return {
        "as_of": today.isoformat(), "series": series, "feeds": feeds,
        "counts": {"users": db.query(User).count(), "ledger_entries": db.query(LedgerEntry).count(), "audit_events": db.query(AuditLog).count()},
        "summary": {"fresh": sum(s["status"] == "fresh" for s in series), "ended": sum(s["status"] == "ended" for s in series), "stale": sum(s["status"] == "stale" for s in series)},
        "policy": "Only public-domain data is used (US government and Federal Reserve series, NOAA, Natural Earth). No licensed or attribution-conditioned data is stored.",
    }
