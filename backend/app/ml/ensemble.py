"""ARIMA + XGBoost ensemble with inverse-RMSE weighting, and a Wilcoxon
signed-rank significance test — both taken directly from the validated
methodology in Baghel (2025, NCI MSc thesis): "We compute inverse-error
weights so lower-error models contribute more: w_m = (1/RMSE_m) /
sum_k(1/RMSE_k)", validated via Wilcoxon signed-rank test against each
standalone model (their result: p=0.016 vs. ARIMA alone)."""

from dataclasses import dataclass

import numpy as np
from scipy.stats import wilcoxon


@dataclass
class EnsembleWeights:
    arima_weight: float
    xgb_weight: float
    arima_rmse: float
    xgb_rmse: float


def compute_inverse_rmse_weights(arima_rmse: float, xgb_rmse: float) -> EnsembleWeights:
    inv_arima, inv_xgb = 1 / max(arima_rmse, 1e-9), 1 / max(xgb_rmse, 1e-9)
    total = inv_arima + inv_xgb
    return EnsembleWeights(
        arima_weight=inv_arima / total,
        xgb_weight=inv_xgb / total,
        arima_rmse=arima_rmse,
        xgb_rmse=xgb_rmse,
    )


def combine_forecasts(arima_forecast: np.ndarray, xgb_forecast: np.ndarray, weights: EnsembleWeights) -> np.ndarray:
    return weights.arima_weight * np.asarray(arima_forecast) + weights.xgb_weight * np.asarray(xgb_forecast)


@dataclass
class SignificanceResult:
    statistic: float
    p_value: float
    n: int
    significant_at_05: bool


def wilcoxon_significance(hybrid_errors: np.ndarray, baseline_errors: np.ndarray) -> SignificanceResult:
    """One-sided test: is the hybrid's absolute error significantly *lower*
    than the baseline's? Mirrors Baghel's exact test setup (scipy.stats.wilcoxon,
    one-sided alternative='less' since the hypothesis is hybrid <= baseline)."""
    hybrid_errors, baseline_errors = np.asarray(hybrid_errors), np.asarray(baseline_errors)
    n = len(hybrid_errors)
    if n < 1 or np.allclose(hybrid_errors, baseline_errors):
        return SignificanceResult(statistic=float("nan"), p_value=1.0, n=n, significant_at_05=False)

    stat, p_value = wilcoxon(hybrid_errors, baseline_errors, alternative="less")
    return SignificanceResult(
        statistic=float(stat), p_value=float(p_value), n=n,
        significant_at_05=p_value < 0.05,
    )
