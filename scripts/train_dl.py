"""Stage 2: deep-learning experiment. LSTM, GRU, TCN and Transformer vs the classical baselines from stage 1, on the
Baltic Panamax index (BPI), 7-day-ahead, through exactly the same walk-forward splits, so every error is paired and a
Wilcoxon signed-rank test is valid. Then a final fit of the recurrent models, exported as NumPy weights that the API
serves without PyTorch.

Run stage 1 first:  backend/.venv/bin/python scripts/dl_baselines.py
Then:               backend/.venv/bin/python scripts/train_dl.py        (needs: pip install -r backend/requirements-ml.txt)
Writes backend/app/ml/artifacts/dl_results.json and lstm_BPI.npz / gru_BPI.npz."""

import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from scipy.stats import wilcoxon
from torch import nn

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.services.freight_data import load_series  # noqa: E402

ART = ROOT / "backend" / "app" / "ml" / "artifacts"
INDEX, HORIZON, N_SPLITS, MIN_TRAIN = "BPI", 7, 5, 200
LOOKBACK, EPOCHS, PATIENCE, SEEDS = 60, 60, 8, 3
EXOG = ["SP500", "DXY", "COAL_AUS", "COAL_ZA"]
torch.set_num_threads(4)


def build_features(y: pd.Series, exog: dict[str, pd.Series]) -> np.ndarray:
    """Per-day channels: BPI log-return plus the log-return of each exogenous series (0 where it does not exist yet)."""
    cols = [np.log(y).diff()]
    for name in EXOG:
        s = exog.get(name)
        if s is None:
            cols.append(pd.Series(0.0, index=y.index))
            continue
        r = np.log(s.where(s > 0)).diff().reindex(y.index.union(s.index)).ffill().reindex(y.index)
        cols.append(r.fillna(0.0))
    return pd.concat(cols, axis=1).fillna(0.0).to_numpy(dtype=np.float32)


def make_samples(feat: np.ndarray, logy: np.ndarray, end: int):
    """Windows ending at t (t + HORIZON < end) with cumulative log-return targets for h = 1..HORIZON."""
    X, Y = [], []
    for t in range(LOOKBACK, end - HORIZON):
        X.append(feat[t - LOOKBACK + 1:t + 1])
        Y.append(logy[t + 1:t + 1 + HORIZON] - logy[t])
    return np.stack(X), np.stack(Y).astype(np.float32)


class Recurrent(nn.Module):
    def __init__(self, kind: str, n_in: int, hidden: int = 32):
        super().__init__()
        self.rnn = (nn.LSTM if kind == "lstm" else nn.GRU)(n_in, hidden, batch_first=True)
        self.drop = nn.Dropout(0.1)
        self.head = nn.Linear(hidden, HORIZON)

    def forward(self, x):
        out, _ = self.rnn(x)
        return self.head(self.drop(out[:, -1]))


class TCN(nn.Module):
    def __init__(self, n_in: int, ch: int = 32):
        super().__init__()
        layers, c = [], n_in
        for d in (1, 2, 4, 8):
            layers += [nn.Conv1d(c, ch, 3, padding=d, dilation=d), nn.GELU(), nn.Dropout(0.1)]
            c = ch
        self.net = nn.Sequential(*layers)
        self.head = nn.Linear(ch, HORIZON)

    def forward(self, x):
        return self.head(self.net(x.transpose(1, 2))[:, :, -1])


class Transformer(nn.Module):
    def __init__(self, n_in: int, d: int = 32):
        super().__init__()
        self.inp = nn.Linear(n_in, d)
        self.pos = nn.Parameter(torch.randn(1, LOOKBACK, d) * 0.02)
        self.enc = nn.TransformerEncoder(nn.TransformerEncoderLayer(d, 2, 64, 0.1, batch_first=True), 2)
        self.head = nn.Linear(d, HORIZON)

    def forward(self, x):
        return self.head(self.enc(self.inp(x) + self.pos)[:, -1])


def make_model(kind: str, n_in: int) -> nn.Module:
    if kind in ("lstm", "gru"):
        return Recurrent(kind, n_in)
    return TCN(n_in) if kind == "tcn" else Transformer(n_in)


def train_one(kind: str, X: np.ndarray, Y: np.ndarray, seed: int):
    torch.manual_seed(seed)
    np.random.seed(seed)
    n_val = max(20, int(len(X) * 0.15))
    Xt, Yt, Xv, Yv = map(torch.from_numpy, (X[:-n_val], Y[:-n_val], X[-n_val:], Y[-n_val:]))
    model = make_model(kind, X.shape[2])
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    loss_fn = nn.HuberLoss(delta=1.0)
    best, best_state, bad, tr_curve, va_curve = 1e9, None, 0, [], []
    for _ in range(EPOCHS):
        model.train()
        perm = torch.randperm(len(Xt))
        run = 0.0
        for i in range(0, len(Xt), 64):
            idx = perm[i:i + 64]
            opt.zero_grad()
            loss = loss_fn(model(Xt[idx]), Yt[idx])
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            run += float(loss) * len(idx)
        model.eval()
        with torch.no_grad():
            v = float(loss_fn(model(Xv), Yv))
        tr_curve.append(run / len(Xt))
        va_curve.append(v)
        if v < best - 1e-6:
            best, bad = v, 0
            best_state = {k: t.clone() for k, t in model.state_dict().items()}
        else:
            bad += 1
            if bad >= PATIENCE:
                break
    model.load_state_dict(best_state)
    model.eval()
    return model, tr_curve, va_curve


