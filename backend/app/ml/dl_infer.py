"""PyTorch-free inference for the recurrent models trained by scripts/train_dl.py. Weights live in
app/ml/artifacts/{lstm,gru}_BPI.npz; the forward pass is plain NumPy, so the deployed API needs no deep-learning
framework (which would not fit the 512 MB free tier)."""

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ART = Path(__file__).resolve().parent / "artifacts"
LOOKBACK = 60
EXOG = ["SP500", "DXY", "COAL_AUS", "COAL_ZA"]


def build_features(y: pd.Series, exog: dict[str, pd.Series]) -> np.ndarray:
    """Identical to scripts/train_dl.py: BPI log-return plus each exogenous log-return (0 where the series is absent)."""
    cols = [np.log(y).diff()]
    for name in EXOG:
        s = exog.get(name)
        if s is None or s.empty:
            cols.append(pd.Series(0.0, index=y.index))
            continue
        r = np.log(s.where(s > 0)).diff().reindex(y.index.union(s.index)).ffill().reindex(y.index)
        cols.append(r.fillna(0.0))
    return pd.concat(cols, axis=1).fillna(0.0).to_numpy(dtype=np.float32)


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def _lstm(x: np.ndarray, w: dict) -> np.ndarray:
    H = w["rnn.weight_hh_l0"].shape[1]
    h, c = np.zeros(H), np.zeros(H)
    for t in range(x.shape[0]):
        g = w["rnn.weight_ih_l0"] @ x[t] + w["rnn.bias_ih_l0"] + w["rnn.weight_hh_l0"] @ h + w["rnn.bias_hh_l0"]
        i, f, gg, o = _sigmoid(g[:H]), _sigmoid(g[H:2 * H]), np.tanh(g[2 * H:3 * H]), _sigmoid(g[3 * H:])
        c = f * c + i * gg
        h = o * np.tanh(c)
    return h


def _gru(x: np.ndarray, w: dict) -> np.ndarray:
    H = w["rnn.weight_hh_l0"].shape[1]
    h = np.zeros(H)
    for t in range(x.shape[0]):
        gi = w["rnn.weight_ih_l0"] @ x[t] + w["rnn.bias_ih_l0"]
        gh = w["rnn.weight_hh_l0"] @ h + w["rnn.bias_hh_l0"]
        r = _sigmoid(gi[:H] + gh[:H])
        z = _sigmoid(gi[H:2 * H] + gh[H:2 * H])
        n = np.tanh(gi[2 * H:] + r * gh[2 * H:])
        h = (1 - z) * n + z * h
    return h


@lru_cache(maxsize=4)
def _load(kind: str, index: str):
    path = ART / f"{kind}_{index}.npz"
    if not path.exists():
        return None
    z = np.load(path)
    seeds = int(z["seeds"])
    members = [{k.split("_", 1)[1]: z[k] for k in z.files if k.startswith(f"s{s}_")} for s in range(seeds)]
    return {"members": members, "mu": z["mu"], "sd": z["sd"], "ysd": z["ysd"]}


def available(index: str = "BPI") -> list[str]:
    return [k for k in ("lstm", "gru") if (ART / f"{k}_{index}.npz").exists()]


def predict(kind: str, y: pd.Series, exog: dict[str, pd.Series], index: str = "BPI") -> np.ndarray | None:
    """Seven daily forecasts (price level) from the seed-averaged recurrent model, or None if no weights exist."""
    pack = _load(kind, index)
    if pack is None:
        return None
    feat = (build_features(y, exog) - pack["mu"]) / pack["sd"]
    window = feat[-LOOKBACK:]
    fn = _lstm if kind == "lstm" else _gru
    cum = []
    for w in pack["members"]:
        h = fn(window.astype(np.float64), {k: v.astype(np.float64) for k, v in w.items()})
        cum.append((w["head.weight"].astype(np.float64) @ h + w["head.bias"]) * pack["ysd"])
    return float(y.iloc[-1]) * np.exp(np.mean(cum, axis=0))


def results() -> dict | None:
    path = ART / "dl_results.json"
    return json.loads(path.read_text()) if path.exists() else None


def weather_experiment() -> dict | None:
    path = ART / "weather_experiment.json"
    return json.loads(path.read_text()) if path.exists() else None
