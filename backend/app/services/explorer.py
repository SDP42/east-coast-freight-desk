"""Historical data explorer (baseline #9): list series, filter a series by date and value, search series and events."""

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import DisruptionEvent, FreightRate

META = {
    "BCI": ("Capesize index", "points"), "BPI": ("Panamax index", "points"), "BSI": ("Supramax index", "points"),
    "BHSI": ("Handysize index", "points"), "COAL_AUS": ("Australian coal", "usd/t"), "COAL_ZA": ("South African coal", "usd/t"), "SP500": ("S&P 500", "usd"),
    "DXY": ("US dollar index", "pts"), "INR": ("INR per USD", "inr"), "AUD": ("USD per AUD", "usd"), "ZAR": ("ZAR per USD", "zar"),
}


def list_series(db: Session) -> list[dict]:
    rows = db.query(FreightRate.index_name, func.min(FreightRate.rate_date), func.max(FreightRate.rate_date), func.count(FreightRate.id), func.min(FreightRate.source)).group_by(FreightRate.index_name).all()
    out = []
    for name, d0, d1, n, src in rows:
        label, unit = META.get(name, (name, ""))
        out.append({"index_name": name, "label": label, "unit": unit, "first": str(d0), "last": str(d1), "rows": n, "source": src})
    return sorted(out, key=lambda r: r["index_name"])


def query(db: Session, index_name: str, start: date | None, end: date | None, min_value: float | None, max_value: float | None, limit: int = 500) -> dict:
    q = db.query(FreightRate).filter(FreightRate.index_name == index_name)
    if start:
        q = q.filter(FreightRate.rate_date >= start)
    if end:
        q = q.filter(FreightRate.rate_date <= end)
    if min_value is not None:
        q = q.filter(FreightRate.value >= min_value)
    if max_value is not None:
        q = q.filter(FreightRate.value <= max_value)
    total, lo, hi, avg = q.with_entities(func.count(FreightRate.id), func.min(FreightRate.value), func.max(FreightRate.value), func.avg(FreightRate.value)).one()
    rows = q.order_by(FreightRate.rate_date.desc()).limit(limit).all()
    return {"index_name": index_name, "total_matches": total, "returned": len(rows),
            "summary": {"min": float(lo), "max": float(hi), "mean": float(avg)} if total else None,
            "rows": [{"date": str(r.rate_date), "value": float(r.value), "unit": r.unit} for r in rows]}


def search(db: Session, text: str) -> dict:
    t = text.lower().strip()
    series = [s for s in list_series(db) if t in s["index_name"].lower() or t in s["label"].lower() or t in (s["source"] or "").lower()]
    events = [{"title": e.title, "category": e.category, "region": e.region, "date": str(e.start_date)} for e in db.query(DisruptionEvent).all()
              if t in e.title.lower() or t in (e.description or "").lower() or t in e.region.lower() or t in e.category.lower()]
    return {"series": series, "events": events}
