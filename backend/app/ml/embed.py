"""Optional sentence embeddings for the assistant's intent routing (Hugging Face model, run locally, no API key).

Model: BAAI/bge-small-en-v1.5 (MIT licence, 384 dimensions), run through fastembed's ONNX runtime, so nothing leaves the machine.
On the 216 hand-written questions (5-fold, three seeds, template examples always in training) embeddings alone score 86.6%, the
old TF-IDF model 73.5%, and the two averaged 86.9% (Wilcoxon p = 0.0007). If fastembed or the model is unavailable the assistant
silently falls back to the TF-IDF model. Set INTENT_EMBEDDINGS=0 to switch this off.
"""

import os
import sys
from functools import lru_cache

MODEL_NAME = "BAAI/bge-small-en-v1.5"


@lru_cache(maxsize=1)
def _embedder():
    if os.environ.get("INTENT_EMBEDDINGS", "1") == "0":
        return None
    extra = os.environ.get("FASTEMBED_PATH")
    if extra and extra not in sys.path:
        sys.path.append(extra)  # appended, so the project's own numpy still wins
    try:
        from fastembed import TextEmbedding

        return TextEmbedding(model_name=MODEL_NAME, cache_dir=os.environ.get("EMBED_CACHE") or None)
    except Exception:  # noqa: BLE001 - not installed, offline, or no cached model: fall back
        return None


def available() -> bool:
    return _embedder() is not None


def embed(texts: list[str]):
    import numpy as np

    m = _embedder()
    if m is None:
        raise RuntimeError("embeddings unavailable")
    return np.array(list(m.embed(texts)))
