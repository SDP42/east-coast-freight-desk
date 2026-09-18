"""Real latest-known-value ticker data — replaces the frontend's earlier
simulated random-walk ticker with genuine historical data pulled straight
from the database. Honesty note: Baltic Exchange rates are a paid feed, so
this is the latest *ingested* value with its real date and real day-over-day
change, not a literal real-time tick — the frontend surfaces the date
explicitly rather than implying a live market feed we don't have access to.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import FreightRate

TICKER_SERIES = [
    ("BDI", "Baltic Dry Index", "points"),
    ("BCI", "Capesize", "points"),
    ("BPI", "Panamax", "points"),
    ("BSI", "Supramax", "points"),
    ("BHSI", "Handysize", "points"),
    ("COAL_AUS", "Australian Coal", "usd/t"),
    ("SP500", "S&P 500", "usd"),
    ("DXY", "US Dollar Index", "pts"),
]


@dataclass
class TickerValue:
    index_name: str
    label: str
    unit: str
    date: object
    value: float
    prev_date: object | None
    prev_value: float | None


def get_ticker_values(db: Session) -> list[TickerValue]:
    results = []
    for index_name, label, unit in TICKER_SERIES:
        rows = (
            db.query(FreightRate.rate_date, FreightRate.value)
            .filter(FreightRate.index_name == index_name)
            .order_by(FreightRate.rate_date.desc())
            .limit(2)
            .all()
        )
        if not rows:
            continue

        latest_date, latest_value = rows[0]
        prev_date, prev_value = rows[1] if len(rows) > 1 else (None, None)

        results.append(
            TickerValue(
                index_name=index_name,
                label=label,
                unit=unit,
                date=latest_date,
                value=float(latest_value),
                prev_date=prev_date,
                prev_value=float(prev_value) if prev_value is not None else None,
            )
        )
    return results
