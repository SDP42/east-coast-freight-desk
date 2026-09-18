from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.personas import DEFAULT_PERSONA, SELF_REGISTER_PERSONAS


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None
    role: str = DEFAULT_PERSONA

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
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PersonaOut(BaseModel):
    key: str
    label: str
    description: str
    focus: list[str]
