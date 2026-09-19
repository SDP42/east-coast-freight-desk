from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require, require_port
from app.core.permissions import port_scope
from app.db.session import get_db
from app.models import Port, User, VesselClass
from app.schemas.compatibility import (
    CompatibilityResultOut,
    ConstraintCheckOut,
    MatrixRow,
    PortOut,
    TidalLoadPlanOut,
    VesselClassOut,
)
from app.services.compatibility import build_compatibility_matrix, check_compatibility

router = APIRouter(prefix="/compatibility", tags=["compatibility"])


@router.get("/ports", response_model=list[PortOut])
def list_ports(destination_only: bool = True, db: Session = Depends(get_db), user: User = Depends(require("ports:read"))) -> list[Port]:
    query = db.query(Port)
    if destination_only:
        query = query.filter(Port.is_destination.is_(True))
    scope = port_scope(user)
    if scope is not None:
        query = query.filter(Port.name.in_(scope))
    return query.order_by(Port.name).all()


@router.get("/vessel-classes", response_model=list[VesselClassOut])
def list_vessel_classes(db: Session = Depends(get_db), _: User = Depends(require("ports:read"))) -> list[VesselClass]:
    return db.query(VesselClass).order_by(VesselClass.dwt_min).all()


@router.get("/matrix", response_model=list[MatrixRow])
def get_matrix(db: Session = Depends(get_db), user: User = Depends(require("ports:read"))) -> list[MatrixRow]:
    query = db.query(Port).filter(Port.is_destination.is_(True))
    scope = port_scope(user)
    if scope is not None:
        query = query.filter(Port.name.in_(scope))
    ports = query.order_by(Port.name).all()
    vessel_classes = db.query(VesselClass).order_by(VesselClass.dwt_min).all()
    if not ports or not vessel_classes:
        raise HTTPException(status_code=404, detail="Ports or vessel classes not seeded yet")
    return build_compatibility_matrix(ports, vessel_classes)


@router.get("/check", response_model=CompatibilityResultOut)
def get_check(
    port_id: int,
    vessel_class_id: int,
    cargo_tonnes: float | None = Query(default=None, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require("ports:read")),
) -> CompatibilityResultOut:
    port = db.query(Port).filter(Port.id == port_id).first()
    if not port:
        raise HTTPException(status_code=404, detail=f"Port {port_id} not found")
    require_port(user, port.name, db)

    vessel_class = db.query(VesselClass).filter(VesselClass.id == vessel_class_id).first()
    if not vessel_class:
        raise HTTPException(status_code=404, detail=f"Vessel class {vessel_class_id} not found")

    result = check_compatibility(port, vessel_class, cargo_tonnes)
    return CompatibilityResultOut(
        compatible=result.compatible,
        port_name=result.port_name,
        vessel_class_name=result.vessel_class_name,
        checks=[ConstraintCheckOut(**c.__dict__) for c in result.checks],
        tidal_plan=TidalLoadPlanOut(**result.tidal_plan.__dict__) if result.tidal_plan else None,
        notes=result.notes,
    )
