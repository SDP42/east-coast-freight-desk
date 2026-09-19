from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import login_guard
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import User
from app.core.personas import PERSONAS, SELF_REGISTER_PERSONAS
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.audit import record
from app.core.permissions import permissions_of, port_scope, role_of
from app.schemas.user import ChangePassword, PersonaOut, ProfileUpdate, Token, UserCreate, UserRead
from app.services.auth import authenticate_user, create_user, get_user_by_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/personas", response_model=list[PersonaOut])
def list_personas() -> list[PersonaOut]:
    """Personas a user can pick at sign-up (admin is excluded)."""
    return [PersonaOut(key=k, **{f: PERSONAS[k][f] for f in ("label", "description", "focus")}) for k in SELF_REGISTER_PERSONAS]


def user_out(u: User) -> UserRead:
    r = role_of(u)
    out = UserRead.model_validate(u)
    out.role_label, out.level, out.role_summary = r["label"], r["level"], r["summary"]
    out.permissions = sorted(permissions_of(u))
    out.port_scope = port_scope(u)
    return out


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    if get_user_by_email(db, data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    return user_out(create_user(db, data))


@router.post("/login", response_model=Token)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    # OAuth2PasswordRequestForm's field is named "username" by the spec — we treat it as the email.
    keys = (f"email:{form_data.username.lower()}", f"ip:{request.client.host if request.client else 'unknown'}")
    wait = login_guard.retry_after(*keys)
    if wait:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed sign-in attempts. Try again in {max(1, wait // 60)} minute(s).",
            headers={"Retry-After": str(wait)},
        )
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        login_guard.record_failure(*keys)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    login_guard.clear(keys[0])
    record(db, user, "login", "password sign-in")
    return Token(access_token=create_access_token(subject=user.email))


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserRead:
    return user_out(current_user)


@router.patch("/me", response_model=UserRead)
def update_profile(data: ProfileUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> UserRead:
    if data.full_name is not None:
        current_user.full_name = data.full_name.strip() or None
    if data.persona is not None:
        current_user.persona = data.persona
    db.commit()
    db.refresh(current_user)
    return user_out(current_user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(data: ChangePassword, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> None:
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if verify_password(data.new_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must differ from the current one")
    current_user.hashed_password = hash_password(data.new_password)
    db.commit()


class DemoLogin(BaseModel):
    email: str


@router.get("/demo-accounts")
def demo_accounts(db: Session = Depends(get_db)) -> list[dict]:
    """The seeded demo accounts (empty when demo login is switched off)."""
    if not get_settings().ALLOW_DEMO_LOGIN:
        return []
    out = []
    for u in db.query(User).filter(User.is_demo.is_(True), User.is_active.is_(True)).order_by(User.id).all():
        r = role_of(u)
        out.append({"email": u.email, "full_name": u.full_name, "role": u.role, "role_label": r["label"], "level": r["level"], "summary": r["summary"], "port_scope": port_scope(u)})
    return sorted(out, key=lambda x: -x["level"])


@router.post("/demo-login", response_model=Token)
def demo_login(body: DemoLogin, db: Session = Depends(get_db)) -> Token:
    """Passwordless sign-in, only for accounts flagged is_demo and only when ALLOW_DEMO_LOGIN is on."""
    user = get_user_by_email(db, body.email)
    if not get_settings().ALLOW_DEMO_LOGIN or not user or not user.is_demo or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Demo sign-in is not available for that account")
    record(db, user, "demo_login", "one-click demo sign-in")
    return Token(access_token=create_access_token(subject=user.email))
