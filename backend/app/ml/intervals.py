"""Calibrated forecast bands for monthly series.

ARIMA's own 95% band assumes normal, constant-variance errors. Walk-forward tests on the USDA ocean rate (scripts/eval_intervals.py)
show that band covers 98 to 100 percent of outcomes, so it is far wider than it needs to be. The band here is empirical instead: the
half-width is the quantile of how far the rate actually moved over the same number of months during the last five years, with the
usual finite-sample correction. Measured coverage sits close to the target and the band is about half as wide."""

import math

import numpy as np

WINDOW = 60  # monthly steps: the last five years of movements


def calibrated_halfwidth(values: np.ndarray, horizon: int, level: float = 0.95, window: int = WINDOW) -> float | None:
    v = np.asarray(values, dtype=float)
    if horizon < 1 or len(v) < horizon + 24:
        return None
    moves = np.abs(v[horizon:] - v[:-horizon])[-window:]
    k = len(moves)
    q = min(1.0, math.ceil((k + 1) * level) / k)
    return float(np.quantile(moves, q))
