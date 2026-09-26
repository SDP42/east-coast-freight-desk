from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.services import fx

router = APIRouter(prefix="/fx", tags=["fx"])


@router.get("/rate")
def rate(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    """Today's USD to INR rate (ECB reference rate), with its date, source and the rate the cost model uses."""
    return fx.live_rate(db)


@router.get("/convert")
def convert(amount: float = Query(..., ge=0, le=1e12), from_currency: str = Query("USD", alias="from"),
            db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    r = fx.live_rate(db)
    if not r.get("rate"):
        raise HTTPException(status_code=503, detail="No exchange rate is available right now")
    try:
        out = fx.convert(amount, from_currency, r["rate"])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {**out, "rate_date": r["rate_date"], "source": r["source"], "live": r["live"]}
