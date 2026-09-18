from datetime import date

from pydantic import BaseModel


class TickerItem(BaseModel):
    index_name: str
    label: str
    unit: str
    date: date
    value: float
    prev_date: date | None
    prev_value: float | None
    change: float | None
    change_pct: float | None