def main() -> None:
    base = json.loads((ART / "dl_baselines.json").read_text())
    db = SessionLocal()
    y = load_series(db, INDEX)
    exog = {n: load_series(db, n) for n in EXOG}
    exog = {k: v for k, v in exog.items() if not v.empty}
    n = len(y)
    print(f"{INDEX}: {n} daily observations, {y.index[0].date()} to {y.index[-1].date()}", flush=True)

    feat_all = build_features(y, exog)
    logy = np.log(y.to_numpy())
    step = max(1, (n - MIN_TRAIN - HORIZON) // N_SPLITS)
    kinds = ["lstm", "gru", "tcn", "transformer"]
    errors: dict[str, list[float]] = {k: [] for k in kinds}
    ensemble_errors: list[float] = []
    curves: dict = {}
    timing = {k: 0.0 for k in kinds}
    t0 = time.time()
    for i in range(N_SPLITS):
        end = MIN_TRAIN + i * step
        if end + HORIZON > n:
            break
        mu, sd = feat_all[:end].mean(0), feat_all[:end].std(0) + 1e-8
        feat = (feat_all - mu) / sd
        X, Y = make_samples(feat, logy, end)
        ysd = Y.std(0) + 1e-8
        actual = y.to_numpy()[end:end + HORIZON]
        last_x = torch.from_numpy(feat[end - LOOKBACK:end][None])
        preds_all = []
        for kind in kinds:
            ts = time.time()
            preds = []
            for seed in range(SEEDS):
                model, tr, va = train_one(kind, X, Y / ysd, seed)
                with torch.no_grad():
                    c = model(last_x).numpy()[0] * ysd
                preds.append(y.to_numpy()[end - 1] * np.exp(c))
                if i == N_SPLITS - 1 and seed == 0:
                    curves[kind] = {"train": [round(v, 4) for v in tr], "val": [round(v, 4) for v in va]}
            p = np.mean(preds, axis=0)
            preds_all.append(p)
            errors[kind].extend(np.abs(actual - p).tolist())
            timing[kind] += time.time() - ts
        ensemble_errors.extend(np.abs(actual - np.mean(preds_all, axis=0)).tolist())
        print(f"split {i + 1}/{N_SPLITS} done ({time.time() - t0:.0f}s)", flush=True)

    k = len(ensemble_errors)
    actual_all = np.array(base["actuals"])[:k]
    ref = np.array(base["arima"])[:k]

    def summarise(name: str, errs, params: int | None = None) -> dict:
        e = np.array(errs)[:k]
        out = {"model": name, "mae": round(float(e.mean()), 3), "rmse": round(float(np.sqrt((e ** 2).mean())), 3),
               "mape": round(float((e / np.abs(actual_all)).mean() * 100), 3)}
        if params:
            out["parameters"] = params
        if name != "ARIMA(2,1,2)":
            out["vs_arima_p"] = round(float(wilcoxon(e, ref, alternative="less").pvalue), 4)
        return out

    n_in = feat_all.shape[1]
    rows = [summarise("ARIMA(2,1,2)", base["arima"]), summarise("XGBoost", base["xgb"]), summarise("ARIMA+XGBoost hybrid", base["hybrid"])]
    for kind in kinds:
        row = summarise({"lstm": "LSTM", "gru": "GRU", "tcn": "TCN", "transformer": "Transformer"}[kind], errors[kind], sum(p.numel() for p in make_model(kind, n_in).parameters()))
        row["train_seconds"] = round(timing[kind], 1)
        rows.append(row)
    rows.append(summarise("Deep ensemble (mean of 4)", ensemble_errors))

    best_deep = min((r for r in rows if r["model"] in ("LSTM", "GRU", "TCN", "Transformer")), key=lambda r: r["mae"])
    result = {
        "index": INDEX, "horizon_days": HORIZON, "paired_forecasts": k, "splits": N_SPLITS, "lookback_days": LOOKBACK, "seeds_per_model": SEEDS,
        "data": {"rows": n, "from": str(y.index[0].date()), "to": str(y.index[-1].date())},
        "leaderboard": sorted(rows, key=lambda r: r["mae"]), "curves": curves, "best_deep_model": best_deep["model"],
        "trained_at": pd.Timestamp.now().isoformat(timespec="seconds"),
        "note": "Lower is better. vs_arima_p is a one-sided paired Wilcoxon test that the model's absolute errors are smaller than ARIMA's on the same forecasts.",
    }
    (ART / "dl_results.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result["leaderboard"], indent=1), flush=True)

    # Final fit of the recurrent models on all data, exported as NumPy weights for PyTorch-free serving.
    mu, sd = feat_all.mean(0), feat_all.std(0) + 1e-8
    feat = (feat_all - mu) / sd
    X, Y = make_samples(feat, logy, n)
    ysd = Y.std(0) + 1e-8
    for kind in ("lstm", "gru"):
        pack = {}
        for seed in range(SEEDS):
            model, _, _ = train_one(kind, X, Y / ysd, seed)
            for name, tensor in model.state_dict().items():
                pack[f"s{seed}_{name}"] = tensor.detach().numpy()
        np.savez(ART / f"{kind}_{INDEX}.npz", **pack, mu=mu, sd=sd, ysd=ysd, seeds=SEEDS)
    print("exported weights; total", round(time.time() - t0), "s", flush=True)


if __name__ == "__main__":
    main()
