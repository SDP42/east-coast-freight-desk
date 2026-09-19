from app.api.deps import require
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.market import HistoryPoint, RegionBoard, TickerItem
from app.services.market import get_history, get_region_boards, get_ticker_values

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


@router.get("/history/{index_name}", response_model=list[HistoryPoint])
def history(index_name: str, limit: int = Query(default=500, ge=2, le=5000), db: Session = Depends(get_db)) -> list[HistoryPoint]:
    rows = get_history(db, index_name.upper(), limit)
    if not rows:
        raise HTTPException(status_code=404, detail=f"No data for '{index_name}'")
    return [HistoryPoint(date=d, value=v) for d, v in rows]


@router.get("/regions", response_model=list[RegionBoard])
def regions(db: Session = Depends(get_db)) -> list[dict]:
    return get_region_boards(db)


@router.get("/pulse")
def pulse(db: Session = Depends(get_db), _=Depends(require("market:read"))) -> dict:
    from app.services.pulse import market_pulse
    return market_pulse(db)
