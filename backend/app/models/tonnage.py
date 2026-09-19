from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class OpenTonnage(Base):
    """A ship a broker has offered as open (available) at a port on a date. Supplied by the user, never scraped."""

    __tablename__ = "open_tonnage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    vessel_name: Mapped[str] = mapped_column(String(120))
    imo: Mapped[str | None] = mapped_column(String(12))
    dwt: Mapped[int] = mapped_column(Integer)
    loa_m: Mapped[float | None] = mapped_column(Numeric(6, 1))
    beam_m: Mapped[float | None] = mapped_column(Numeric(5, 1))
    draft_m: Mapped[float | None] = mapped_column(Numeric(5, 2))
    open_port: Mapped[str] = mapped_column(String(80))
    open_date: Mapped[date] = mapped_column(Date)
    speed_knots: Mapped[float | None] = mapped_column(Numeric(4, 1))
    broker: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str] = mapped_column(Text, default="")
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
