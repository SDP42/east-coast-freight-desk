"""Real latest-known-value ticker data — replaces the frontend's earlier
simulated random-walk ticker with genuine historical data pulled straight
from the database. Honesty note: there is no free live freight feed, so
this is the latest *ingested* value with its real date and real day-over-day
change, not a literal real-time tick — the frontend surfaces the date
explicitly rather than implying a live market feed we don't have access to.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import FreightRate

TICKER_SERIES = [
    ("OCEAN_GULF_JAPAN", "Grain ocean rate, Gulf-Japan", "usd/t"),
    ("OCEAN_PNW_JAPAN", "Grain ocean rate, PNW-Japan", "usd/t"),
    ("DEEPSEA_PPI", "Deep-sea freight PPI", "pts"),
    ("COAL_PPI", "Coal price index (PPI)", "pts"),
    ("BRENT", "Brent crude", "usd/bbl"),
    ("INR", "INR per USD", "inr"),
    ("DXY", "US Dollar Index", "pts"),
]


# Region boards. Only series we hold real, public-domain data for are listed; regions without one are returned empty with an
# explicit note rather than filled with invented numbers.
REGION_BOARDS = [
    {"region": "Freight", "note": "USDA grain ocean rates (a dry-bulk proxy) and the US BLS deep-sea freight index; monthly, to 2026",
     "series": [("OCEAN_GULF_JAPAN", "Grain ocean rate, Gulf to Japan", "usd/t"), ("OCEAN_PNW_JAPAN", "Grain ocean rate, PNW to Japan", "usd/t"), ("DEEPSEA_PPI", "Deep-sea freight PPI", "pts")]},
    {"region": "Fuel and coal", "note": "US EIA Brent crude (daily, a bunker-fuel proxy) and the US BLS coal price index (monthly)",
     "series": [("BRENT", "Brent crude", "usd/bbl"), ("COAL_PPI", "Coal price index (PPI)", "pts")]},
    {"region": "Australia", "note": "Federal Reserve exchange rate", "series": [("AUD", "AUD / USD", "usd")]},
    {"region": "Southern Africa / Mozambique", "note": "Federal Reserve exchange rate for the rand, the nearest proxy for Mozambique", "series": [("ZAR", "ZAR per USD", "zar")]},
    {"region": "United States", "note": "Federal Reserve broad dollar index", "series": [("DXY", "US Dollar Index", "pts")]},
    {"region": "India (destination)", "note": "Freight is USD-quoted; Indian budgets are INR", "series": [("INR", "INR per USD", "inr")]},
    {"region": "Indonesia", "note": "No free public-domain price series for this origin", "series": []},
    {"region": "Russia", "note": "No free public-domain price series for this origin", "series": []},
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
