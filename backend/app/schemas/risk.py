from datetime import date

from pydantic import BaseModel


class DisruptionEventOut(BaseModel):
    id: int
    start_date: date
    end_date: date | None
    category: str
    region: str
    title: str
    description: str | None
    impact_score: float | None
    source_url: str | None

    model_config = {"from_attributes": True}


class RelevantEventOut(BaseModel):
    title: str
    category: str
    region: str
    start_date: date
    impact_score: float
    relevance_weight: float


class RiskFactorOut(BaseModel):
    name: str
    score: float
    weight: float
    detail: str


class RouteRiskOut(BaseModel):
    origin_country: str
    destination_port_name: str
    composite_score: float
    risk_label: str
    factors: list[RiskFactorOut]
    relevant_events: list[RelevantEventOut]
