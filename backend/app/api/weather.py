from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require
from app.core.permissions import port_scope
from app.db.session import get_db
from app.models import User
from app.services import weather

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/ports")
def ports(db: Session = Depends(get_db), user: User = Depends(require("ports:read"))) -> dict:
    """Live weather and sea state at the discharge ports (a port officer sees only their assigned ports)."""
    return weather.port_weather(db, port_scope(user))
