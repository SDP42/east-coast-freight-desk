from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import haldia

router = APIRouter(prefix="/haldia", tags=["haldia"])


@router.get("/summary")
def haldia_summary(db: Session = Depends(get_db)) -> dict:
    """Public: real observed coal-vessel statistics at Haldia plus port facts (used by the landing page)."""
    return haldia.summary(db)
