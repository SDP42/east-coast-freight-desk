"""Port–Vessel Compatibility Engine — feature #1 in FEATURES.md, the single
biggest differentiator this project has: a hard-constraint rules engine built
from our own researched draft/LOA/beam/tidal data for all 7 East Coast ports
(SIH2026_Research_and_References.docx, Table 1), rather than treating vessel
recommendation and port physical feasibility as separate problems the way
every reviewed paper and competitor platform (Veson, Xeneta, Signal Ocean,
Windward) does.
"""

import math
from dataclasses import dataclass, field

from app.models import Port, VesselClass

# Conservative default cargo handling rate (tonnes/day) used only when a port
# has no berth-level rate on file — real per-berth rates (where known) live on
# the Berth model and should be preferred once populated.
DEFAULT_HANDLING_RATE_TPD = 20_000

# Real, researched figure for Haldia specifically (SIH2026 research
# compendium, Section 3.2): a Panamax can load/discharge only a fraction of
# its parcel per tidal cycle due to draft limits — flagged in that research as
# a search-derived estimate, not a directly-quoted primary figure, so treated
# here as a configurable default rather than a certainty.
TONNES_PER_TIDAL_CYCLE_DEFAULT = 26_500
TIDES_PER_DAY = 2


@dataclass
class ConstraintCheck:
    name: str
    required: float | None
    available: float | None
    passed: bool
    detail: str


@dataclass
class TidalLoadPlan:
    tonnes_per_cycle: float
    cycles_required: int
    days_required: float
    max_vessels_per_tide: int | None


@dataclass
class CompatibilityResult:
    compatible: bool
    port_name: str
    vessel_class_name: str
    checks: list[ConstraintCheck] = field(default_factory=list)
    tidal_plan: TidalLoadPlan | None = None
    notes: list[str] = field(default_factory=list)


def check_compatibility(port: Port, vessel_class: VesselClass, cargo_tonnes: float | None = None) -> CompatibilityResult:
    checks: list[ConstraintCheck] = []
    notes: list[str] = []

    def add_check(name: str, required: float | None, available: float | None, passed: bool, detail: str) -> None:
        checks.append(ConstraintCheck(name=name, required=required, available=available, passed=passed, detail=detail))

    if vessel_class.typical_draft_m is not None and port.max_draft_m is not None:
        passed = float(vessel_class.typical_draft_m) <= float(port.max_draft_m)
        add_check(
            "draft", float(vessel_class.typical_draft_m), float(port.max_draft_m), passed,
            f"{vessel_class.name} typical draft {vessel_class.typical_draft_m}m "
            f"{'fits within' if passed else 'exceeds'} {port.name}'s max draft {port.max_draft_m}m",
        )
    else:
        notes.append("Draft data incomplete for this port/vessel-class pair — treated as unknown, not a pass.")

    if vessel_class.typical_loa_m is not None and port.max_loa_m is not None:
        passed = float(vessel_class.typical_loa_m) <= float(port.max_loa_m)
        add_check(
            "loa", float(vessel_class.typical_loa_m), float(port.max_loa_m), passed,
            f"{vessel_class.name} typical LOA {vessel_class.typical_loa_m}m "
            f"{'fits within' if passed else 'exceeds'} {port.name}'s max LOA {port.max_loa_m}m",
        )

    if vessel_class.typical_beam_m is not None and port.max_beam_m is not None:
        passed = float(vessel_class.typical_beam_m) <= float(port.max_beam_m)
        add_check(
            "beam", float(vessel_class.typical_beam_m), float(port.max_beam_m), passed,
            f"{vessel_class.name} typical beam {vessel_class.typical_beam_m}m "
            f"{'fits within' if passed else 'exceeds'} {port.name}'s max beam {port.max_beam_m}m",
        )

    hard_checks_passed = all(c.passed for c in checks) if checks else False
    tidal_plan = None

    if hard_checks_passed and port.tidal_restricted:
        notes.append(
            f"{port.name} is tide-restricted"
            + (f" ({port.max_vessels_per_tide} vessels/tide)" if port.max_vessels_per_tide else "")
            + " — see tidal_plan for the loading schedule this implies."
        )
        if cargo_tonnes:
            tonnes_per_cycle = TONNES_PER_TIDAL_CYCLE_DEFAULT
            cycles_required = math.ceil(cargo_tonnes / tonnes_per_cycle)
            tidal_plan = TidalLoadPlan(
                tonnes_per_cycle=tonnes_per_cycle,
                cycles_required=cycles_required,
                days_required=round(cycles_required / TIDES_PER_DAY, 1),
                max_vessels_per_tide=port.max_vessels_per_tide,
            )

    return CompatibilityResult(
        compatible=hard_checks_passed,
        port_name=port.name,
        vessel_class_name=vessel_class.name,
        checks=checks,
        tidal_plan=tidal_plan,
        notes=notes,
    )


def build_compatibility_matrix(ports: list[Port], vessel_classes: list[VesselClass]) -> list[dict]:
    matrix = []
    for port in ports:
        row = {"port": port.name, "port_id": port.id, "vessel_classes": {}}
        for vc in vessel_classes:
            result = check_compatibility(port, vc)
            row["vessel_classes"][vc.name] = result.compatible
        matrix.append(row)
    return matrix
