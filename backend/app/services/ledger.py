"""Hash-chained fixture ledger (#18) with market-timing benchmarking (#10).

Each entry's hash covers its own fields and the previous entry's hash, so editing or deleting an old
entry invalidates every later one. Benchmarking compares each fixture's date to the freight market
around it (real BDI) and its rate to the illustrative rate for that route."""

import hashlib
import json
from datetime import date, datetime, timedelta

import numpy as np
from sqlalchemy.orm import Session

from app.models import LedgerEntry, Port, Route, VesselClass
from app.services.freight_data import load_series
from app.services.recommendation import BASE_RATE_USD_PER_TONNE_PER_1000NM, VESSEL_CLASS_COST_MULTIPLIER, pick_vessel_class

GENESIS = "0" * 64
FIELDS = ("fixture_date", "vessel_name", "origin_country", "destination_port", "cargo_tonnes", "charter_type", "rate_usd_per_tonne", "notes", "is_sample")


def _canonical(e: LedgerEntry | dict, prev_hash: str, created_by: int | None, created_at: str) -> str:
    get = (lambda k: getattr(e, k)) if not isinstance(e, dict) else (lambda k: e[k])
    body = {
        "fixture_date": str(get("fixture_date")), "vessel_name": get("vessel_name"), "origin_country": get("origin_country"),
        "destination_port": get("destination_port"), "cargo_tonnes": round(float(get("cargo_tonnes")), 2), "charter_type": get("charter_type"),
        "rate_usd_per_tonne": None if get("rate_usd_per_tonne") is None else round(float(get("rate_usd_per_tonne")), 3),
        "notes": get("notes") or "", "is_sample": bool(get("is_sample")), "created_by": created_by, "created_at": created_at, "prev": prev_hash,
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":"))


def _hash(payload: str) -> str:
    return hashlib.sha256(payload.encode()).hexdigest()


def last_hash(db: Session) -> str:
    last = db.query(LedgerEntry).order_by(LedgerEntry.id.desc()).first()
    return last.entry_hash if last else GENESIS


def add_entry(db: Session, data: dict, user_id: int | None) -> LedgerEntry:
    prev = last_hash(db)
    now = datetime.utcnow().replace(microsecond=0)
    entry = LedgerEntry(created_by=user_id, created_at=now, prev_hash=prev, entry_hash="", **data)
    entry.entry_hash = _hash(_canonical(entry, prev, user_id, now.isoformat()))
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def verify_chain(db: Session) -> dict:
    prev = GENESIS
    rows = db.query(LedgerEntry).order_by(LedgerEntry.id).all()
    for r in rows:
        expected = _hash(_canonical(r, prev, r.created_by, r.created_at.replace(microsecond=0).isoformat()))
        if r.prev_hash != prev or r.entry_hash != expected:
            return {"valid": False, "entries": len(rows), "first_broken_id": r.id,
                    "reason": "previous-hash link is wrong" if r.prev_hash != prev else "entry contents do not match its hash"}
        prev = r.entry_hash
    return {"valid": True, "entries": len(rows), "head_hash": prev, "first_broken_id": None, "reason": None}


def benchmark(db: Session) -> list[dict]:
    bdi = load_series(db, "BDI")
    classes = db.query(VesselClass).order_by(VesselClass.dwt_min).all()
    out = []
    for r in db.query(LedgerEntry).order_by(LedgerEntry.fixture_date).all():
        d = np.datetime64(r.fixture_date)
        row: dict = {"id": r.id, "date": str(r.fixture_date), "vessel": r.vessel_name, "route": f"{r.origin_country} to {r.destination_port}",
                     "cargo_tonnes": float(r.cargo_tonnes), "rate": float(r.rate_usd_per_tonne) if r.rate_usd_per_tonne is not None else None, "is_sample": r.is_sample}
        window = bdi[(bdi.index >= str(r.fixture_date - timedelta(days=30))) & (bdi.index <= str(r.fixture_date + timedelta(days=30)))]
        trailing = bdi[(bdi.index >= str(r.fixture_date - timedelta(days=90))) & (bdi.index <= str(r.fixture_date))]
        if len(window) < 30 or trailing.empty or bdi.index[0] > np.datetime64(r.fixture_date) or bdi.index[-1] < d:
            row.update({"timing": None, "note": "BDI history does not cover this date"})
        else:
            at = float(bdi[bdi.index <= str(r.fixture_date)].iloc[-1])
            best = float(window.min())
            row["timing"] = {
                "bdi_at_fixture": round(at, 0), "percentile_in_trailing_90d": round(float((trailing < at).mean() * 100), 0),
                "best_bdi_within_30d": round(best, 0), "best_day": str(window.idxmin().date()),
                "missed_saving_pct": round(max(0.0, (at - best) / at * 100), 1),
                "forward_30d_change_pct": round(float((bdi[bdi.index >= str(r.fixture_date)].iloc[min(30, len(bdi[bdi.index >= str(r.fixture_date)]) - 1)] / at - 1) * 100), 1),
            }
        port = db.query(Port).filter(Port.name == r.destination_port).first()
        route = (db.query(Route).join(Port, Route.origin_port_id == Port.id).filter(Port.country == r.origin_country, Route.destination_port_id == port.id).first()) if port else None
        if route and route.distance_nm and classes:
            vc = pick_vessel_class(classes, float(r.cargo_tonnes))
            ref = BASE_RATE_USD_PER_TONNE_PER_1000NM * float(route.distance_nm) / 1000 * VESSEL_CLASS_COST_MULTIPLIER.get(vc.name, 1.0)
            row["illustrative_rate"] = round(ref, 2)
            if row["rate"] is not None:
                row["rate_vs_illustrative_pct"] = round((row["rate"] / ref - 1) * 100, 1)
        out.append(row)
    return out


SAMPLE = [
    (date(2023, 3, 6), "MV Sample Harmony", "Australia", "Paradip", 75000, "spot", 14.2),
    (date(2023, 10, 9), "MV Sample Dawn", "Australia", "Haldia", 33000, "spot", 17.8),
    (date(2021, 9, 20), "MV Sample Meridian", "Mozambique", "Visakhapatnam", 70000, "spot", 22.5),
    (date(2022, 6, 14), "MV Sample Tern", "Russia", "Paradip", 65000, "spot", 41.0),
    (date(2024, 2, 12), "MV Sample Crest", "United States", "Gangavaram", 80000, "coa", 36.5),
    (date(2020, 4, 6), "MV Sample Lantern", "Indonesia", "Dhamra", 55000, "spot", 6.9),
]


def load_sample(db: Session, user_id: int | None) -> int:
    n = 0
    for d, vessel, origin, port, cargo, ctype, rate in SAMPLE:
        add_entry(db, dict(fixture_date=d, vessel_name=vessel, origin_country=origin, destination_port=port, cargo_tonnes=cargo, charter_type=ctype,
                           rate_usd_per_tonne=rate, notes="Illustrative sample entry, not a real fixture", is_sample=True), user_id)
        n += 1
    return n
