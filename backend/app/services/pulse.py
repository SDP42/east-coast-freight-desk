"""Market pulse: what the current public-domain data says today (US-government and Federal Reserve series only)."""

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models import FreightRate
from app.services.explorer import META

PULSE_SERIES = ["OCEAN_GULF_JAPAN", "OCEAN_PNW_JAPAN", "DEEPSEA_PPI", "COAL_PPI", "BRENT", "INR", "AUD", "DXY"]


def _series(db: Session, name: str) -> pd.Series:
    rows = db.query(FreightRate.rate_date, FreightRate.value).filter(FreightRate.index_name == name).order_by(FreightRate.rate_date).all()
    return pd.Series([float(v) for _, v in rows], index=pd.to_datetime([d for d, _ in rows]))


def _change(s: pd.Series, days: int) -> float | None:
    if s.empty:
        return None
    past = s[s.index <= s.index[-1] - pd.Timedelta(days=days)]
    return None if past.empty else float(round((s.iloc[-1] / past.iloc[-1] - 1) * 100, 2))


def market_pulse(db: Session) -> dict:
    cards = []
    for name in PULSE_SERIES:
        s = _series(db, name)
        if s.empty:
            continue
        pct = round(float((s <= s.iloc[-1]).mean()) * 100)
        cards.append({
            "series": name, "label": META.get(name, (name, ""))[0], "unit": META.get(name, ("", ""))[1], "latest": round(float(s.iloc[-1]), 3),
            "as_of": s.index[-1].date().isoformat(), "change_3m_pct": _change(s, 92), "change_12m_pct": _change(s, 365),
            "percentile_since_start": pct, "history_from": s.index[0].date().isoformat(),
        })
    notes = []
    for c in cards:
        if c["change_12m_pct"] is not None and abs(c["change_12m_pct"]) >= 10:
            notes.append(f"{c['label']} is {c['change_12m_pct']:+.1f}% over 12 months (to {c['as_of']}), at the {c['percentile_since_start']}th percentile since {c['history_from'][:4]}.")
    return {
        "cards": cards, "ports": [], "chokepoints": [], "headlines": notes,
        "note": "All series here are US-government or Federal Reserve data (public domain). Port-traffic and chokepoint feeds were removed because their licences carry conditions.",
    }
