"""Open tonnage: which ships are actually available, from the lists brokers send.

No free, licence-clean source of named ships exists, so availability comes from data SAIL already receives: brokers' open
position lists (ship name, size, where and when it is open). Users upload them here (CSV or Excel); the desk matches ships to a
cargo by size, berth fit, laycan and ETA. Nothing is scraped and nothing is shared beyond the organisation.
"""

import io
import re
from datetime import date, datetime, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from app.models import OpenTonnage, Port, Route, VesselClass
from app.services.compatibility import check_compatibility, part_laden_fraction

DEFAULT_SPEED_KN = 12.0
STALE_AFTER_DAYS = 7  # broker lists go out of date fast
PORT_ORIGIN = [  # keyword -> origin country used by the route table
    (r"hay point|dalrymple|abbot point|gladstone|newcastle|queensland|brisbane|australia", "Australia"),
    (r"hampton|norfolk|baltimore|mobile|new orleans|houston|us gulf|united states|usa", "United States"),
    (r"nacala|beira|maputo|richards bay|mozambique|south africa", "Mozambique"),
    (r"vostochny|nakhodka|ust-luga|vanino|russia", "Russia"),
    (r"balikpapan|samarinda|kalimantan|indonesia", "Indonesia"),
]
ALIASES = {
    "vessel_name": ["vessel_name", "vessel", "name", "ship", "ship name", "vessel name"],
    "imo": ["imo", "imo no", "imo number"],
    "dwt": ["dwt", "deadweight", "dw", "dwt (t)", "dwt tonnes"],
    "loa_m": ["loa_m", "loa", "length", "loa (m)"],
    "beam_m": ["beam_m", "beam", "breadth", "beam (m)"],
    "draft_m": ["draft_m", "draft", "draught", "summer draft", "draft (m)"],
    "open_port": ["open_port", "open", "open port", "position", "open at", "port", "location"],
    "open_date": ["open_date", "open date", "date", "eta open", "open on", "available", "open from"],
    "speed_knots": ["speed_knots", "speed", "speed (kn)", "knots"],
    "broker": ["broker", "source", "from"],
    "notes": ["notes", "remarks", "comment", "comments"],
}


def origin_of(open_port: str) -> str | None:
    t = (open_port or "").lower()
    for pat, country in PORT_ORIGIN:
        if re.search(pat, t):
            return country
    return None


def _norm(c: str) -> str:
    return re.sub(r"\s+", " ", str(c).strip().lower())


def parse_upload(content: bytes, filename: str) -> tuple[list[dict], list[dict]]:
    """Read a CSV or Excel broker list. Returns (valid rows, errors). Column names are matched loosely."""
    name = (filename or "").lower()
    df = pd.read_excel(io.BytesIO(content)) if name.endswith((".xlsx", ".xls")) else pd.read_csv(io.BytesIO(content))
    lookup = {_norm(c): c for c in df.columns}
    col = {field: next((lookup[a] for a in names if a in lookup), None) for field, names in ALIASES.items()}
    missing = [f for f in ("vessel_name", "dwt", "open_port", "open_date") if col[f] is None]
    if missing:
        raise ValueError(f"The file needs columns for: {', '.join(missing)} (found: {', '.join(map(str, df.columns))}).")
    rows, errors = [], []
    for i, r in df.iterrows():
        line = i + 2  # header is line 1
        try:
            dwt = int(float(r[col["dwt"]]))
            d = pd.to_datetime(r[col["open_date"]], dayfirst=True).date()
            vessel = str(r[col["vessel_name"]]).strip()
            port = str(r[col["open_port"]]).strip()
            if not vessel or vessel.lower() == "nan" or not port or port.lower() == "nan":
                raise ValueError("vessel name and open port are required")
            if not 8_000 <= dwt <= 400_000:
                raise ValueError(f"deadweight {dwt:,} t is outside 8,000 to 400,000")
            row = {"vessel_name": vessel, "dwt": dwt, "open_port": port, "open_date": d}
            for f in ("imo", "broker", "notes"):
                v = r[col[f]] if col[f] else None
                row[f] = None if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()
            for f in ("loa_m", "beam_m", "draft_m", "speed_knots"):
                v = r[col[f]] if col[f] else None
                row[f] = None if v is None or pd.isna(v) else float(v)
            rows.append(row)
        except Exception as e:  # noqa: BLE001 - report the row, keep the rest
            errors.append({"line": line, "error": str(e)})
    return rows, errors


