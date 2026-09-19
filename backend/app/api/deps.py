from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_error

    email = decode_access_token(token)
    if email is None:
        raise credentials_error

    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        raise credentials_error

    return user


def require(permission: str):
    """Dependency factory: the caller must be signed in and hold `permission`, otherwise HTTP 403."""
    from app.core.permissions import PERMISSION_LABELS, has, role_of
    from app.services.audit import record

    def dependency(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        if not has(user, permission):
            record(db, user, "denied", f"missing {permission}", allowed=False)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your role ({role_of(user)['label']}) cannot access this: {PERMISSION_LABELS.get(permission, permission)}.",
            )
        return user

    return dependency


def require_port(user: User, port_name: str, db: Session) -> None:
    """403 unless the user may see `port_name` (port-scoped roles see only their assigned ports)."""
    from app.core.permissions import can_see_port, role_of
    from app.services.audit import record

    if not can_see_port(user, port_name):
        record(db, user, "denied", f"port {port_name} outside assignment", allowed=False)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"{port_name} is outside the ports assigned to your account ({role_of(user)['label']}).")
