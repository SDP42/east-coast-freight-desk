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
