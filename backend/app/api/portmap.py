from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.portmap import build_map_overview

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/overview")
def overview(db: Session = Depends(get_db)) -> dict:
    """Ports (real), sea lanes and simulated vessels for the map view."""
    return build_map_overview(db)
