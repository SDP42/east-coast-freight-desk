"""Always-on broker briefing (#20): short paragraphs built from the same engines as the assistant. Each paragraph is
included only if the user's role may see it, and port paragraphs use only the user's assigned ports."""

from sqlalchemy.orm import Session

from app.core.permissions import has, port_scope
from app.ml.intent import Entities
from app.services import assistant as a


def build(db: Session, user=None) -> dict:
    scope = port_scope(user) if user is not None else None
    first_port = scope[0] if scope else "Haldia"
    plan = [
        ("Market", "market:read", a._market_now, Entities(index_name="OCEAN_GULF_JAPAN")),
        ("Outlook", "market:read", a._forecast, Entities(index_name="OCEAN_GULF_JAPAN", horizon_days=90)),
        ("Ports", "ports:read", a._congestion, Entities(port=first_port) if scope else Entities()),
        ("Route risk", "risk:read", a._risk, Entities(origin="Australia", port=first_port)),
    ]
    parts = []
    for title, perm, fn, ent in plan:
        if user is not None and not has(user, perm):
            continue
        ans = fn(db, ent, [])
        parts.append({"title": title, "text": ans.text, "figures": [{"label": l, "value": v} for l, v in ans.figures[:4]]})
    return {"sections": parts, "scope": "your assigned ports only: " + ", ".join(scope) if scope is not None else "all data your role may see",
            "note": "Generated from the live engines each time you open it; data ends where each series ends, which the text states."}
