from pydantic import BaseModel


class ConstraintCheckOut(BaseModel):
    name: str
    required: float | None
    available: float | None
    passed: bool
    detail: str


class TidalLoadPlanOut(BaseModel):
    tonnes_per_cycle: float
    cycles_required: int
    days_required: float
    max_vessels_per_tide: int | None


class CompatibilityResultOut(BaseModel):
    compatible: bool
    port_name: str
    vessel_class_name: str
    checks: list[ConstraintCheckOut]
    tidal_plan: TidalLoadPlanOut | None
    notes: list[str]


class PortOut(BaseModel):
    id: int
    name: str
    country: str
    is_destination: bool
    max_draft_m: float | None
    max_loa_m: float | None
    max_beam_m: float | None
    tidal_restricted: bool
    max_vessels_per_tide: int | None
    annual_capacity_mtpa: float | None
    avg_turnaround_hours: float | None
    notes: str | None

    model_config = {"from_attributes": True}


class VesselClassOut(BaseModel):
    id: int
    name: str
    dwt_min: float
    dwt_max: float
    typical_loa_m: float | None
    typical_beam_m: float | None
    typical_draft_m: float | None

    model_config = {"from_attributes": True}


class MatrixRow(BaseModel):
    port: str
    port_id: int
    vessel_classes: dict[str, bool]
