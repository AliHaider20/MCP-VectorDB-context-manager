"""Deduplication helpers used at both ingestion time and retrieval time.

Ingestion-time dedup: exact-match via a normalized content hash, stored as a
unique index in SQLite (see db.py). Identical chunks (e.g. repeated
boilerplate/footers across files) are embedded and stored only once; new
source files are just linked to the existing chunk.

Retrieval-time dedup: exact-hash dedup as a safety net, plus a lightweight
near-duplicate filter (word-shingle Jaccard similarity) to collapse
overlap-adjacent chunks that differ by a few words but are otherwise
redundant, so `top_k` results returned to Claude are `top_k` *distinct*
chunks instead of near-copies of each other.
"""

import hashlib

from vectordb_mcp.config import NEAR_DUP_JACCARD_THRESHOLD, NEAR_DUP_SHINGLE_SIZE


def content_hash(text: str) -> str:
    """Normalized exact-match hash: collapse whitespace, lowercase, sha256."""
    normalized = " ".join(text.strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def shingles(text: str, k: int = NEAR_DUP_SHINGLE_SIZE) -> frozenset:
    """Set of k-word shingles, used for cheap near-duplicate detection."""
    words = text.lower().split()
    if len(words) < k:
        return frozenset({tuple(words)}) if words else frozenset()
    return frozenset(tuple(words[i : i + k]) for i in range(len(words) - k + 1))


def jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    if union == 0:
        return 0.0
    return len(a & b) / union


def is_near_duplicate(candidate_shingles: frozenset, accepted_shingles: list) -> bool:
    return any(
        jaccard(candidate_shingles, s) >= NEAR_DUP_JACCARD_THRESHOLD
        for s in accepted_shingles
    )
