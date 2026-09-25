"""Administration: users, roles, port assignments and the audit log (admin only), plus the read-only
role/permission matrix that every signed-in user can see."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require
from app.core.permissions import PERMISSION_LABELS, ROLES, assigned_ports, role_of
from app.db.session import get_db
from app.models import AuditLog, Port, User
from app.services.audit import record

router = APIRouter(tags=["admin"])


@router.get("/access/matrix")
def access_matrix(_: User = Depends(get_current_user)) -> dict:
    return {
        "permissions": PERMISSION_LABELS,
        "roles": [{"key": k, "label": r["label"], "level": r["level"], "summary": r["summary"], "port_scoped": r["port_scoped"], "permissions": sorted(r["permissions"])}
                  for k, r in sorted(ROLES.items(), key=lambda t: -t[1]["level"])],
    }


def _user_out(u: User) -> dict:
    return {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role, "role_label": role_of(u)["label"], "persona": u.persona,
            "assigned_ports": assigned_ports(u), "is_active": u.is_active, "is_demo": u.is_demo, "created_at": str(u.created_at)}


@router.get("/admin/users")
def list_users(db: Session = Depends(get_db), _: User = Depends(require("admin:users"))) -> dict:
    ports = [p.name for p in db.query(Port).filter(Port.is_destination.is_(True)).order_by(Port.name).all()]
    return {"users": [_user_out(u) for u in db.query(User).order_by(User.id).all()], "roles": [{"key": k, "label": r["label"]} for k, r in ROLES.items()], "ports": ports}


class UserPatch(BaseModel):
    role: str | None = None
    assigned_ports: list[str] | None = None
    is_active: bool | None = None


@router.patch("/admin/users/{user_id}")
def patch_user(user_id: int, p: UserPatch, db: Session = Depends(get_db), admin: User = Depends(require("admin:users"))) -> dict:
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.is_demo:
        raise HTTPException(status_code=409, detail="Demo accounts are fixed so the demo always behaves the same.")
    if target.id == admin.id and (p.role not in (None, admin.role) or p.is_active is False):
        raise HTTPException(status_code=409, detail="You cannot change your own role or deactivate yourself.")
    changes = []
    if p.role is not None:
        if p.role not in ROLES:
            raise HTTPException(status_code=422, detail=f"role must be one of {list(ROLES)}")
        changes.append(f"role {target.role}->{p.role}")
        target.role = p.role
    if p.assigned_ports is not None:
        valid = {x.name for x in db.query(Port).filter(Port.is_destination.is_(True)).all()}
        bad = [x for x in p.assigned_ports if x not in valid]
        if bad:
            raise HTTPException(status_code=422, detail=f"Unknown ports: {bad}")
        target.assigned_ports = json.dumps(p.assigned_ports)
        changes.append(f"ports {p.assigned_ports}")
    if p.is_active is not None:
        target.is_active = p.is_active
        changes.append(f"active={p.is_active}")
    db.commit()
    record(db, admin, "admin_change", f"user {target.email}: {', '.join(changes) or 'no change'}")
    return _user_out(target)


@router.get("/admin/audit")
def audit(limit: int = Query(100, ge=1, le=500), denied_only: bool = False, db: Session = Depends(get_db), _: User = Depends(require("admin:users"))) -> dict:
    q = db.query(AuditLog)
    if denied_only:
        q = q.filter(AuditLog.allowed.is_(False))
    rows = q.order_by(AuditLog.id.desc()).limit(limit).all()
    return {"entries": [{"id": r.id, "at": str(r.created_at), "email": r.email, "role": r.role, "action": r.action, "detail": r.detail, "allowed": r.allowed} for r in rows],
            "denied_total": db.query(AuditLog).filter(AuditLog.allowed.is_(False)).count(), "total": db.query(AuditLog).count()}


@router.get("/admin/data-health")
def data_health(db: Session = Depends(get_db), _: User = Depends(require("admin:users"))) -> dict:
    from app.services.datahealth import data_health as build
    return build(db)


@router.get("/admin/analytics")
def analytics(days: int = Query(14, ge=1, le=90), db: Session = Depends(get_db), _: User = Depends(require("admin:users"))) -> dict:
    from app.services.insights import admin_analytics
    return admin_analytics(db, days)


@router.get("/admin/refresh-status")
def refresh_status(_: User = Depends(require("admin:users"))) -> dict:
    from app.services import refresh

    return refresh.status()


@router.post("/admin/refresh-data")
def refresh_data(db: Session = Depends(get_db), admin: User = Depends(require("admin:users"))) -> dict:
    """Fetch the latest public observations now instead of waiting for the schedule."""
    from app.services import refresh

    return refresh.refresh_all(db)
