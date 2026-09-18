from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.market import TickerItem
from app.services.market import get_ticker_values

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/ticker", response_model=list[TickerItem])
def get_ticker(db: Session = Depends(get_db)) -> list[TickerItem]:
    values = get_ticker_values(db)
    items = []
    for v in values:
        change = round(v.value - v.prev_value, 4) if v.prev_value is not None else None
        change_pct = round((change / v.prev_value) * 100, 3) if change is not None and v.prev_value else None
        items.append(
            TickerItem(
                index_name=v.index_name, label=v.label, unit=v.unit,
                date=v.date, value=round(v.value, 2),
                prev_date=v.prev_date, prev_value=round(v.prev_value, 2) if v.prev_value is not None else None,
                change=change, change_pct=change_pct,
            )
        )
    return items
