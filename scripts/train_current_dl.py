"""GRU test on the current monthly data: does a neural network forecast the USDA Gulf-to-Japan ocean rate better than
'no change'? Run separately from train_current.py (PyTorch and XGBoost crash when loaded in one process on this machine).

Walk-forward: retrain every 24 months on data known at that time, predict the next month's log change from the last 12 months
of changes in the rate, the Pacific rate, coal, iron ore and the rupee. Three seeds averaged. Writes current_dl.json.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from scipy.stats import wilcoxon
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.db.session import SessionLocal  # noqa: E402
from app.models import FreightRate  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "backend" / "app" / "ml" / "artifacts" / "current_dl.json"
W = 12


def monthly(db, name):
    rows = db.query(FreightRate.rate_date, FreightRate.value).filter(FreightRate.index_name == name).order_by(FreightRate.rate_date).all()
    return pd.Series([float(v) for _, v in rows], index=pd.to_datetime([d for d, _ in rows])).resample("MS").mean().interpolate(limit=6)


class GRU(nn.Module):
    def __init__(self, n):
        super().__init__()
        self.g = nn.GRU(n, 16, batch_first=True)
        self.o = nn.Linear(16, 1)

    def forward(self, x):
        h, _ = self.g(x)
        return self.o(h[:, -1]).squeeze(-1)


def windows(F: np.ndarray, y: np.ndarray, idx):
    X = np.stack([F[i - W + 1:i + 1] for i in idx]); return torch.tensor(X, dtype=torch.float32), torch.tensor(y[list(idx)], dtype=torch.float32)


def main() -> None:
    torch.set_num_threads(1)
    db = SessionLocal()
    cols = {"GULF": "OCEAN_GULF_JAPAN", "PNW": "OCEAN_PNW_JAPAN", "COAL": "COAL_PPI", "OIL": "BRENT", "INR": "INR"}
    df = pd.concat({k: monthly(db, v) for k, v in cols.items()}, axis=1).dropna()
    db.close()
    d = np.log(df).diff().dropna()
    F = ((d - d.expanding(24).mean().shift(1)) / d.expanding(24).std().shift(1)).fillna(0).clip(-5, 5).to_numpy()  # scale with past data only
    y = d["GULF"].shift(-1).to_numpy()  # next month's change
    dates = d.index
    level = df["GULF"].reindex(dates).to_numpy()
    starts = [i for i, t in enumerate(dates) if t >= pd.Timestamp("2010-01-01") and i + 1 < len(dates)]
    preds, truth, naive = {}, {}, {}
    for block in range(0, len(starts), 24):
        chunk = starts[block:block + 24]
        cut = chunk[0]
        train_idx = list(range(W, cut - 1))  # outcome at i+1 must be known by `cut`
        Xt, yt = windows(F, y, train_idx)
        ps = []
        for seed in (1, 2, 3):
            torch.manual_seed(seed)
            m = GRU(F.shape[1]); opt = torch.optim.Adam(m.parameters(), lr=0.01, weight_decay=1e-3)
            for _ in range(60):
                opt.zero_grad(); loss = nn.functional.mse_loss(m(Xt), yt); loss.backward(); opt.step()
            m.eval()
            with torch.no_grad():
                ps.append(m(windows(F, np.nan_to_num(y), chunk)[0]).numpy())
        p = np.mean(ps, axis=0)
        for j, i in enumerate(chunk):
            preds[i] = level[i] * float(np.exp(p[j])); truth[i] = level[i + 1]; naive[i] = level[i]
    ks = sorted(preds)
    a = np.array([truth[k] for k in ks]); pg = np.array([preds[k] for k in ks]); pn = np.array([naive[k] for k in ks])
    e_g, e_n = np.abs(pg - a), np.abs(pn - a)
    res = {
        "trained_at": datetime.now().isoformat(timespec="seconds"), "model": "GRU(16) on 12-month windows, 3 seeds, retrained every 24 months", "target": "next-month USDA Gulf-to-Japan ocean rate",
        "origins": len(ks), "test_from": dates[ks[0]].date().isoformat(), "test_to": dates[ks[-1]].date().isoformat(),
        "gru_mae_usd_per_t": round(float(e_g.mean()), 2), "naive_mae_usd_per_t": round(float(e_n.mean()), 2), "p_vs_naive": round(float(wilcoxon(e_g, e_n).pvalue), 4),
        "note": "About 300 monthly observations is very little for a neural network; the result is evidence for this series and window only.",
    }
    OUT.write_text(json.dumps(res, indent=1))
    print(res)


if __name__ == "__main__":
    main()
