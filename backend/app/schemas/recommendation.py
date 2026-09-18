from pydantic import BaseModel

from app.schemas.compatibility import CompatibilityResultOut


class RecommendationRequest(BaseModel):
    destination_port_id: int
    cargo_tonnes: float
    origin_countries: list[str] | None = None  # None = compare all 5


class OriginRecommendation(BaseModel):
    origin_country: str
    route_id: int | None
    distance_nm: float | None
    typical_transit_days: float | None
    vessel_class_name: str
    compatibility: CompatibilityResultOut
    estimated_freight_usd_per_tonne: float | None
    estimated_total_cost_usd: float | None
    market_index_used: str | None
    market_index_forecast_value: float | None
    market_index_forecast_change_pct: float | None
    rank: int | None
    notes: list[str]


class RecommendationResponse(BaseModel):
    destination_port_name: str
    cargo_tonnes: float
    recommendations: list[OriginRecommendation]
    methodology_note: str
