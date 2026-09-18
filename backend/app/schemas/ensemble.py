from datetime import date

from pydantic import BaseModel


class EnsembleForecastPoint(BaseModel):
    date: date
    arima_value: float
    xgb_value: float
    hybrid_value: float


class ModelMetricOut(BaseModel):
    rmse: float
    mae: float
    mape: float


class ShapFeature(BaseModel):
    feature: str
    mean_abs_shap: float


class SignificanceOut(BaseModel):
    statistic: float
    p_value: float
    n: int
    significant_at_05: bool


class EnsembleForecastResponse(BaseModel):
    index_name: str
    horizon: int
    arima_order: tuple[int, int, int]
    xgb_params: dict
    weights: dict[str, float]
    forecast: list[EnsembleForecastPoint]
    arima_metrics: ModelMetricOut
    xgb_metrics: ModelMetricOut
    hybrid_metrics: ModelMetricOut
    top_features: list[ShapFeature]
    hybrid_vs_arima: SignificanceOut
    hybrid_vs_xgb: SignificanceOut
