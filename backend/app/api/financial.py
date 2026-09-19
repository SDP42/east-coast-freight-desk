from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require
from app.db.session import get_db
from app.models import Port, VesselClass
from app.schemas.financial import (
    BallastCandidate,
    BallastOptionOut,
    CoaVsSpotRequest,
    CoaVsSpotResponse,
    DemurrageRequest,
    DemurrageResponse,
    FixtureProjectionOut,
    RoiRequest,
    RoiResponse,
)
from app.services.financial import estimate_demurrage, estimate_roi, rank_ballast_options, simulate_coa_vs_spot

router = APIRouter(prefix="/financial", tags=["financial"], dependencies=[Depends(require("financial:read"))])


@router.post("/coa-vs-spot", response_model=CoaVsSpotResponse)
def coa_vs_spot(payload: CoaVsSpotRequest, db: Session = Depends(get_db)) -> CoaVsSpotResponse:
    try:
        result = simulate_coa_vs_spot(
            db, payload.index_name.upper(), payload.current_rate_usd_per_tonne,
            payload.cargo_tonnes_per_fixture, payload.num_fixtures, payload.interval_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return CoaVsSpotResponse(
        index_name=result.index_name,
        current_index_value=result.current_index_value,
        current_rate_usd_per_tonne=result.current_rate_usd_per_tonne,
        coa_rate_usd_per_tonne=result.coa_rate_usd_per_tonne,
        fixtures=[FixtureProjectionOut(**f.__dict__) for f in result.fixtures],
        total_coa_cost_usd=result.total_coa_cost_usd,
        total_spot_cost_usd=result.total_spot_cost_usd,
        spot_cost_std_usd=result.spot_cost_std_usd,
        expected_savings_usd=result.expected_savings_usd,
        recommendation=result.recommendation,
        rationale=result.rationale,
    )


@router.post("/ballast-options", response_model=list[BallastOptionOut])
def ballast_options(candidates: list[BallastCandidate], db: Session = Depends(get_db)) -> list[BallastOptionOut]:
    tuples = [(c.origin_country, c.destination_port_id, c.laycan_start) for c in candidates]
    results = rank_ballast_options(db, tuples)
    return [BallastOptionOut(**r.__dict__) for r in results]


@router.post("/demurrage", response_model=DemurrageResponse)
def demurrage(payload: DemurrageRequest, db: Session = Depends(get_db)) -> DemurrageResponse:
    port = db.query(Port).filter(Port.id == payload.port_id).first()
    if not port:
        raise HTTPException(status_code=404, detail=f"Port {payload.port_id} not found")
    vessel_class = db.query(VesselClass).filter(VesselClass.id == payload.vessel_class_id).first()
    if not vessel_class:
        raise HTTPException(status_code=404, detail=f"Vessel class {payload.vessel_class_id} not found")

    result = estimate_demurrage(port, vessel_class, payload.laytime_allowed_days)
    return DemurrageResponse(**result.__dict__)


@router.post("/roi", response_model=RoiResponse)
def roi(payload: RoiRequest, db: Session = Depends(get_db)) -> RoiResponse:
    try:
        result = estimate_roi(
            db, payload.index_name.upper(), payload.annual_cargo_tonnes,
            payload.assumed_freight_usd_per_tonne, payload.captured_pct,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return RoiResponse(**result.__dict__)
