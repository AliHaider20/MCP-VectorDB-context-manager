import os
from typing import List

# Model is downloaded once and cached locally; skip HF Hub network/update
# checks on every load. Must be set before sentence_transformers/
# huggingface_hub are imported.
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from vectordb_mcp.config import EMBED_MODEL_ID

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = SentenceTransformer(
            EMBED_MODEL_ID,
            trust_remote_code=True,
            device=device,
            local_files_only=True,
        )
    return _model


def embed_query(text: str) -> np.ndarray:
    model = _get_model()
    vec = model.encode(
        [text], task="retrieval", prompt_name="query", normalize_embeddings=True
    )
    return np.asarray(vec[0], dtype="float32")


def embed_documents(texts: List[str]) -> np.ndarray:
    model = _get_model()
    vecs = model.encode(
        texts, task="retrieval", prompt_name="document", normalize_embeddings=True
    )
    return np.asarray(vecs, dtype="float32")
