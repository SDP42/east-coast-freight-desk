from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Port(Base):
    """An East Coast (or origin-country) port, with the physical constraints that
    drive vessel eligibility — this is the seed data for the Port–Vessel
    Compatibility Engine built in Section 7, sourced from our own compiled
    research (Table 1: draft/LOA/beam/tidal data for all 7 East Coast ports)."""

    __tablename__ = "ports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    unlocode: Mapped[str | None] = mapped_column(String(10), unique=True)
    country: Mapped[str] = mapped_column(String(80), nullable=False)
    is_destination: Mapped[bool] = mapped_column(Boolean, default=True)
    """True for India East Coast discharge ports; False for foreign loading ports
    (Australia, US, Mozambique, Russia, Indonesia)."""

    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6))

    max_draft_m: Mapped[float | None] = mapped_column(Numeric(5, 2))
    max_loa_m: Mapped[float | None] = mapped_column(Numeric(6, 2))
    max_beam_m: Mapped[float | None] = mapped_column(Numeric(5, 2))

    tidal_restricted: Mapped[bool] = mapped_column(Boolean, default=False)
    max_vessels_per_tide: Mapped[int | None] = mapped_column(Integer)

    annual_capacity_mtpa: Mapped[float | None] = mapped_column(Numeric(8, 2))
    avg_turnaround_hours: Mapped[float | None] = mapped_column(Numeric(6, 2))

    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(Text)
    """Citation for the constraint figures, e.g. reference numbers from the
    research compendium."""

    berths: Mapped[list["Berth"]] = relationship(back_populates="port", cascade="all, delete-orphan")


class Berth(Base):
    """A specific berth within a port — finer-grained than the port-wide max
    draft/LOA, since (e.g.) Paradip's Capesize-capable outer berth and its
    14.5 m coal berths are very different in practice."""

    __tablename__ = "berths"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    port_id: Mapped[int] = mapped_column(ForeignKey("ports.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    draft_m: Mapped[float | None] = mapped_column(Numeric(5, 2))
    loa_m: Mapped[float | None] = mapped_column(Numeric(6, 2))
    beam_m: Mapped[float | None] = mapped_column(Numeric(5, 2))

    cargo_type: Mapped[str | None] = mapped_column(String(60))
    handling_rate_tpd: Mapped[float | None] = mapped_column(Numeric(10, 2))
    """Tonnes-per-day handling rate for this berth, where published."""

    port: Mapped["Port"] = relationship(back_populates="berths")
