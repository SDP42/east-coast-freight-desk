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


# Region boards. Only series we actually hold real data for are listed; regions
# without a free real series are returned empty with an explicit note rather
# than filled with invented numbers.
REGION_BOARDS = [
    {"region": "Global Freight", "note": "Baltic Exchange sub-indices (Mendeley dataset, ends Jul 2019)",
     "series": [("BDI", "Baltic Dry Index", "points"), ("BCI", "Capesize", "points"), ("BPI", "Panamax", "points"),
                ("BSI", "Supramax", "points"), ("BHSI", "Handysize", "points")]},
    {"region": "Australia", "note": "Newcastle coal (World Bank) and the Australian dollar (FRED)",
     "series": [("COAL_AUS", "Australian coal", "usd/t"), ("AUD", "AUD / USD", "usd")]},
    {"region": "Southern Africa / Mozambique", "note": "South African coal is the nearest real price proxy for Mozambique",
     "series": [("COAL_ZA", "South African coal", "usd/t"), ("ZAR", "ZAR per USD", "zar")]},
    {"region": "United States", "note": "S&P 500 was the strongest BDI predictor in Kim et al. (2025)",
     "series": [("SP500", "S&P 500", "pts"), ("DXY", "US Dollar Index", "pts")]},
    {"region": "India (destination)", "note": "Freight is USD-quoted; Indian budgets are INR",
     "series": [("INR", "INR per USD", "inr")]},
    {"region": "Indonesia", "note": "No free real price series ingested for this origin", "series": []},
    {"region": "Russia", "note": "No free real price series ingested for this origin", "series": []},
]


def get_history(db: Session, index_name: str, limit: int) -> list[tuple]:
    rows = (
        db.query(FreightRate.rate_date, FreightRate.value)
        .filter(FreightRate.index_name == index_name)
        .order_by(FreightRate.rate_date.desc())
        .limit(limit)
        .all()
    )
    return [(d, float(v)) for d, v in reversed(rows)]


def get_region_boards(db: Session, spark_points: int = 40) -> list[dict]:
    boards = []
    for board in REGION_BOARDS:
        series_out = []
        for index_name, label, unit in board["series"]:
            hist = get_history(db, index_name, spark_points + 1)
            if len(hist) < 2:
                continue
            latest_date, latest = hist[-1]
            prev = hist[-2][1]
            series_out.append({
                "index_name": index_name, "label": label, "unit": unit,
                "date": latest_date, "value": round(latest, 4),
                "change_pct": round((latest - prev) / prev * 100, 3) if prev else None,
                "spark": [round(v, 4) for _, v in hist[1:]],
            })
        boards.append({"region": board["region"], "note": board["note"], "series": series_out})
    return boards


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
