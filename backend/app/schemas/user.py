from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.personas import DEFAULT_PERSONA, SELF_REGISTER_PERSONAS


def check_password_policy(password: str, email: str | None = None) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one letter and one number")
    if email and password.lower() == email.lower():
        raise ValueError("Password must not be the same as the email")
    return password


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str | None = None
    role: str = DEFAULT_PERSONA  # the persona chosen at sign-up; it never grants permissions

    @field_validator("password")
    @classmethod
    def password_policy(cls, v: str) -> str:
        return check_password_policy(v)

    @field_validator("role")
    @classmethod
    def role_must_be_self_registrable(cls, v: str) -> str:
        if v not in SELF_REGISTER_PERSONAS:
            raise ValueError(f"role must be one of {SELF_REGISTER_PERSONAS}")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None
    role: str
    persona: str | None = None
    is_demo: bool = False
    is_active: bool
    created_at: datetime
    role_label: str = ""
    level: int = 0
    permissions: list[str] = []
    port_scope: list[str] | None = None
    role_summary: str = ""


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PersonaOut(BaseModel):
    key: str
    label: str
    description: str
    focus: list[str]


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def password_policy(cls, v: str) -> str:
        return check_password_policy(v)


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    persona: str | None = None

    @field_validator("persona")
    @classmethod
    def persona_must_be_known(cls, v: str | None) -> str | None:
        if v is not None and v not in SELF_REGISTER_PERSONAS:
            raise ValueError(f"persona must be one of {SELF_REGISTER_PERSONAS}")
        return v
