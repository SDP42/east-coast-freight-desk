import pandas as pd
from sqlalchemy.orm import Session

from app.models import FreightRate


# The primary freight series is the USDA monthly grain ocean rate (US government, public domain). Monthly series keep their own
# frequency: turning them into daily data would invent thousands of near-identical points and overstate every test.
PRIMARY_INDEX = "OCEAN_GULF_JAPAN"
MONTHLY = {"OCEAN_GULF_JAPAN", "OCEAN_PNW_JAPAN", "DEEPSEA_PPI", "COAL_PPI"}


def is_monthly(series: pd.Series) -> bool:
    return len(series) > 3 and float(pd.Series(series.index).diff().dt.days.median()) > 20


def step_offset(series: pd.Series) -> pd.DateOffset:
    """One step of the series: a month for monthly data, a day otherwise."""
    return pd.DateOffset(months=1) if is_monthly(series) else pd.DateOffset(days=1)


def load_series(db: Session, index_name: str) -> pd.Series:
    """Load a market series as a date-indexed pandas Series, sorted chronologically (daily series are filled to every
    calendar day; monthly series stay monthly). Returns an empty Series if the index_name has no data."""
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
    if index_name in MONTHLY:
        series.index = pd.DatetimeIndex(series.index).to_period("M").to_timestamp()
        m = series.asfreq("MS")
        # Keep only the stretch after the last long gap (more than six missing months), then fill the short gaps, so no long
        # run of values is invented and the monthly frequency is preserved for the models.
        na = m.isna().astype(int)
        run = na.groupby((na != na.shift()).cumsum()).transform("sum") * na
        long_gap = run[run > 6]
        if not long_gap.empty:
            m = m.loc[long_gap.index[-1] + pd.DateOffset(months=1):]
        return m.interpolate(limit_direction="both")
    return series.asfreq("D").interpolate(limit_direction="both")


def available_index_names(db: Session) -> list[str]:
    rows = db.query(FreightRate.index_name).distinct().all()
    return sorted(r[0] for r in rows)