def add_rows(db: Session, rows: list[dict], owner_id: int | None, is_sample: bool = False) -> int:
    for r in rows:
        db.add(OpenTonnage(owner_id=owner_id, is_sample=is_sample, **r))
    db.commit()
    return len(rows)


def sample_rows(today: date | None = None) -> list[dict]:
    """A clearly labelled illustrative list (invented ships) so the module can be demonstrated without real broker data."""
    t = today or date.today()
    spec = [
        ("MV Sample Aurora", 82000, "Hay Point", 3, 229.0, 32.3, 14.2, 13.0), ("MV Sample Meridian", 76000, "Hay Point", 6, 225.0, 32.2, 13.9, 12.5),
        ("MV Sample Kestrel", 180000, "Hay Point", 5, 292.0, 45.0, 18.1, 12.5), ("MV Sample Harbour", 58000, "Newcastle", 4, 190.0, 32.2, 12.8, 12.0),
        ("MV Sample Tern", 81000, "Nacala", 9, 229.0, 32.3, 14.3, 12.0), ("MV Sample Orion", 74000, "Richards Bay", 12, 225.0, 32.2, 13.8, 12.0),
        ("MV Sample Delta", 79000, "Hampton Roads", 15, 229.0, 32.3, 14.0, 12.5), ("MV Sample Coral", 63000, "Vostochny", 8, 199.9, 32.2, 13.0, 12.0),
        ("MV Sample Baltic", 38000, "Balikpapan", 5, 180.0, 28.0, 10.5, 11.5), ("MV Sample Vega", 92000, "Hay Point", 2, 235.0, 38.0, 14.9, 13.0),
    ]
    return [{"vessel_name": n, "imo": None, "dwt": dwt, "loa_m": loa, "beam_m": bm, "draft_m": dr, "open_port": port, "open_date": t + timedelta(days=days),
             "speed_knots": kn, "broker": "Illustrative sample (invented ships)", "notes": "Sample data, not real ships"} for n, dwt, port, days, loa, bm, dr, kn in spec]


MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_NAME = re.compile(r"\b(?:M\.?/?V\.?|MV)\s+([A-Za-z][A-Za-z0-9'\-]*(?:\s+[A-Za-z0-9'\-]+){0,3}?)(?=\s*[,;:\-\u2013(]|\s+\d|\s+(?:dwt|built|open|opening|ppt|prompt|spot|abt|about)\b|$)", re.I)
_DWT = re.compile(r"(\d{2,3})\s*k\s*(?:dwt|mt|t)?\b|(\d{2,3}[,.]?\d{3})\s*(?:mt\b|mts\b|dwt|t\b)?", re.I)


def _parse_date(t: str, today: date) -> date | None:
    m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?[\s\-/]*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", t, re.I)
    if m:
        d, mo = int(m.group(1)), MONTHS[m.group(2).lower()]
    else:
        m = re.search(r"\b(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2,4}))?\b", t)
        if not m:
            return None
        d, mo = int(m.group(1)), int(m.group(2))
        if mo > 12 and d <= 12:
            d, mo = mo, d
    try:
        cand = date(today.year, mo, d)
    except ValueError:
        return None
    return cand if cand >= today - timedelta(days=30) else date(today.year + 1, mo, d)


