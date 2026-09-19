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


@router.post("/laytime", dependencies=[Depends(require("ports:read"))])
def laytime_claim(p: LaytimeIn) -> dict:
    return laytime.laytime_statement(
        p.cargo_tonnes, p.rate_tonnes_per_day, p.hours_nor_to_complete, p.notice_hours, p.demurrage_usd_per_day,
        [laytime.Stoppage(s.label, s.hours, s.after_laytime) for s in p.stoppages],
    )


@router.get("/laytime/defaults", dependencies=[Depends(require("ports:read"))])
def laytime_defaults() -> dict:
    return {"demurrage_usd_per_day": DEMURRAGE_RATE_USD_PER_DAY, "note": "Benchmark demurrage rates by vessel class from the research compendium; use the charter party rate for a real claim."}


class VerdictIn(BaseModel):
    port: str = "Paradip"
    cargo_tonnes: float = Field(60000, ge=5000, le=400000)
    need_by_days: float = Field(45, ge=7, le=90)


@router.post("/verdict", dependencies=[Depends(require("financial:read"))])
def verdict_call(p: VerdictIn, db: Session = Depends(get_db)) -> dict:
    from app.core.cache import cached
    from app.services import verdict
    try:
        return cached(f"verdict:{p.port}:{p.cargo_tonnes}:{p.need_by_days}", 600, lambda: verdict.build(db, p.port, p.cargo_tonnes, p.need_by_days))
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=str(e))


class ParcelIn(BaseModel):
    origin: str = "Australia"
    port: str = "Paradip"
    cargo_tonnes: float = Field(75000, ge=5000, le=400000)
    vessel_class: str = "Panamax"
    count: int = Field(1, ge=1, le=200)


class ProgrammeIn(BaseModel):
    parcels: list[ParcelIn] = []


@router.post("/finance/programme", dependencies=[Depends(require("financial:read"))])
def programme(p: ProgrammeIn, db: Session = Depends(get_db)) -> dict:
    from fastapi import HTTPException
    from app.services import insights
    try:
        return insights.programme_plan(db, [x.model_dump() for x in p.parcels] or None)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


class MixIn(BaseModel):
    mix: dict[str, float] = {}
    port: str = "Paradip"
    cargo_tonnes: float = Field(75000, ge=5000, le=400000)


@router.post("/sourcing/resilience", dependencies=[Depends(require("demand:read"))])
def sourcing_resilience(p: MixIn, db: Session = Depends(get_db)) -> dict:
    from app.services import insights
    return insights.resilience(db, p.mix or None, p.port, p.cargo_tonnes)


@router.get("/verdict/evidence", dependencies=[Depends(require("financial:read"))])
def verdict_evidence(db: Session = Depends(get_db)) -> dict:
    from app.services import verdict_eval
    return verdict_eval.evidence(db)


@router.get("/weather/window")
def weather_window(port: str, db: Session = Depends(get_db), user=Depends(require("ports:read"))) -> dict:
    from fastapi import HTTPException
    from app.api.deps import require_port
    from app.services import weather
    require_port(user, port, db)
    try:
        return weather.window(db, port)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001 - network or upstream error
        raise HTTPException(status_code=502, detail=f"Weather service unavailable: {type(e).__name__}")


class OptimiseIn(BaseModel):
    demand_kt: dict[str, float] = {}
    port_cap_kt: dict[str, float] = {}
    max_share: dict[str, float] = {}
    vessel_class: str = "Panamax"


@router.post("/sourcing/optimise", dependencies=[Depends(require("financial:read"))])
def sourcing_optimise(p: OptimiseIn, db: Session = Depends(get_db)) -> dict:
    from app.services import optimiser
    return optimiser.optimise(db, p.demand_kt or None, p.port_cap_kt or None, p.max_share or None, p.vessel_class)
