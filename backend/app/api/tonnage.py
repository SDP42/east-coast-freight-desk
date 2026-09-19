"""Open-tonnage endpoints: upload broker lists, list them, and match ships to a cargo."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require
from app.db.session import get_db
from app.models import OpenTonnage, User
from app.services import tonnage
from app.services.audit import record

router = APIRouter(prefix="/tonnage", tags=["tonnage"])
MAX_BYTES = 2_000_000


def _out(t: OpenTonnage) -> dict:
    return {"id": t.id, "vessel": t.vessel_name, "imo": t.imo, "dwt": t.dwt, "loa_m": float(t.loa_m) if t.loa_m is not None else None, "beam_m": float(t.beam_m) if t.beam_m is not None else None,
            "draft_m": float(t.draft_m) if t.draft_m is not None else None, "open_port": t.open_port, "open_date": t.open_date.isoformat(), "speed_knots": float(t.speed_knots) if t.speed_knots is not None else None,
            "broker": t.broker, "notes": t.notes, "is_sample": bool(t.is_sample), "uploaded_at": str(t.uploaded_at)}


@router.get("", dependencies=[Depends(require("recommend:read"))])
def list_tonnage(db: Session = Depends(get_db)) -> dict:
    rows = db.query(OpenTonnage).order_by(OpenTonnage.open_date, OpenTonnage.vessel_name).all()
    return {"ships": [_out(r) for r in rows], "count": len(rows),
            "template": "vessel_name, imo, dwt, loa_m, beam_m, draft_m, open_port, open_date, speed_knots, broker, notes (only vessel_name, dwt, open_port and open_date are required)"}


@router.post("/upload")
async def upload(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(require("ledger:write"))) -> dict:
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than 2 MB")
    try:
        rows, errors = tonnage.parse_upload(content, file.filename or "")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:  # noqa: BLE001 - unreadable file
        raise HTTPException(status_code=422, detail="Could not read the file. Use a CSV or Excel (.xlsx) list.")
    added = tonnage.add_rows(db, rows, user.id)
    record(db, user, "tonnage_upload", f"{file.filename}: {added} ships added, {len(errors)} rows skipped")
    return {"added": added, "skipped": errors[:50], "skipped_count": len(errors)}


@router.post("/sample")
def load_sample(db: Session = Depends(get_db), user: User = Depends(require("ledger:write"))) -> dict:
    if db.query(OpenTonnage).filter(OpenTonnage.is_sample.is_(True)).count():
        raise HTTPException(status_code=409, detail="The sample list is already loaded")
    return {"added": tonnage.add_rows(db, tonnage.sample_rows(), user.id, is_sample=True), "note": "Ten invented ships, clearly labelled as a sample."}


@router.delete("/{ship_id}")
def delete_ship(ship_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    from app.core.permissions import has

    t = db.query(OpenTonnage).filter(OpenTonnage.id == ship_id).first()
    if t is None:
        raise HTTPException(status_code=404, detail="Not found")
    if not (has(user, "admin:users") or t.owner_id == user.id):
        raise HTTPException(status_code=403, detail="Only the person who uploaded a ship, or an administrator, can remove it")
    db.delete(t)
    db.commit()
    return {"deleted": ship_id}


class MatchIn(BaseModel):
    port: str = "Paradip"
    cargo_tonnes: float = Field(60000, ge=5000, le=400000)
    need_by_days: float = Field(30, ge=3, le=120)


@router.post("/match", dependencies=[Depends(require("recommend:read"))])
def match(p: MatchIn, db: Session = Depends(get_db)) -> dict:
    try:
        return tonnage.match(db, p.port, p.cargo_tonnes, p.need_by_days)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


class TextIn(BaseModel):
    text: str = Field(min_length=8, max_length=20000)


@router.post("/parse-text")
def parse_text(p: TextIn, user: User = Depends(require("ledger:write"))) -> dict:
    """Turn pasted broker position text into suggested rows. Nothing is saved until the user confirms."""
    rows, skipped = tonnage.parse_text(p.text)
    return {"rows": [{**r, "open_date": r["open_date"].isoformat()} for r in rows], "unread_lines": skipped[:30], "note": "Suggestions only: check each row, then save."}


class RowIn(BaseModel):
    vessel_name: str = Field(min_length=1, max_length=120)
    dwt: int = Field(ge=8000, le=400000)
    open_port: str = Field(min_length=2, max_length=80)
    open_date: str
    draft_m: float | None = None
    loa_m: float | None = None
    broker: str | None = None
    notes: str | None = None


class RowsIn(BaseModel):
    rows: list[RowIn] = Field(min_length=1, max_length=200)


@router.post("/save-rows")
def save_rows(p: RowsIn, db: Session = Depends(get_db), user: User = Depends(require("ledger:write"))) -> dict:
    from datetime import date as _date

    rows = []
    for r in p.rows:
        try:
            d = _date.fromisoformat(r.open_date)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Bad date '{r.open_date}' for {r.vessel_name}")
        rows.append({"vessel_name": r.vessel_name.strip(), "dwt": r.dwt, "open_port": r.open_port.strip(), "open_date": d, "draft_m": r.draft_m, "loa_m": r.loa_m,
                     "broker": r.broker, "notes": r.notes or "", "imo": None, "beam_m": None, "speed_knots": None})
    added = tonnage.add_rows(db, rows, user.id)
    record(db, user, "tonnage_upload", f"pasted text: {added} ships added")
    return {"added": added}


@router.get("/template.csv")
def template() -> "Response":
    from fastapi.responses import PlainTextResponse

    body = "vessel_name,imo,dwt,loa_m,beam_m,draft_m,open_port,open_date,speed_knots,broker,notes\nMV Example,,82000,229,32.3,14.2,Hay Point,2026-10-01,12.5,Your broker,Example row\n"
    return PlainTextResponse(body, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=open_tonnage_template.csv"})
