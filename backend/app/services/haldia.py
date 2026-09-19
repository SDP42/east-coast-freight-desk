"""Observed facts about coal discharge at Haldia Dock Complex, from SMP Kolkata's public
daily morning-position reports (parsed by scripts/ingest_haldia_positions.py)."""

import statistics as st
from collections import Counter

from sqlalchemy.orm import Session

from app.models import HaldiaCoalCall

# Facts from the port trust and terminal operator publications (see SECTIONS.md 14c).
PORT_FACTS = {
    "berths": 14,
    "oil_jetties": 3,
    "lock_length_m": 330,
    "lock_width_m": 39,
    "sandheads_distance_km": 130,
    "sagar_pilotage_upstream_km": 45,
    "transit_hours_sandheads_to_jetty": 6,
    "coal_berth_4a_unloaders": 2,
    "coal_berth_4a_rate_t_per_day": 14000,
}


def summary(db: Session) -> dict:
    rows = db.query(HaldiaCoalCall).all()
    tonnage = [r.tonnage_t for r in rows if r.tonnage_t]
    draft = [float(r.expected_draft_m) for r in rows if r.expected_draft_m]
    loa = [float(r.loa_m) for r in rows if r.loa_m]
    dates = [r.first_report_date for r in rows]
    recent = sorted(rows, key=lambda r: r.first_report_date, reverse=True)[:12]
    return {
        "facts": PORT_FACTS,
        "observed": {
            "vessels": len(rows),
            "period_start": min(dates).isoformat() if dates else None,
            "period_end": max(dates).isoformat() if dates else None,
            "median_cargo_t": st.median(tonnage) if tonnage else None,
            "min_cargo_t": min(tonnage) if tonnage else None,
            "max_cargo_t": max(tonnage) if tonnage else None,
            "median_draft_m": st.median(draft) if draft else None,
            "min_draft_m": min(draft) if draft else None,
            "max_draft_m": max(draft) if draft else None,
            "median_loa_m": st.median(loa) if loa else None,
            "by_importer": dict(Counter(r.importer_group for r in rows)),
            "by_cargo": dict(Counter(r.cargo for r in rows)),
        },
        "recent_vessels": [
            {"name": r.vessel_name, "loa_m": float(r.loa_m) if r.loa_m else None, "draft_m": float(r.expected_draft_m) if r.expected_draft_m else None,
             "cargo": r.cargo, "tonnage_t": r.tonnage_t, "importer": r.importer_group, "date": r.first_report_date.isoformat()}
            for r in recent
        ],
    }
