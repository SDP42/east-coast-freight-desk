from datetime import date

from sqlalchemy import Date, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PortActivity(Base):
    """Daily dry-bulk port calls and AIS-estimated tonnes per port (IMF PortWatch).
    Tonnes are modelled estimates, not official port statistics."""

    __tablename__ = "port_activity"
    __table_args__ = (UniqueConstraint("port_name", "activity_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    port_name: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    activity_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    dry_bulk_calls: Mapped[int] = mapped_column(Integer, default=0)
    dry_bulk_import_t: Mapped[int] = mapped_column(Integer, default=0)
    dry_bulk_export_t: Mapped[int] = mapped_column(Integer, default=0)


class ChokepointTransit(Base):
    """Daily dry-bulk vessel transits and capacity through a maritime chokepoint (IMF PortWatch)."""

    __tablename__ = "chokepoint_transits"
    __table_args__ = (UniqueConstraint("chokepoint", "transit_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chokepoint: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    transit_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    dry_bulk_transits: Mapped[int] = mapped_column(Integer, default=0)
    dry_bulk_capacity_dwt: Mapped[int] = mapped_column(Integer, default=0)


class HaldiaCoalCall(Base):
    """A coal vessel (coking or PCI) named in SMP Kolkata's Haldia Dock Complex daily
    'morning position' reports. One row per vessel id, keeping the fullest record."""

    __tablename__ = "haldia_coal_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vessel_id: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    vessel_name: Mapped[str] = mapped_column(String(80), nullable=False)
    first_report_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    loa_m: Mapped[float | None] = mapped_column(Numeric(6, 2))
    expected_draft_m: Mapped[float | None] = mapped_column(Numeric(4, 2))
    cargo: Mapped[str] = mapped_column(String(20), nullable=False)
    tonnage_t: Mapped[int | None] = mapped_column(Integer)
    importer_group: Mapped[str] = mapped_column(String(20), nullable=False)
    origin_port: Mapped[str | None] = mapped_column(String(40))
