"""Runs ARIMA and XGBoost through the same walk-forward splits so their
errors are paired (required for the Wilcoxon signed-rank test and for
computing honest inverse-RMSE ensemble weights) — adapts Baghel (2025)'s
validated ARIMA+XGBoost methodology to our daily-data walk-forward setup."""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

from app.ml.arima_model import rmse as calc_rmse
from app.ml.ensemble import EnsembleWeights, combine_forecasts, compute_inverse_rmse_weights
from app.ml.xgboost_model import fit_xgboost, forecast_recursive


@dataclass
class ModelMetrics:
    rmse: float
    mae: float
    mape: float


@dataclass
class PairedBacktestReport:
    horizon: int
    n_splits: int
    actuals: list[float] = field(default_factory=list)
    arima_abs_errors: list[float] = field(default_factory=list)
    xgb_abs_errors: list[float] = field(default_factory=list)
    hybrid_abs_errors: list[float] = field(default_factory=list)

    def metrics_for(self, errors_source: str) -> ModelMetrics:
        errors = {"arima": self.arima_abs_errors, "xgb": self.xgb_abs_errors, "hybrid": self.hybrid_abs_errors}[errors_source]
        arr, actual_arr = np.array(errors), np.array(self.actuals)
        mask = actual_arr != 0
        mape = float(np.mean(arr[mask] / np.abs(actual_arr[mask])) * 100) if mask.any() else float("nan")
        return ModelMetrics(rmse=float(np.sqrt(np.mean(arr**2))), mae=float(np.mean(arr)), mape=mape)


def paired_walk_forward_backtest(
    series: pd.Series,
    arima_order: tuple[int, int, int],
    xgb_params: dict,
    exogenous: dict[str, pd.Series] | None,
    horizon: int = 7,
    n_splits: int = 5,
    min_train_size: int = 200,
) -> tuple[PairedBacktestReport, EnsembleWeights]:
    n = len(series)
    usable_range = n - min_train_size - horizon
    step = max(1, usable_range // n_splits)

    report = PairedBacktestReport(horizon=horizon, n_splits=n_splits)
    arima_rmses, xgb_rmses = [], []

    for i in range(n_splits):
        train_end_idx = min_train_size + i * step
        test_end_idx = train_end_idx + horizon
        if test_end_idx > n:
            break

        train = series.iloc[:train_end_idx]
        actual = series.iloc[train_end_idx:test_end_idx].to_numpy()

        arima_fitted = ARIMA(train, order=arima_order).fit()
        arima_pred = arima_fitted.forecast(steps=horizon).to_numpy()

        # NOT truncated to <= train_end: our exogenous datasets (e.g. FRED's
        # S&P 500 series only covers ~2016 onward) have coverage gaps relative
        # to our 2012-2019 freight-rate history that are a data-availability
        # limitation, not real information leakage — per-row leakage is
        # already prevented inside build_feature_frame's shift(1). Truncating
        # here as well previously wiped out S&P 500 entirely for any split
        # ending before 2016, silently training XGBoost on zero rows (the
        # "Empty dataset at worker" bug caught in Section 6 testing).
        split_exog = exogenous or {}
        xgb_fit = fit_xgboost(train, xgb_params, split_exog)
        xgb_pred = forecast_recursive(xgb_fit, train, split_exog, horizon)

        split_arima_rmse = calc_rmse(actual, arima_pred)
        split_xgb_rmse = calc_rmse(actual, xgb_pred)
        arima_rmses.append(split_arima_rmse)
        xgb_rmses.append(split_xgb_rmse)

        weights = compute_inverse_rmse_weights(split_arima_rmse, split_xgb_rmse)
        hybrid_pred = combine_forecasts(arima_pred, xgb_pred, weights)

        report.actuals.extend(actual.tolist())
        report.arima_abs_errors.extend(np.abs(actual - arima_pred).tolist())
        report.xgb_abs_errors.extend(np.abs(actual - xgb_pred).tolist())
        report.hybrid_abs_errors.extend(np.abs(actual - hybrid_pred).tolist())

    overall_weights = compute_inverse_rmse_weights(float(np.mean(arima_rmses)), float(np.mean(xgb_rmses)))
    return report, overall_weights
