import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from statsmodels.tsa.arima.model import ARIMA

from app.core.cache import cached, data_version
from app.db.session import get_db
from app.ml.arima_model import fit_best_arima, forecast, forecast_with_ci
from app.ml.backtesting import walk_forward_backtest
from app.ml.ensemble import wilcoxon_significance
from app.ml.ensemble_backtest import paired_walk_forward_backtest
from app.ml.xgboost_model import compute_shap_values, fit_xgboost, forecast_recursive, select_best_params
from app.schemas.ensemble import (
    EnsembleForecastPoint,
    EnsembleForecastResponse,
    ModelMetricOut,
    ShapFeature,
    SignificanceOut,
)
from app.schemas.forecast import BacktestSplitMetric, ForecastPoint, ForecastResponse
from app.services.freight_data import available_index_names, load_series

router = APIRouter(prefix="/forecast", tags=["forecast"])

EXOGENOUS_CANDIDATES = ["SP500", "DXY", "COAL_AUS", "COAL_ZA"]


@router.get("/indices", response_model=list[str])
def list_indices(db: Session = Depends(get_db)) -> list[str]:
    return available_index_names(db)


@router.get("/{index_name}", response_model=ForecastResponse)
def get_forecast(
    index_name: str,
    horizon: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
) -> ForecastResponse:
    key = f"forecast:{index_name.upper()}:{horizon}:{data_version(db, index_name.upper())}"
    return ForecastResponse(**cached(key, 6 * 3600, lambda: _compute_forecast(index_name, horizon, db).model_dump(mode="json")))


def _compute_forecast(index_name: str, horizon: int, db: Session) -> ForecastResponse:
    series = load_series(db, index_name.upper())
    if series.empty:
        raise HTTPException(status_code=404, detail=f"No data for index '{index_name}'")
    if len(series) < 200:
        raise HTTPException(status_code=422, detail="Not enough history to fit a reliable ARIMA model")

    best = fit_best_arima(series)

    def fit_predict(train: pd.Series, h: int) -> np.ndarray:
        fitted = ARIMA(train, order=best.order).fit()
        return fitted.forecast(steps=h).to_numpy()

    backtest = walk_forward_backtest(series, fit_predict, horizon=min(horizon, 30), n_splits=5)

    mean, lower, upper = forecast_with_ci(best, horizon)
    forecast_points = [
        ForecastPoint(date=d.date(), value=round(float(v), 2), lower_ci=round(float(lo), 2), upper_ci=round(float(hi), 2))
        for d, v, lo, hi in zip(mean.index, mean.to_numpy(), lower.to_numpy(), upper.to_numpy())
    ]

    return ForecastResponse(
        index_name=index_name.upper(),
        horizon=horizon,
        model="ARIMA",
        order=best.order,
        is_stationary=best.is_stationary,
        adf_pvalue=round(best.adf_pvalue, 6),
        forecast=forecast_points,
        backtest_mean_rmse=round(backtest.mean_rmse, 4),
        backtest_mean_mae=round(backtest.mean_mae, 4),
        backtest_mean_mape=round(backtest.mean_mape, 4),
        backtest_splits=[
            BacktestSplitMetric(
                split_index=s.split_index,
                train_end=pd.to_datetime(s.train_end).date(),
                rmse=round(s.rmse, 4),
                mae=round(s.mae, 4),
                mape=round(s.mape, 4),
            )
            for s in backtest.splits
        ],
    )


@router.get("/{index_name}/ensemble", response_model=EnsembleForecastResponse)
def get_ensemble_forecast(
    index_name: str,
    horizon: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
) -> EnsembleForecastResponse:
    names = [index_name.upper(), *EXOGENOUS_CANDIDATES]
    key = f"ensemble:{index_name.upper()}:{horizon}:{data_version(db, *names)}"
    return EnsembleForecastResponse(**cached(key, 6 * 3600, lambda: _compute_ensemble(index_name, horizon, db).model_dump(mode="json")))


def _compute_ensemble(index_name: str, horizon: int, db: Session) -> EnsembleForecastResponse:
    """ARIMA + XGBoost ensemble with inverse-RMSE weighting and a Wilcoxon
    signed-rank significance test — the validated methodology from Baghel
    (2025, NCI MSc thesis), with S&P 500 / US Dollar Index / coal price
    exogenous features per Kim, Kim & Choi (2025, PLOS ONE)'s SHAP findings."""
    index_name = index_name.upper()
    series = load_series(db, index_name)
    if series.empty:
        raise HTTPException(status_code=404, detail=f"No data for index '{index_name}'")
    if len(series) < 250:
        raise HTTPException(status_code=422, detail="Not enough history to fit a reliable ensemble model")

    exogenous = {}
    for name in EXOGENOUS_CANDIDATES:
        if name == index_name:
            continue
        exog_series = load_series(db, name)
        if not exog_series.empty:
            exogenous[name.lower()] = exog_series

    best_arima = fit_best_arima(series)
    xgb_params = select_best_params(series, exogenous)

    report, weights = paired_walk_forward_backtest(
        series, best_arima.order, xgb_params, exogenous, horizon=horizon, n_splits=5,
    )

    xgb_final = fit_xgboost(series, xgb_params, exogenous)
    arima_forecast_values = forecast(best_arima, horizon).to_numpy()
    xgb_forecast_values = forecast_recursive(xgb_final, series, exogenous, horizon)
    hybrid_forecast_values = weights.arima_weight * arima_forecast_values + weights.xgb_weight * xgb_forecast_values

    future_dates = pd.date_range(start=series.index[-1] + pd.Timedelta(days=1), periods=horizon)

    hybrid_vs_arima = wilcoxon_significance(report.hybrid_abs_errors, report.arima_abs_errors)
    hybrid_vs_xgb = wilcoxon_significance(report.hybrid_abs_errors, report.xgb_abs_errors)

    return EnsembleForecastResponse(
        index_name=index_name,
        horizon=horizon,
        arima_order=best_arima.order,
        xgb_params=xgb_params,
        weights={"arima": round(weights.arima_weight, 4), "xgb": round(weights.xgb_weight, 4)},
        forecast=[
            EnsembleForecastPoint(
                date=d.date(), arima_value=round(float(a), 2), xgb_value=round(float(x), 2), hybrid_value=round(float(h), 2),
            )
            for d, a, x, h in zip(future_dates, arima_forecast_values, xgb_forecast_values, hybrid_forecast_values)
        ],
        arima_metrics=ModelMetricOut(**report.metrics_for("arima").__dict__),
        xgb_metrics=ModelMetricOut(**report.metrics_for("xgb").__dict__),
        hybrid_metrics=ModelMetricOut(**report.metrics_for("hybrid").__dict__),
        top_features=[ShapFeature(**f) for f in compute_shap_values(xgb_final)],
        hybrid_vs_arima=SignificanceOut(**hybrid_vs_arima.__dict__),
        hybrid_vs_xgb=SignificanceOut(**hybrid_vs_xgb.__dict__),
    )
