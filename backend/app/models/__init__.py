"""Import every model module here so `Base.metadata` is fully populated —
required for Alembic's autogenerate to see all tables."""

from app.models.disruption import DisruptionEvent
from app.models.extras import AlertEvent, AlertRule, CycloneExposure, LedgerEntry, ModelRun
from app.models.fixture import Fixture
from app.models.freight import FreightRate
from app.models.market_activity import ChokepointTransit, HaldiaCoalCall, PortActivity
from app.models.port import Berth, Port
from app.models.route import Route
from app.models.trade import TradeVolume
from app.models.user import User
from app.models.vessel import Vessel, VesselClass

__all__ = [
    "AlertEvent",
    "AlertRule",
    "CycloneExposure",
    "LedgerEntry",
    "ModelRun",
    "ChokepointTransit",
    "PortActivity",
    "DisruptionEvent",
    "Fixture",
    "FreightRate",
    "HaldiaCoalCall",
    "Berth",
    "Port",
    "Route",
    "TradeVolume",
    "User",
    "Vessel",
    "VesselClass",
]
