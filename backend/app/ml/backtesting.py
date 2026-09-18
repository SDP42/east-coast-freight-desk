"""Walk-forward backtesting — trains on an expanding window and evaluates on
the next `horizon` unseen points, repeated across multiple splits, rather than
a single train/test split. This is what lets us honestly report accuracy
instead of cherry-picking one lucky split, and is the same evaluation
discipline used in both reviewed papers (Baghel 2025; Sahu & Patil 2017)."""

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.ml.arima_model import mae as calc_mae
from app.ml.arima_model import mape as calc_mape
from app.ml.arima_model import rmse as calc_rmse


@dataclass
class SplitResult:
    split_index: int
    train_end: str
    rmse: float
    mae: float
    mape: float


@dataclass
class BacktestReport:
    horizon: int
    n_splits: int
    splits: list[SplitResult] = field(default_factory=list)

    @property
    def mean_rmse(self) -> float:
        return float(np.mean([s.rmse for s in self.splits])) if self.splits else float("nan")

    @property
    def mean_mae(self) -> float:
        return float(np.mean([s.mae for s in self.splits])) if self.splits else float("nan")

    @property
    def mean_mape(self) -> float:
        return float(np.mean([s.mape for s in self.splits])) if self.splits else float("nan")


def walk_forward_backtest(
    series: pd.Series,
    fit_predict_fn: Callable[[pd.Series, int], np.ndarray],
    horizon: int = 7,
    n_splits: int = 5,
    min_train_size: int = 180,
) -> BacktestReport:
    """`fit_predict_fn(train_series, horizon)` must return an array of
    `horizon` forecast values. Splits are spaced evenly across the tail of the
    series so each one trains on an expanding window and tests on the next
    `horizon` points, never touching future data."""
    n = len(series)
    usable_range = n - min_train_size - horizon
    if usable_range <= 0:
        raise ValueError(f"Series too short ({n} points) for {n_splits} splits of horizon {horizon}")

    step = max(1, usable_range // n_splits)
    report = BacktestReport(horizon=horizon, n_splits=n_splits)

    for i in range(n_splits):
        train_end_idx = min_train_size + i * step
        test_end_idx = train_end_idx + horizon
        if test_end_idx > n:
            break

        train = series.iloc[:train_end_idx]
        actual = series.iloc[train_end_idx:test_end_idx].to_numpy()

        predicted = fit_predict_fn(train, horizon)

        report.splits.append(
            SplitResult(
                split_index=i,
                train_end=str(train.index[-1].date()),
                rmse=calc_rmse(actual, predicted),
                mae=calc_mae(actual, predicted),
                mape=calc_mape(actual, predicted),
            )
        )

    return report
