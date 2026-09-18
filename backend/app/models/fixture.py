from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Fixture(Base):
    """A vessel chartering fixture — either historical (imported by the
    organisation via the Section 14 fixture-ledger upload, to benchmark actual
    decisions against the model's counterfactual recommendation, feature #16
    of the plan) or model-recommended.

    `is_actual=True` rows are the organisation's own historical charters;
    `is_actual=False` rows are recommendations produced by the engine."""

    __tablename__ = "fixtures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    fixture_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id"))
    vessel_class_id: Mapped[int | None] = mapped_column(ForeignKey("vessel_classes.id"))
    vessel_id: Mapped[int | None] = mapped_column(ForeignKey("vessels.id"))

    charter_type: Mapped[str] = mapped_column(String(20), nullable=False)
    """'spot', 'time_charter', or 'coa'."""

    cargo_tonnes: Mapped[float | None] = mapped_column(Numeric(12, 2))
    rate_value: Mapped[float | None] = mapped_column(Numeric(12, 4))
    rate_unit: Mapped[str | None] = mapped_column(String(20))
    """'usd_per_tonne' or 'usd_per_day'."""

    laycan_start: Mapped[date | None] = mapped_column(Date)
    laycan_end: Mapped[date | None] = mapped_column(Date)

    is_actual: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[str | None] = mapped_column(Text)