def parse_text(text: str, today: date | None = None) -> tuple[list[dict], list[str]]:
    """Read broker position text (one ship per line, as in a typical email) into rows for the user to check.

    Recognises 'MV NAME', deadweight ('82,000 dwt', '82k dwt'), an open port from the known loading ports, an open date
    ('22/09', '22 Sep', 'prompt', 'spot'), and optional draft ('14.2 m draft') and LOA. Returns (rows, lines it could not read).
    Every row is only a suggestion: the user confirms before anything is saved.
    """
    today = today or date.today()
    rows, skipped = [], []
    for raw in text.splitlines():
        line = raw.strip(" \t-*\u2022")
        if len(line) < 8:
            continue
        nm = _NAME.search(line)
        name = nm.group(1).strip().title() if nm else ("TBN" if re.search(r"\btbn\b", line, re.I) else None)
        dwt = None
        for m in _DWT.finditer(line):
            v = int(m.group(1)) * 1000 if m.group(1) else int(re.sub(r"[,.]", "", m.group(2)))
            if 8_000 <= v <= 400_000 and not (1990 <= v <= 2030):
                dwt = v
                break
        port = next((m.group(0) for pat, _c in PORT_ORIGIN for m in [re.search(pat, line, re.I)] if m), None)
        d = _parse_date(line, today)
        if d is None:
            if re.search(r"\b(ppt|prompt)\b", line, re.I):
                d = today + timedelta(days=2)
            elif re.search(r"\bspot\b", line, re.I):
                d = today + timedelta(days=1)
        if not (dwt and port and d):
            skipped.append(raw.strip())
            continue
        dm = re.search(r"(\d{1,2}[.,]\d{1,2})\s*m\s*(?:draft|draught|sdwt)", line, re.I) or re.search(r"(?:draft|draught)\s*(\d{1,2}[.,]\d{1,2})", line, re.I)
        lm = re.search(r"\bloa\s*(\d{3}(?:[.,]\d)?)", line, re.I)
        rows.append({"vessel_name": name or "Unnamed", "dwt": dwt, "open_port": port.title(), "open_date": d, "imo": None,
                     "draft_m": float(dm.group(1).replace(",", ".")) if dm else None, "loa_m": float(lm.group(1).replace(",", ".")) if lm else None, "beam_m": None,
                     "speed_knots": None, "broker": "Pasted text", "notes": line[:200], "needs_review": name is None})
    return rows, skipped


def _class_of(classes: list[VesselClass], dwt: int) -> VesselClass | None:
    for c in classes:
        if float(c.dwt_min) <= dwt <= float(c.dwt_max):
            return c
    return None


def _route(db: Session, origin: str, port: Port) -> Route | None:
    return (db.query(Route).join(Port, Route.origin_port_id == Port.id).filter(Port.country == origin, Route.destination_port_id == port.id).first())


