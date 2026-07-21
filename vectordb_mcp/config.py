from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "vectordb.sqlite3"

EMBED_MODEL_ID = "jinaai/jina-embeddings-v5-text-nano"
EMBED_DIM = 768

DEFAULT_COLLECTION = "main"
DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 50

# How many extra candidates to over-fetch from FAISS per requested top_k,
# so retrieval-time dedup still has enough headroom to return top_k *distinct* chunks.
SEARCH_OVERFETCH_MULTIPLIER = 4

# Word-shingle Jaccard threshold above which two chunks are treated as
# near-duplicates during retrieval (see dedup.py).
NEAR_DUP_JACCARD_THRESHOLD = 0.7
NEAR_DUP_SHINGLE_SIZE = 5


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
