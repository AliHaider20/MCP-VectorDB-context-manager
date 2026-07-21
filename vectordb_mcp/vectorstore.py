from pathlib import Path
from typing import List, Tuple

import faiss
import numpy as np

from vectordb_mcp.config import DATA_DIR, EMBED_DIM, ensure_data_dir

_indexes: dict = {}


def _index_path(collection: str) -> Path:
    return DATA_DIR / f"{collection}.index"


def _load(collection: str):
    if collection in _indexes:
        return _indexes[collection]
    ensure_data_dir()
    path = _index_path(collection)
    if path.exists():
        index = faiss.read_index(str(path))
    else:
        index = faiss.IndexIDMap(faiss.IndexFlatIP(EMBED_DIM))
    _indexes[collection] = index
    return index


def add(collection: str, ids: List[int], vectors: np.ndarray) -> None:
    index = _load(collection)
    index.add_with_ids(
        np.ascontiguousarray(vectors, dtype="float32"),
        np.ascontiguousarray(ids, dtype="int64"),
    )
    faiss.write_index(index, str(_index_path(collection)))


def search(collection: str, vector: np.ndarray, top_k: int) -> Tuple[List[int], List[float]]:
    index = _load(collection)
    if index.ntotal == 0:
        return [], []
    scores, ids = index.search(np.asarray([vector], dtype="float32"), top_k)
    return ids[0].tolist(), scores[0].tolist()


def delete_collection(collection: str) -> None:
    _indexes.pop(collection, None)
    path = _index_path(collection)
    if path.exists():
        path.unlink()