def match(db: Session, port_name: str, cargo_tonnes: float, need_by_days: float, today: date | None = None, open_from_days: float = 0.0) -> dict:
    """Rank the open ships that could carry this cargo to this port by the date needed."""
    today = today or date.today()
    port = db.query(Port).filter(Port.name == port_name, Port.is_destination.is_(True)).first()
    if port is None:
        raise ValueError(f"Unknown port {port_name}")
    classes = db.query(VesselClass).order_by(VesselClass.dwt_min).all()
    ships = db.query(OpenTonnage).all()
    latest = max((s.uploaded_at for s in ships if s.uploaded_at), default=None)
    out = []
    for s in ships:
        vc = _class_of(classes, s.dwt)
        reasons, ok = [], True
        # Size: the parcel should suit the ship (not much smaller than a large ship, not more than it can carry).
        if cargo_tonnes > 0.95 * s.dwt:
            ok = False
            reasons.append(f"cargo {cargo_tonnes:,.0f} t exceeds about 95% of its {s.dwt:,} t deadweight")
        elif cargo_tonnes < 0.55 * s.dwt:
            ok = False
            reasons.append(f"cargo is under 55% of its {s.dwt:,} t deadweight, so it would sail part-empty")
        # Berth: the ship's own dimensions if the broker gave them, otherwise its class's typical ones.
        if vc is not None:
            r = check_compatibility(port, vc)
            fits, part = r.compatible, r.partial_load_ok
            if s.draft_m is not None and port.max_draft_m is not None:
                d = float(s.draft_m)
                if d <= float(port.max_draft_m):
                    fits, part = True, False
                else:
                    frac = part_laden_fraction(d, float(port.max_draft_m))
                    fits, part = False, frac >= 0.6
                    if part and cargo_tonnes > s.dwt * frac * 0.95:
                        part = False
            if s.loa_m is not None and port.max_loa_m is not None and float(s.loa_m) > float(port.max_loa_m):
                fits, part = False, False
                reasons.append(f"length {float(s.loa_m):.0f} m exceeds {port.name}'s {float(port.max_loa_m):.0f} m limit")
            if not fits and not part:
                ok = False
                reasons.append(f"does not fit {port.name}'s berth limits")
            elif not fits and part:
                reasons.append("fits only part-laden (a smaller cargo than full deadweight)")
        # Timing: open date plus sailing time against the date the cargo is needed.
        origin = origin_of(s.open_port)
        eta = None
        if origin is None:
            reasons.append(f"open port '{s.open_port}' is not one the route table knows, so the ETA cannot be worked out")
        else:
            route = _route(db, origin, port)
            if route and route.distance_nm:
                knots = float(s.speed_knots) if s.speed_knots else DEFAULT_SPEED_KN
                sail = float(route.distance_nm) / (knots * 24)
                eta = s.open_date + timedelta(days=sail + 1)
        deadline = today + timedelta(days=need_by_days)
        if eta is not None and eta > deadline:
            ok = False
            reasons.append(f"would arrive {eta:%d %b}, after the {deadline:%d %b} deadline")
        status = "suitable" if ok and eta is not None else "unknown timing" if ok else "not suitable"
        out.append({"id": s.id, "vessel": s.vessel_name, "imo": s.imo, "dwt": s.dwt, "class": vc.name if vc else None, "open_port": s.open_port, "open_date": s.open_date.isoformat(),
                    "origin": origin, "eta": eta.isoformat() if eta else None, "days_to_deadline": (deadline - eta).days if eta else None, "broker": s.broker, "status": status,
                    "reasons": reasons, "is_sample": bool(s.is_sample)})
    order = {"suitable": 0, "unknown timing": 1, "not suitable": 2}
    out.sort(key=lambda r: (order[r["status"]], -(r["days_to_deadline"] or -999), abs((r["dwt"] or 0) - cargo_tonnes / 0.9)))
    suitable = [r for r in out if r["status"] == "suitable"]
    stale = latest is not None and (datetime.utcnow() - latest).days > STALE_AFTER_DAYS
    return {
        "port": port_name, "cargo_tonnes": cargo_tonnes, "need_by_days": need_by_days, "total_on_lists": len(ships), "suitable_count": len(suitable), "matches": out,
        "lists_last_uploaded": latest.isoformat(timespec="seconds") if latest else None, "lists_stale": stale,
        "any_sample": any(r["is_sample"] for r in out),
        "summary": ("No open-tonnage list has been uploaded, so ship availability cannot be checked. Upload the lists your brokers send." if not ships else
                    f"{len(suitable)} of {len(ships)} listed ships could carry {cargo_tonnes:,.0f} t to {port_name} by day {need_by_days:g}." + (" The lists are more than a week old: ask brokers for fresh positions." if stale else "")),
        "method": "Size (cargo between 55% and 95% of deadweight), berth fit (the ship's own draft and length if given, else its class), and ETA (open date + one day + distance at the ship's speed, default 12 knots) against the deadline. Positions are as the broker stated them; nothing is verified against AIS.",
    }
