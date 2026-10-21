"""One pinned multilingual model for both index and query embeddings."""
from __future__ import annotations

import os
from functools import lru_cache
from threading import Lock

import numpy as np

from apps.backend.common.utils.text import strip_accents

EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
EMBEDDING_ID = f"{EMBEDDING_MODEL}@{EMBEDDING_REVISION}:accent-mean-v1"
EMBEDDING_DIMENSION = 1024
_lock = Lock()


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL, revision=EMBEDDING_REVISION,
                               device=os.environ.get("EMBEDDING_DEVICE") or None,
                               model_kwargs={"use_safetensors": False})


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    # Serialize model initialization and MPS inference across concurrent requests.
    with _lock:
        model = _model()
        views = texts + [strip_accents(t) for t in texts]
        lengths = model.tokenizer(views, truncation=False, return_length=True)["length"]
        if any(length > model.max_seq_length for length in lengths):
            raise ValueError("Đoạn vượt token budget của embedding; giảm kích thước chunk, không tự cắt mất text.")
        vectors = model.encode(views, batch_size=4, normalize_embeddings=True,
                               show_progress_bar=len(texts) > 1)
    if vectors.shape != (len(views), EMBEDDING_DIMENSION):
        raise ValueError("Embedding không khớp VECTOR(1024).")
    vectors = vectors[:len(texts)] + vectors[len(texts):]
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors.tolist()
