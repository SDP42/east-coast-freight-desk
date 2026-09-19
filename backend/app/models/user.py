from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(120))

    role: Mapped[str] = mapped_column(String(30), default="viewer")
    """Authority role (see app.core.permissions.ROLES): admin, finance_head, procurement_manager,
    chartering_analyst, port_ops or viewer. Assigned by an administrator; never chosen at sign-up."""

    persona: Mapped[str | None] = mapped_column(String(30))
    """Interface persona the user picked at sign-up. Shapes greetings and shortcuts only, never permissions."""

    assigned_ports: Mapped[str | None] = mapped_column(Text)
    """JSON list of port names for port-scoped roles (port_ops)."""

    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
