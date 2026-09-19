"""Fast ARIMA forecast for interactive use (the assistant). Fits a fixed ARIMA(2,1,2) on the last
~3 years of the series (the order the AIC grid typically selects for these indices) and caches the result per
series end date, so a chat question does not pay for the full order search."""

from dataclasses import dataclass

import pandas as pd
from sqlalchemy.orm import Session
from statsmodels.tsa.arima.model import ARIMA

from app.services.freight_data import is_monthly, load_series

_cache: dict[tuple[str, str, int], "QuickForecast"] = {}


@dataclass
class QuickForecast:
    index_name: str
    last_date: str
    last_value: float
    horizon: int
    forecast_end: float
    change_pct: float
    lower: float
    upper: float


def quick_forecast(db: Session, index_name: str, horizon: int) -> QuickForecast | None:
    series = load_series(db, index_name)
    monthly = is_monthly(series)
    if series.empty or len(series) < (60 if monthly else 200):
        return None
    key = (index_name, str(series.index[-1].date()), horizon)
    if key in _cache:
        return _cache[key]
    s = series.iloc[-(240 if monthly else 800):]
    fit = ARIMA(s, order=(2, 1, 2)).fit()
    res = fit.get_forecast(horizon)
    mean = float(res.predicted_mean.iloc[-1])
    ci = res.conf_int(alpha=0.05).iloc[-1]
    last = float(s.iloc[-1])
    out = QuickForecast(index_name, str(pd.Timestamp(s.index[-1]).date()), last, horizon, mean, (mean - last) / last * 100, float(ci.iloc[0]), float(ci.iloc[1]))
    _cache[key] = out
    return out
