"""Import every model module here so `Base.metadata` is fully populated —
required for Alembic's autogenerate to see all tables."""

from app.models.disruption import DisruptionEvent
from app.models.fixture import Fixture
from app.models.freight import FreightRate
from app.models.port import Berth, Port
from app.models.route import Route
from app.models.trade import TradeVolume
from app.models.user import User
from app.models.vessel import Vessel, VesselClass

__all__ = [
    "DisruptionEvent",
    "Fixture",
    "FreightRate",
    "Berth",
    "Port",
    "Route",
    "TradeVolume",
    "User",
    "Vessel",
    "VesselClass",
]
