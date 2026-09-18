from datetime import date

from pydantic import BaseModel


class ForecastPoint(BaseModel):
    date: date
    value: float
    lower_ci: float
    upper_ci: float


class BacktestSplitMetric(BaseModel):
    split_index: int
    train_end: date
    rmse: float
    mae: float
    mape: float


class ForecastResponse(BaseModel):
    index_name: str
    horizon: int
    model: str
    order: tuple[int, int, int]
    is_stationary: bool
    adf_pvalue: float
    forecast: list[ForecastPoint]
    backtest_mean_rmse: float
    backtest_mean_mae: float
    backtest_mean_mape: float
    backtest_splits: list[BacktestSplitMetric]
