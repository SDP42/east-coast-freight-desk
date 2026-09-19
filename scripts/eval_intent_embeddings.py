"""Measure the assistant's intent accuracy with and without Hugging Face embeddings and write intent_eval.json.

Uses the same protocol as the original figure: 5-fold on the hand-written questions with the template questions always in
training, repeated for three seeds. Needs fastembed (pip install fastembed); set FASTEMBED_PATH if it is installed elsewhere.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.ml import embed, intent  # noqa: E402


def main() -> None:
    if not embed.available():
        raise SystemExit("Embeddings unavailable: install fastembed first.")
    hx, hy = intent._handwritten()
    ax, ay = intent.augmented()
    hy, ay = np.array(hy), np.array(ay)
    Eh, Ea = embed.embed(hx), embed.embed(ax)
    res = {"tfidf": [], "embeddings": [], "combined": []}
    for seed in (7, 11, 23):
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=seed).split(hx, hy):
            xt = [intent.tag(hx[i]) for i in tr] + [intent.tag(q) for q in ax]
            yt = list(hy[tr]) + list(ay)
            m = intent._pipeline().fit(xt, yt)
            pt = m.predict_proba([intent.tag(hx[i]) for i in te])
            e = LogisticRegression(C=20, max_iter=3000).fit(np.vstack([Eh[tr], Ea]), yt)
            pe = e.predict_proba(Eh[te])
            res["tfidf"].append(float((m.classes_[pt.argmax(1)] == hy[te]).mean()))
            res["embeddings"].append(float((e.classes_[pe.argmax(1)] == hy[te]).mean()))
            res["combined"].append(float((e.classes_[(pt + pe).argmax(1)] == hy[te]).mean()))
    out = {"evaluated_at": datetime.now().isoformat(timespec="seconds"), "model": embed.MODEL_NAME, "folds": len(res["tfidf"]), "questions": len(hx), "intents": len(set(hy)),
           **{f"{k}_accuracy": round(float(np.mean(v)), 3) for k, v in res.items()}, **{f"{k}_std": round(float(np.std(v)), 3) for k, v in res.items()},
           "p_combined_vs_tfidf": round(float(wilcoxon(res["combined"], res["tfidf"]).pvalue), 4),
           "note": "Held-out hand-written questions, in-distribution; not an external benchmark."}
    p = Path(__file__).resolve().parents[1] / "backend" / "app" / "ml" / "artifacts" / "intent_eval.json"
    p.write_text(json.dumps(out, indent=1))
    print(out)


if __name__ == "__main__":
    main()
