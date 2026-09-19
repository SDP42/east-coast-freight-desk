"""Always-on broker briefing (#20): four short paragraphs built from the same engines as the assistant."""

from sqlalchemy.orm import Session

from app.ml.intent import Entities
from app.services import assistant as a


def build(db: Session) -> dict:
    parts = []
    for title, fn, ent in (
        ("Market", a._market_now, Entities(index_name="BDI")),
        ("Outlook", a._forecast, Entities(index_name="BDI", horizon_days=14)),
        ("Ports", a._congestion, Entities()),
        ("Route risk", a._risk, Entities(origin="Australia", port="Haldia")),
    ):
        ans = fn(db, ent, [])
        parts.append({"title": title, "text": ans.text, "figures": [{"label": l, "value": v} for l, v in ans.figures[:4]]})
    return {"sections": parts, "note": "Generated from the live engines each time you open it; data ends where each series ends, which the text states."}
