"""Feature engineering for the XGBoost model: lag features, rolling-window statistics and calendar features, with public
macro series (dollar index, oil, coal PPI) as optional extras. Lags and windows are counted in steps of the series, so a
monthly series uses monthly lags (1, 2, 3, 6, 12) and a daily one uses daily lags (1, 2, 3, 7, 14)."""

import pandas as pd

LAG_DAYS = (1, 2, 3, 7, 14)
ROLLING_WINDOWS = (7, 30)


def build_feature_frame(target: pd.Series, exogenous: dict[str, pd.Series] | None = None) -> pd.DataFrame:
    """`target` is the series being forecast (e.g. BDI), date-indexed.
    `exogenous` maps feature name -> date-indexed series (e.g. {"sp500": ...,
    "dxy": ..., "coal_aus": ...}), reindexed and forward-filled onto the
    target's index since these series don't publish on identical calendars."""
    df = pd.DataFrame({"y": target})
    monthly = len(target) > 3 and float(pd.Series(target.index).diff().dt.days.median()) > 20
    lags, windows = ((1, 2, 3, 6, 12), (3, 12)) if monthly else (LAG_DAYS, ROLLING_WINDOWS)

    for lag in lags:
        df[f"lag_{lag}"] = target.shift(lag)

    for window in windows:
        df[f"rolling_mean_{window}"] = target.shift(1).rolling(window).mean()
        df[f"rolling_std_{window}"] = target.shift(1).rolling(window).std()

    df["month"] = df.index.month
    if not monthly:
        df["day_of_week"] = df.index.dayofweek
    df["year"] = df.index.year

    if exogenous:
        for name, series in exogenous.items():
            # Some exogenous series (e.g. S&P 500 from FRED) start later than
            # our freight-rate history (2016 vs. 2012). Reindexing straight
            # onto df.index BEFORE filling is a bug: if df.index predates the
            # series entirely, there is nothing left to ffill/bfill from and
            # every value stays NaN — dropna() then wipes the whole early
            # training set, and XGBoost silently trains on zero rows (a real
            # bug caught in Section 6 testing, confirmed via "Empty dataset at
            # worker" warnings). Fix: fill on the UNION of both indexes first
            # (so the series' own real values are still present to fill from),
            # then slice down to df.index. bfill means the earliest available
            # reading is used for the pre-history period — a minor, documented
            # bias, not lookahead into genuinely future data.
            union_index = df.index.union(series.index)
            filled = series.reindex(union_index).ffill().bfill()
            aligned = filled.reindex(df.index).shift(1)
            df[f"exog_{name}"] = aligned

    return df


def feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c != "y"]
