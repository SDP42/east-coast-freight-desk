"""How good is the freight-momentum rule behind the verdict? A track record on history, with the honest answer.

Rule tested: if the freight rate rose more than a threshold over the last three months, 'rent now'; if it fell by more, 'wait'.
Outcome: the change over the following two months. Two series: the USDA grain ocean rate (1996 to 2026, monthly) and the Baltic
Panamax index (2012 to 2019, monthly average). A rule has an edge only if the rate rose more after 'rent now' than after 'wait'.
"""

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu
from sqlalchemy.orm import Session

from app.services.mlproof import _series


def _test(s: pd.Series, name: str, thr: float = 0.06, back: int = 3, fwd: int = 2) -> dict:
    l = np.log(s)
    d = pd.concat([l.diff(back).rename("m"), (l.shift(-fwd) - l).rename("f")], axis=1).dropna()
    up, dn = d[d.m > thr].f, d[d.m < -thr].f
    p = float(mannwhitneyu(up, dn).pvalue) if len(up) > 5 and len(dn) > 5 else None
    return {
        "series": name, "from": s.index[0].date().isoformat(), "to": s.index[-1].date().isoformat(), "threshold_pct": round(thr * 100), "rent_now_signals": int(len(up)), "wait_signals": int(len(dn)),
        "avg_change_after_rent_now_pct": round(float(up.mean()) * 100, 1), "avg_change_after_wait_pct": round(float(dn.mean()) * 100, 1),
        "rose_after_rent_now_pct": round(float((up > 0).mean()) * 100), "fell_after_wait_pct": round(float((dn < 0).mean()) * 100), "p_value": None if p is None else round(p, 3),
        "has_edge": bool(p is not None and p < 0.05 and up.mean() > dn.mean()),
    }


def evidence(db: Session) -> dict:
    usda = _series(db, "OCEAN_GULF_JAPAN").resample("MS").mean().interpolate(limit=6).dropna()
    bpi = _series(db, "BPI").resample("MS").mean().dropna()
    tests = [_test(usda, "USDA grain ocean rate"), _test(bpi, "Baltic Panamax index")]
    verdict = ("Mixed evidence: momentum shows a small, borderline edge in the 30-year USDA series and none in the 2012 to 2019 Baltic data, so the verdict gives the freight-momentum signal a modest weight and leans mainly on time pressure, supply, season and the rupee."
               if tests[0]["has_edge"] and not tests[1]["has_edge"] else "The momentum rule shows no consistent edge; it is a small part of the verdict.")
    return {"tests": tests, "summary": verdict, "method": "Mann-Whitney test of the two-month change after a 6% three-month rise against after a 6% fall. Signals overlap in time, so treat p-values as indicative."}
