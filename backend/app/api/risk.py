from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require, require_port
from app.db.session import get_db
from app.models import DisruptionEvent, Port, User
from app.schemas.risk import DisruptionEventOut, RelevantEventOut, RiskFactorOut, RouteRiskOut
from app.services.risk import compute_route_risk

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/events", response_model=list[DisruptionEventOut])
def list_events(db: Session = Depends(get_db), _: User = Depends(require("risk:read"))) -> list[DisruptionEvent]:
    return db.query(DisruptionEvent).order_by(DisruptionEvent.start_date.desc()).all()


@router.get("/score", response_model=RouteRiskOut)
def get_route_risk(origin_country: str, destination_port_id: int, db: Session = Depends(get_db), user: User = Depends(require("risk:read"))) -> RouteRiskOut:
    destination = db.query(Port).filter(Port.id == destination_port_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail=f"Port {destination_port_id} not found")
    require_port(user, destination.name, db)

    result = compute_route_risk(db, origin_country, destination)
    return RouteRiskOut(
        origin_country=result.origin_country,
        destination_port_name=result.destination_port_name,
        composite_score=result.composite_score,
        risk_label=result.risk_label,
        factors=[RiskFactorOut(**f.__dict__) for f in result.factors],
        relevant_events=[RelevantEventOut(**e.__dict__) for e in result.relevant_events],
    )
