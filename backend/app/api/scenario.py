from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require
from app.db.session import get_db
from app.models import Port
from app.schemas.scenario import OriginDeltaOut, ReroutePortOut, ScenarioRequest, ScenarioResponse
from app.services.scenario import Shock, run_scenario

router = APIRouter(prefix="/scenario", tags=["scenario"], dependencies=[Depends(require("recommend:read"))])

DEFAULT_ORIGINS = ["Australia", "United States", "Mozambique", "Russia", "Indonesia"]
VALID_SHOCKS = {"freight_spike", "port_closure", "red_sea_closure", "origin_disruption"}


@router.post("/run", response_model=ScenarioResponse)
def run(payload: ScenarioRequest, db: Session = Depends(get_db)) -> ScenarioResponse:
    destination = db.query(Port).filter(Port.id == payload.destination_port_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail=f"Port {payload.destination_port_id} not found")
    if payload.cargo_tonnes <= 0:
        raise HTTPException(status_code=422, detail="cargo_tonnes must be positive")
    bad = [s.type for s in payload.shocks if s.type not in VALID_SHOCKS]
    if bad:
        raise HTTPException(status_code=422, detail=f"Unknown shock type(s): {bad}. Valid: {sorted(VALID_SHOCKS)}")

    result = run_scenario(
        db, destination, payload.cargo_tonnes, payload.origin_countries or DEFAULT_ORIGINS,
        [Shock(**s.model_dump()) for s in payload.shocks],
    )
    return ScenarioResponse(
        destination_port_name=result.destination_port_name,
        cargo_tonnes=result.cargo_tonnes,
        vessel_class_name=result.vessel_class_name,
        shocks_applied=result.shocks_applied,
        origins=[OriginDeltaOut(**o.__dict__) for o in result.origins],
        baseline_best_origin=result.baseline_best_origin,
        scenario_best_origin=result.scenario_best_origin,
        best_origin_changed=result.best_origin_changed,
        reroute_alternatives=[ReroutePortOut(**r.__dict__) for r in result.reroute_alternatives],
        summary=result.summary,
    )
