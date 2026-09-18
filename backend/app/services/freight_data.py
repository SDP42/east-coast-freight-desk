import pandas as pd
from sqlalchemy.orm import Session

from app.models import FreightRate


def load_series(db: Session, index_name: str) -> pd.Series:
    """Load a market series (BDI/BCI/BPI/BSI/BHSI or a commodity price series)
    as a date-indexed pandas Series, sorted chronologically. Returns an empty
    Series if the index_name has no data."""
    rows = (
        db.query(FreightRate.rate_date, FreightRate.value)
        .filter(FreightRate.index_name == index_name)
        .order_by(FreightRate.rate_date)
        .all()
    )
    if not rows:
        return pd.Series(dtype="float64")

    dates, values = zip(*rows)
    series = pd.Series([float(v) for v in values], index=pd.DatetimeIndex(dates), name=index_name)
    series = series[~series.index.duplicated(keep="last")]
    return series.asfreq("D").interpolate(limit_direction="both")


def available_index_names(db: Session) -> list[str]:
    rows = db.query(FreightRate.index_name).distinct().all()
    return sorted(r[0] for r in rows)
