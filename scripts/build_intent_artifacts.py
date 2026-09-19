"""Train the assistant's intent model once and save it (plus its cross-validation accuracy) next to the code, so a small server
does not have to spend over a minute training it on the first question. Re-run this whenever the training questions in
backend/app/ml/intent.py change; if you forget, the app notices the mismatch and trains at runtime instead."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import joblib  # noqa: E402

from app.ml import intent  # noqa: E402


def main() -> None:
    intent.ARTIFACTS.mkdir(exist_ok=True)
    sig = intent.signature()
    x, y = intent._xy()
    joblib.dump({"signature": sig, "model": intent._pipeline().fit(x, y)}, intent.ARTIFACTS / "intent_model.joblib", compress=3)
    accs = intent.cv_accuracies.__wrapped__() if hasattr(intent.cv_accuracies, "__wrapped__") else None
    if accs is None:
        (intent.ARTIFACTS / "intent_cv.json").unlink(missing_ok=True)  # ensure a fresh computation below
        accs = intent.cv_accuracies()
    (intent.ARTIFACTS / "intent_cv.json").write_text(json.dumps({"signature": sig, "accuracies": accs}))
    print(f"saved intent model and CV accuracy ({len(accs)} folds, mean {sum(accs) / len(accs):.3f})")


if __name__ == "__main__":
    main()
