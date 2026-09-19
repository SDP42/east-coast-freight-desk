"""What-If Studio and Urgent Fixture Desk endpoints (need financial:read: they expose cost estimates)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require
from app.db.session import get_db
from app.services import whatif

router = APIRouter(prefix="/whatif", tags=["whatif"], dependencies=[Depends(require("financial:read"))])
ORIGINS = ["Australia", "United States", "Mozambique", "Russia", "Indonesia"]
PORTS = ["Paradip", "Visakhapatnam", "Gangavaram", "Dhamra", "Gopalpur", "Haldia"]


class LeverIn(BaseModel):
    origin: str = "Australia"
    port: str = "Haldia"
    cargo_tonnes: float = Field(75000, ge=5000, le=400000)
    vessel_class: str = "Panamax"
    freight_shock_pct: float = Field(0, ge=-60, le=300)
    inr_shock_pct: float = Field(0, ge=-30, le=50)
    bunker_shock_pct: float = Field(0, ge=-60, le=200)
    port_delay_days: float = Field(0, ge=0, le=30)
    storm_delay_days: float = Field(0, ge=0, le=20)
    reroute_nm: float = Field(0, ge=0, le=8000)
    speed_knots: float = Field(12, ge=8, le=16)
    laytime_days: float = Field(2.5, ge=0.5, le=10)
    urgency_premium_pct: float = Field(0, ge=0, le=60)


def _lv(p: LeverIn) -> whatif.Levers:
    return whatif.Levers(**p.model_dump())


def _guard(fn):
    try:
        return fn()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/meta")
def meta() -> dict:
    return {"origins": ORIGINS, "ports": PORTS, "vessel_classes": ["Handysize", "Supramax", "Panamax", "Capesize"], "playbooks": whatif.PLAYBOOKS}


@router.post("/run")
def run(p: LeverIn, db: Session = Depends(get_db)) -> dict:
    return _guard(lambda: whatif.what_if(db, _lv(p)))


@router.post("/sensitivity")
def sens(p: LeverIn, db: Session = Depends(get_db)) -> dict:
    return _guard(lambda: whatif.sensitivity(db, _lv(p)))


class BreakevenIn(BaseModel):
    a: LeverIn
    b: LeverIn


@router.post("/breakeven")
def be(p: BreakevenIn, db: Session = Depends(get_db)) -> dict:
    return _guard(lambda: whatif.breakeven(db, _lv(p.a), _lv(p.b)))


class UrgentIn(BaseModel):
    port: str = "Paradip"
    cargo_tonnes: float = Field(60000, ge=5000, le=400000)
    deadline_days: float = Field(20, ge=5, le=90)


@router.post("/urgent")
def urgent(p: UrgentIn, db: Session = Depends(get_db)) -> dict:
    from app.core.cache import cached

    return _guard(lambda: cached(f"urgent:{p.port}:{p.cargo_tonnes}:{p.deadline_days}", 600, lambda: whatif.urgent_desk(db, p.port, p.cargo_tonnes, p.deadline_days)))
