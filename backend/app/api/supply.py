"""Ship availability and the laytime calculator."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require
from app.db.session import get_db
from app.models import Port, VesselClass
from app.services import laytime, supply
from app.services.financial import DEMURRAGE_RATE_USD_PER_DAY

router = APIRouter(tags=["supply"])


@router.get("/supply/newcastle", dependencies=[Depends(require("recommend:read"))])
def newcastle() -> dict:
    return supply.newcastle_supply()


class StoppageIn(BaseModel):
    label: str = "Rain"
    hours: float = Field(0, ge=0, le=2000)
    after_laytime: bool = False


class LaytimeIn(BaseModel):
    cargo_tonnes: float = Field(75000, ge=1000, le=400000)
    rate_tonnes_per_day: float = Field(20000, ge=1000, le=100000)
    hours_nor_to_complete: float = Field(120, ge=1, le=2000)
    notice_hours: float = Field(6, ge=0, le=48)
    demurrage_usd_per_day: float = Field(20000, ge=1000, le=200000)
    stoppages: list[StoppageIn] = []


@router.post("/laytime", dependencies=[Depends(require("financial:read"))])
def laytime_claim(p: LaytimeIn) -> dict:
    return laytime.laytime_statement(
        p.cargo_tonnes, p.rate_tonnes_per_day, p.hours_nor_to_complete, p.notice_hours, p.demurrage_usd_per_day,
        [laytime.Stoppage(s.label, s.hours, s.after_laytime) for s in p.stoppages],
    )


@router.get("/laytime/defaults", dependencies=[Depends(require("financial:read"))])
def laytime_defaults() -> dict:
    return {"demurrage_usd_per_day": DEMURRAGE_RATE_USD_PER_DAY, "note": "Benchmark demurrage rates by vessel class from the research compendium; use the charter party rate for a real claim."}
