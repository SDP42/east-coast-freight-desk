from datetime import date

from pydantic import BaseModel


class HistoryPoint(BaseModel):
    date: date
    value: float


class RegionSeries(BaseModel):
    index_name: str
    label: str
    unit: str
    date: date
    value: float
    change_pct: float | None
    spark: list[float]


class RegionBoard(BaseModel):
    region: str
    note: str
    series: list[RegionSeries]


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
