"""The bare liveness route and the saved assistant model."""

import asyncio

from app.api.health import liveness
from app.ml import intent


def test_liveness_answers_without_a_database():
    assert asyncio.run(liveness()) == {"status": "ok"}


def test_saved_intent_model_matches_the_training_data():
    """If the training questions change without re-running scripts/build_intent_artifacts.py, the app silently retrains at runtime
    (slow on a small server). This test makes that visible."""
    import joblib
    import pytest
    import sklearn

    if sklearn.__version__ != "1.5.2":  # the version pinned in requirements.txt, which the saved file is built with
        pytest.skip("saved model is built with the pinned scikit-learn version")
    saved = joblib.load(intent.ARTIFACTS / "intent_model.joblib")
    assert saved["signature"] == intent.signature(), "run: python scripts/build_intent_artifacts.py"
    assert intent.model() is not None
