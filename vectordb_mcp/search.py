from vectordb_mcp import db, vectorstore
from vectordb_mcp.config import SEARCH_OVERFETCH_MULTIPLIER
from vectordb_mcp.dedup import is_near_duplicate, shingles
from vectordb_mcp.embeddings import embed_query


def vector_search(query: str, collection_name: str, top_k: int) -> list:
    vec = embed_query(query)

    # Over-fetch candidates so that after dedup we can still return `top_k`
    # *distinct* chunks, rather than top_k raw hits that collapse to fewer
    # once near-duplicates are dropped.
    candidate_k = max(top_k * SEARCH_OVERFETCH_MULTIPLIER, top_k)
    ids, scores = vectorstore.search(collection_name, vec, candidate_k)
    if not ids:
        return []

    rows = db.fetch_chunks(ids)

    seen_hashes: set = set()
    accepted_shingles: list = []
    results = []

    for chunk_id, score in zip(ids, scores):
        if chunk_id == -1 or chunk_id not in rows:
            continue
        row = rows[chunk_id]

        # Exact-duplicate safety net (should rarely trigger, since ingestion
        # already dedupes exact matches within a collection).
        if row["content_hash"] in seen_hashes:
            continue

        # Near-duplicate filter: collapses overlap-adjacent chunks that
        # differ by a few words but are otherwise redundant context.
        sh = shingles(row["text"])
        if is_near_duplicate(sh, accepted_shingles):
            continue

        seen_hashes.add(row["content_hash"])
        accepted_shingles.append(sh)
        results.append(
            {
                "text": row["text"],
                "score": score,
                "sources": row["sources"],
            }
        )
        if len(results) >= top_k:
            break

    return results
