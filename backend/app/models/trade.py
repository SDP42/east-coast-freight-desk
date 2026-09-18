from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class TradeVolume(Base):
    """Annual/monthly coal import volumes by origin country and destination
    port — demand-side signal for the forecasting and recommendation models,
    sourced from DGCIS/UN Comtrade/WITS per the ingestion pipeline (Section 3)."""

    __tablename__ = "trade_volumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    period_start: Mapped[str] = mapped_column(String(10), nullable=False)
    """ISO date string for the start of the reporting period (year or month)."""
    period_type: Mapped[str] = mapped_column(String(10), default="annual")
    """'annual' or 'monthly'."""

    origin_country: Mapped[str] = mapped_column(String(80), nullable=False)
    destination_port_id: Mapped[int | None] = mapped_column(ForeignKey("ports.id"))

    commodity: Mapped[str] = mapped_column(String(60), nullable=False)
    """'coking_coal', 'thermal_coal', 'total_coal', etc."""

    tonnes: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    source: Mapped[str | None] = mapped_column(String(120))
