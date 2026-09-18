from pydantic import BaseModel


class ShockIn(BaseModel):
    type: str  # freight_spike | port_closure | red_sea_closure | origin_disruption
    pct: float | None = None
    days: float | None = None
    origin_country: str | None = None
    extra_distance_nm: float | None = None


class ScenarioRequest(BaseModel):
    destination_port_id: int
    cargo_tonnes: float
    origin_countries: list[str] | None = None
    shocks: list[ShockIn]


class OriginDeltaOut(BaseModel):
    origin_country: str
    baseline_cost_usd: float | None
    scenario_cost_usd: float | None
    delta_usd: float | None
    delta_pct: float | None
    baseline_rank: int
    scenario_rank: int
    compatible: bool


class ReroutePortOut(BaseModel):
    port_name: str
    best_origin: str
    estimated_total_cost_usd: float
    savings_vs_scenario_best_usd: float


class ScenarioResponse(BaseModel):
    destination_port_name: str
    cargo_tonnes: float
    vessel_class_name: str
    shocks_applied: list[str]
    origins: list[OriginDeltaOut]
    baseline_best_origin: str | None
    scenario_best_origin: str | None
    best_origin_changed: bool
    reroute_alternatives: list[ReroutePortOut]
    summary: str
