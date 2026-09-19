"""Data health for the administrator: how fresh each series is, and why an old one is old."""

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AuditLog, ChokepointTransit, FreightRate, HaldiaCoalCall, LedgerEntry, PortActivity, User
from app.services.explorer import META

# Expected update rhythm in days, and a reason when a series has ended for good.
# Monthly series publish about two months late, and FRED's daily series lag by about a week.
RHYTHM = {"BCI": 1, "BPI": 1, "BSI": 1, "BHSI": 1, "COAL_AUS": 45, "COAL_ZA": 45, "IRON_ORE": 45, "DEEPSEA_PPI": 45,
          "SP500": 7, "DXY": 7, "INR": 7, "AUD": 7, "ZAR": 7}
ENDED = {
    "BCI": "Mendeley research dataset ends July 2019; the live Baltic feed is a paid licence.",
    "BPI": "Mendeley research dataset ends July 2019; the live Baltic feed is a paid licence.",
    "BSI": "Mendeley research dataset ends July 2019; the live Baltic feed is a paid licence.",
    "BHSI": "Mendeley research dataset ends July 2019; the live Baltic feed is a paid licence.",
}


def data_health(db: Session) -> dict:
    today = date.today()
    series = []
    for name, latest, first, n, source in (
        db.query(FreightRate.index_name, func.max(FreightRate.rate_date), func.min(FreightRate.rate_date), func.count(), func.max(FreightRate.source))
        .group_by(FreightRate.index_name).all()
    ):
        age = (today - latest).days
        rhythm = RHYTHM.get(name, 31)
        status = "fresh" if age <= rhythm * 2 + 5 else ("ended" if name in ENDED else "stale")
        series.append({
            "series": name, "label": META.get(name, (name, ""))[0], "first": first.isoformat(), "latest": latest.isoformat(),
            "age_days": age, "rows": n, "status": status, "source": source, "why": ENDED.get(name) if status != "fresh" else None,
        })
    order = {"stale": 0, "ended": 1, "fresh": 2}
    series.sort(key=lambda s: (order[s["status"]], s["series"]))

    def latest(model, col):
        d = db.query(func.max(col)).scalar()
        return d.isoformat() if d else None

    feeds = [
        {"feed": "IMF PortWatch port calls", "latest": latest(PortActivity, PortActivity.activity_date), "rows": db.query(PortActivity).count()},
        {"feed": "IMF PortWatch chokepoints", "latest": latest(ChokepointTransit, ChokepointTransit.transit_date), "rows": db.query(ChokepointTransit).count()},
        {"feed": "SMP Kolkata Haldia coal calls", "latest": latest(HaldiaCoalCall, HaldiaCoalCall.first_report_date), "rows": db.query(HaldiaCoalCall).count()},
    ]
    return {
        "as_of": today.isoformat(),
        "series": series, "feeds": feeds,
        "counts": {"users": db.query(User).count(), "ledger_entries": db.query(LedgerEntry).count(), "audit_events": db.query(AuditLog).count()},
        "summary": {"fresh": sum(s["status"] == "fresh" for s in series), "ended": sum(s["status"] == "ended" for s in series), "stale": sum(s["status"] == "stale" for s in series)},
    }
