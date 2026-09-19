"""Market pulse: what the current public data says today.

The Baltic freight indices in the database end in July 2019, and a test showed the current public deep-sea freight PPI
does not predict them (monthly-change correlation 0.00, out-of-sample R-squared below zero), so no nowcast of the Baltic
indices is offered. What IS current, free and dry-bulk relevant is shown instead: coal and iron-ore prices to mid-2026, the
rupee and dollar, and IMF PortWatch dry-bulk traffic at India's East Coast ports and the chokepoints, to last week.
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ChokepointTransit, FreightRate, PortActivity
from app.services.explorer import META

PULSE_SERIES = ["COAL_AUS", "IRON_ORE", "DEEPSEA_PPI", "INR", "AUD", "DXY"]


def _series(db: Session, name: str) -> pd.Series:
    rows = db.query(FreightRate.rate_date, FreightRate.value).filter(FreightRate.index_name == name).order_by(FreightRate.rate_date).all()
    return pd.Series([float(v) for _, v in rows], index=pd.to_datetime([d for d, _ in rows]))


def _change(s: pd.Series, days: int) -> float | None:
    if s.empty:
        return None
    target = s.index[-1] - pd.Timedelta(days=days)
    past = s[s.index <= target]
    return None if past.empty else round((s.iloc[-1] / past.iloc[-1] - 1) * 100, 2)


def market_pulse(db: Session) -> dict:
    cards = []
    for name in PULSE_SERIES:
        s = _series(db, name)
        if s.empty:
            continue
        pct = round(float((s <= s.iloc[-1]).mean()) * 100)
        c3, c12 = _change(s, 92), _change(s, 365)
        cards.append({
            "series": name, "label": META.get(name, (name, ""))[0], "unit": META.get(name, ("", ""))[1], "latest": round(float(s.iloc[-1]), 3),
            "as_of": s.index[-1].date().isoformat(), "change_3m_pct": None if c3 is None else float(c3), "change_12m_pct": None if c12 is None else float(c12),
            "percentile_since_start": pct, "history_from": s.index[0].date().isoformat(),
        })

    # East Coast dry-bulk port calls: last 28 days against the 28 days before and the same window a year ago.
    end = db.query(func.max(PortActivity.activity_date)).scalar()
    ports = []
    if end:
        def window(port: str, a: date, b: date) -> tuple[float, float]:
            rows = db.query(PortActivity.dry_bulk_calls, PortActivity.dry_bulk_import_t).filter(PortActivity.port_name == port, PortActivity.activity_date > a, PortActivity.activity_date <= b).all()
            return (float(np.mean([r[0] for r in rows])) if rows else 0.0, float(np.sum([r[1] for r in rows])) if rows else 0.0)
        for port in ["Paradip", "Visakhapatnam", "Haldia", "Dhamra", "Gopalpur"]:
            now_c, now_t = window(port, end - timedelta(days=28), end)
            prev_c, _ = window(port, end - timedelta(days=56), end - timedelta(days=28))
            yr_c, yr_t = window(port, end - timedelta(days=28 + 365), end - timedelta(days=365))
            ports.append({
                "port": port, "calls_per_day_28d": round(now_c, 2), "vs_previous_28d_pct": round((now_c / prev_c - 1) * 100, 1) if prev_c else None,
                "vs_year_ago_pct": round((now_c / yr_c - 1) * 100, 1) if yr_c else None, "dry_bulk_import_kt_28d": round(now_t / 1000, 1),
                "import_vs_year_ago_pct": round((now_t / yr_t - 1) * 100, 1) if yr_t else None,
            })

    # Chokepoints: last 28 days of dry-bulk capacity against the same window a year ago and the pre-Oct-2023 norm.
    chokes = []
    cend = db.query(func.max(ChokepointTransit.transit_date)).scalar()
    if cend:
        for name in ["Suez Canal", "Bab el-Mandeb Strait", "Cape of Good Hope", "Malacca Strait"]:
            rows = db.query(ChokepointTransit.transit_date, ChokepointTransit.dry_bulk_capacity_dwt).filter(ChokepointTransit.chokepoint == name).all()
            s = pd.Series([float(v) for _, v in rows], index=pd.to_datetime([d for d, _ in rows])).sort_index()
            if s.empty:
                continue
            last = s[s.index > pd.Timestamp(cend) - pd.Timedelta(days=28)].mean()
            yr = s[(s.index > pd.Timestamp(cend) - pd.Timedelta(days=28 + 365)) & (s.index <= pd.Timestamp(cend) - pd.Timedelta(days=365))].mean()
            base = s[(s.index >= "2022-01-01") & (s.index < "2023-10-01")].mean()
            chokes.append({
                "chokepoint": name, "dry_bulk_dwt_per_day_28d": round(float(last)), "vs_year_ago_pct": float(round((last / yr - 1) * 100, 1)) if yr else None,
                "vs_pre_oct_2023_pct": float(round((last / base - 1) * 100, 1)) if base else None,
            })

    notes = []
    for c in cards:
        if c["change_12m_pct"] is not None and abs(c["change_12m_pct"]) >= 10:
            notes.append(f"{c['label']} is {c['change_12m_pct']:+.1f}% over 12 months (to {c['as_of']}), at the {c['percentile_since_start']}th percentile since {c['history_from'][:4]}.")
    for k in chokes:
        if k["vs_pre_oct_2023_pct"] is not None and abs(k["vs_pre_oct_2023_pct"]) >= 20:
            notes.append(f"{k['chokepoint']} carries {k['vs_pre_oct_2023_pct']:+.0f}% dry-bulk capacity against the pre-October-2023 norm.")
    return {
        "cards": cards, "ports": ports, "chokepoints": chokes, "headlines": notes,
        "ports_as_of": end.isoformat() if end else None, "chokepoints_as_of": cend.isoformat() if cend else None,
        "note": "Baltic freight indices end July 2019. The public deep-sea freight PPI does not track them (tested), so no nowcast is shown; these are the current, free, dry-bulk-relevant signals.",
    }
