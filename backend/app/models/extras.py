from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CycloneExposure(Base):
    """Historical cyclone exposure per destination port and calendar month, derived from IBTrACS
    North Indian Ocean best tracks (1990-2025): the share of days with a tropical storm (>=34 kt)
    centred within 400 km of the port, and storms per year."""

    __tablename__ = "cyclone_exposure"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    port_name: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    storm_day_prob: Mapped[float] = mapped_column(Numeric(7, 5), nullable=False)
    severe_day_prob: Mapped[float] = mapped_column(Numeric(7, 5), nullable=False)
    storms_per_year: Mapped[float] = mapped_column(Numeric(7, 4), nullable=False)
    years: Mapped[int] = mapped_column(Integer, nullable=False)


class LedgerEntry(Base):
    """Hash-chained fixture ledger: every entry stores the SHA-256 of its own fields plus the previous
    entry's hash, so any later edit or deletion breaks the chain and is detectable."""

    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    fixture_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    vessel_name: Mapped[str] = mapped_column(String(120), nullable=False)
    origin_country: Mapped[str] = mapped_column(String(60), nullable=False)
    destination_port: Mapped[str] = mapped_column(String(80), nullable=False)
    cargo_tonnes: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    charter_type: Mapped[str] = mapped_column(String(20), nullable=False)
    rate_usd_per_tonne: Mapped[float | None] = mapped_column(Numeric(10, 3))
    notes: Mapped[str | None] = mapped_column(Text)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    param_a: Mapped[str | None] = mapped_column(String(60))
    param_b: Mapped[str | None] = mapped_column(String(60))
    threshold: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    webhook_url: Mapped[str | None] = mapped_column(String(300))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_fired_at: Mapped[datetime | None] = mapped_column(DateTime)


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("alert_rules.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    fired_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    message: Mapped[str] = mapped_column(Text, nullable=False)
    delivery: Mapped[str] = mapped_column(String(120), default="in_app")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)


class ModelRun(Base):
    """One retraining run of a forecast model, recorded for the monitoring history."""

    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    index_name: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    trigger: Mapped[str] = mapped_column(String(20), nullable=False)
    order: Mapped[str] = mapped_column(String(20), nullable=False)
    train_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    train_end: Mapped[date] = mapped_column(Date, nullable=False)
    holdout_mape: Mapped[float | None] = mapped_column(Numeric(8, 4))
    drift_before: Mapped[bool] = mapped_column(Boolean, default=False)
