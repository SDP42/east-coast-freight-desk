from sqlalchemy.orm import Session

from app.models import AuditLog


def record(db: Session, user, action: str, detail: str, allowed: bool = True) -> None:
    """Best-effort audit entry; a logging failure must never break the request."""
    try:
        db.add(AuditLog(user_id=getattr(user, "id", None), email=getattr(user, "email", None), role=getattr(user, "role", None),
                        action=action, detail=detail[:900], allowed=allowed))
        db.commit()
    except Exception:
        db.rollback()
