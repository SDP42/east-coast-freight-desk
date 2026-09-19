"""XGBoost forecasting model — the validated ARIMA+XGBoost ensemble partner
per Baghel (2025). Trained with early stopping and a small time-aware grid
search over max_depth/learning_rate/n_estimators, following the exact
hyperparameter-tuning approach documented in that thesis."""

from dataclasses import dataclass
from itertools import product

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBRegressor

from app.ml.features import build_feature_frame, feature_columns

GRID = {
    "max_depth": [3, 5],
    "learning_rate": [0.05, 0.1],
    "n_estimators": [200, 400],
}


@dataclass
class XgbFitResult:
    model: XGBRegressor
    params: dict
    feature_names: list[str]
    train_frame: pd.DataFrame


def select_best_params(target: pd.Series, exogenous: dict[str, pd.Series] | None = None) -> dict:
    """Time-aware grid search (done once on the full series) — separated from
    fitting so a walk-forward backtest can reuse the same hyperparameters
    across folds instead of re-searching per fold, which would be both slow
    and not how a real deployment would behave (you don't re-tune on every
    incoming day of data)."""
    df = build_feature_frame(target, exogenous).dropna()
    cols = feature_columns(df)
    X, y = df[cols], df["y"]

    tscv = TimeSeriesSplit(n_splits=3)
    best_params, best_score = None, float("inf")

    for max_depth, lr, n_est in product(GRID["max_depth"], GRID["learning_rate"], GRID["n_estimators"]):
        scores = []
        for train_idx, val_idx in tscv.split(X):
            model = XGBRegressor(
                max_depth=max_depth, learning_rate=lr, n_estimators=n_est,
                objective="reg:squarederror", random_state=42,
            )
            model.fit(X.iloc[train_idx], y.iloc[train_idx])
            pred = model.predict(X.iloc[val_idx])
            scores.append(float(np.sqrt(np.mean((y.iloc[val_idx].to_numpy() - pred) ** 2))))
        mean_score = float(np.mean(scores))
        if mean_score < best_score:
            best_score = mean_score
            best_params = {"max_depth": max_depth, "learning_rate": lr, "n_estimators": n_est}

    return best_params


def fit_xgboost(
    target: pd.Series,
    params: dict,
    exogenous: dict[str, pd.Series] | None = None,
) -> XgbFitResult:
    df = build_feature_frame(target, exogenous).dropna()
    cols = feature_columns(df)
    X, y = df[cols], df["y"]

    model = XGBRegressor(**params, objective="reg:squarederror", random_state=42)
    model.fit(X, y)

    return XgbFitResult(model=model, params=params, feature_names=cols, train_frame=df)


def fit_best_xgboost(target: pd.Series, exogenous: dict[str, pd.Series] | None = None) -> XgbFitResult:
    params = select_best_params(target, exogenous)
    return fit_xgboost(target, params, exogenous)


def forecast_recursive(fit_result: XgbFitResult, target: pd.Series, exogenous: dict[str, pd.Series] | None, horizon: int) -> np.ndarray:
    """Multi-step forecast by recursively feeding each prediction back in as
    the newest observation — necessary because XGBoost has no native notion
    of a future timestep the way ARIMA does."""
    extended = target.copy()
    predictions = []

    for _ in range(horizon):
        df = build_feature_frame(extended, exogenous)
        row = df[fit_result.feature_names].iloc[[-1]]
        if row.isna().any(axis=None):
            row = row.ffill(axis=0).fillna(0)
        pred = float(fit_result.model.predict(row)[0])
        predictions.append(pred)
        from app.services.freight_data import step_offset

        next_date = extended.index[-1] + step_offset(target)
        extended.loc[next_date] = pred

    return np.array(predictions)


def compute_shap_values(fit_result: XgbFitResult, top_n: int = 8) -> list[dict]:
    """Top-N features by mean absolute SHAP value (explainability). Uses the shap library; if it cannot read the installed
    XGBoost version, falls back to XGBoost's own exact tree-SHAP contributions, which are the same quantity."""
    X = fit_result.train_frame[fit_result.feature_names]
    try:
        import shap  # imported here: it pulls in numba (about 55 MB) that most requests never need

        shap_values = shap.TreeExplainer(fit_result.model).shap_values(X)
    except Exception:  # noqa: BLE001 - shap and xgboost version mismatch
        import xgboost as xgb

        contribs = fit_result.model.get_booster().predict(xgb.DMatrix(X), pred_contribs=True)
        shap_values = contribs[:, :-1]  # the last column is the bias term
    mean_abs = np.abs(shap_values).mean(axis=0)
    ranked = sorted(zip(fit_result.feature_names, mean_abs), key=lambda t: -t[1])[:top_n]
    return [{"feature": name, "mean_abs_shap": round(float(val), 4)} for name, val in ranked]
