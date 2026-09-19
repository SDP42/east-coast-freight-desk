from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class FreightRate(Base):
    """Daily freight rate observations — Baltic sub-indices
    (BCI/BPI/BSI/BHSI) plus route-specific $/tonne assessments where
    available. This is the core time-series table the forecasting models
    (Section 5/6) train on.

    Made a TimescaleDB hypertable opportunistically by
    `scripts/enable_timescaledb.py` if the extension is present on the target
    Postgres instance; works as a normal indexed table otherwise, so the schema
    itself has no hard TimescaleDB dependency (kept deployment-portable)."""

    __tablename__ = "freight_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    index_name: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    """A market series identifier: BCI, BPI, BSI, BHSI, ROUTE_SPOT, or a
    commodity price series (e.g. COAL_AUS, COAL_ZA) — one shared time-series
    table for every market signal the forecasting models consume, rather than
    a separate table per series type."""

    value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="points")
    """'points' for freight index values, 'usd_per_tonne' for commodity prices
    or route rates, 'usd_per_day' for TCE rates."""

    route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id"))
    vessel_class_id: Mapped[int | None] = mapped_column(ForeignKey("vessel_classes.id"))

    source: Mapped[str | None] = mapped_column(String(120))
