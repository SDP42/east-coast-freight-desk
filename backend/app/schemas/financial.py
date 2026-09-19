from datetime import date

from pydantic import BaseModel


class CoaVsSpotRequest(BaseModel):
    index_name: str
    current_rate_usd_per_tonne: float
    cargo_tonnes_per_fixture: float
    num_fixtures: int = 6
    interval_days: int = 30


class FixtureProjectionOut(BaseModel):
    fixture_number: int
    date: date
    forecast_index_value: float
    projected_spot_rate_usd_per_tonne: float


class CoaVsSpotResponse(BaseModel):
    index_name: str
    current_index_value: float
    current_rate_usd_per_tonne: float
    coa_rate_usd_per_tonne: float
    fixtures: list[FixtureProjectionOut]
    total_coa_cost_usd: float
    total_spot_cost_usd: float
    spot_cost_std_usd: float
    expected_savings_usd: float
    recommendation: str
    rationale: str


class BallastCandidate(BaseModel):
    origin_country: str
    destination_port_id: int
    laycan_start: date | None = None


class BallastOptionOut(BaseModel):
    origin_country: str
    destination_port_name: str
    estimated_ballast_days: float
    laycan_wait_days: float
    total_idle_days: float
    notes: str


class DemurrageRequest(BaseModel):
    port_id: int
    vessel_class_id: int
    laytime_allowed_days: float = 3.0


class DemurrageResponse(BaseModel):
    port_name: str
    vessel_class_name: str
    actual_turnaround_days: float
    laytime_allowed_days: float
    demurrage_days: float
    demurrage_rate_usd_per_day: float
    expected_demurrage_usd: float
    notes: list[str]


class RoiRequest(BaseModel):
    index_name: str = "BPI"
    annual_cargo_tonnes: float
    assumed_freight_usd_per_tonne: float
    captured_pct: float = 20.0


class RoiResponse(BaseModel):
    index_name: str
    historical_coefficient_of_variation_pct: float
    annual_cargo_tonnes: float
    assumed_freight_usd_per_tonne: float
    captured_pct: float
    estimated_annual_savings_usd: float
    notes: str
