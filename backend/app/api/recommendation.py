from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Port
from app.schemas.compatibility import CompatibilityResultOut, ConstraintCheckOut, TidalLoadPlanOut
from app.schemas.recommendation import OriginRecommendation, RecommendationRequest, RecommendationResponse
from app.services.recommendation import compare_origins

router = APIRouter(prefix="/recommendation", tags=["recommendation"])

DEFAULT_ORIGINS = ["Australia", "United States", "Mozambique", "Russia", "Indonesia"]


@router.post("/compare", response_model=RecommendationResponse)
def compare(payload: RecommendationRequest, db: Session = Depends(get_db)) -> RecommendationResponse:
    destination = db.query(Port).filter(Port.id == payload.destination_port_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail=f"Destination port {payload.destination_port_id} not found")
    if payload.cargo_tonnes <= 0:
        raise HTTPException(status_code=422, detail="cargo_tonnes must be positive")

    origins = payload.origin_countries or DEFAULT_ORIGINS
    results = compare_origins(db, destination, payload.cargo_tonnes, origins)

    recommendations = []
    for rank, r in enumerate(results, start=1):
        c = r.compatibility
        recommendations.append(
            OriginRecommendation(
                origin_country=r.origin_country,
                route_id=r.route.id if r.route else None,
                distance_nm=float(r.route.distance_nm) if r.route and r.route.distance_nm else None,
                typical_transit_days=float(r.route.typical_transit_days) if r.route and r.route.typical_transit_days else None,
                vessel_class_name=r.vessel_class.name,
                compatibility=CompatibilityResultOut(
                    compatible=c.compatible,
                    port_name=c.port_name,
                    vessel_class_name=c.vessel_class_name,
                    checks=[ConstraintCheckOut(**ch.__dict__) for ch in c.checks],
                    tidal_plan=TidalLoadPlanOut(**c.tidal_plan.__dict__) if c.tidal_plan else None,
                    notes=c.notes,
                ),
                estimated_freight_usd_per_tonne=r.estimated_freight_usd_per_tonne,
                estimated_total_cost_usd=r.estimated_total_cost_usd,
                market_index_used=r.market_signal.index_name,
                market_index_forecast_value=r.market_signal.forecast_value,
                market_index_forecast_change_pct=r.market_signal.change_pct,
                rank=rank,
                notes=r.notes,
            )
        )

    return RecommendationResponse(
        destination_port_name=destination.name,
        cargo_tonnes=payload.cargo_tonnes,
        recommendations=recommendations,
        methodology_note=(
            "Cost estimates are illustrative (distance × a published $/tonne-per-1000nm benchmark × "
            "vessel-class multiplier), not live freight quotes — see each recommendation's notes. "
            "Compatibility is a hard physical constraint from Section 7; ranking is by estimated cost "
            "among physically compatible origins first."
        ),
    )
