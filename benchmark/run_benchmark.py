"""Measures real dedup savings against a realistic small corpus.

Corpus (benchmark/docs/): 6 internal-wiki-style markdown files that each
repeat the same confidentiality-notice header and revision-history footer
verbatim (the common "every doc has the same boilerplate" case), plus two
files (deployment.md / incident_response.md) that describe the same
rollback procedure in different words (the "near-duplicate, not exact"
case near-dup filtering targets).

Run from the project root with the venv active:
    python benchmark/run_benchmark.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vectordb_mcp import db, vectorstore
from vectordb_mcp.config import EMBED_DIM
from vectordb_mcp.dedup import is_near_duplicate, jaccard, shingles
from vectordb_mcp.embeddings import embed_query
from vectordb_mcp.ingest import ingest_document

COLLECTION = "benchmark"
DOCS_DIR = Path(__file__).resolve().parent / "docs"


def reset_collection():
    db.init_db()
    db.delete_collection(COLLECTION)
    vectorstore.delete_collection(COLLECTION)
    db.ensure_collection(COLLECTION, EMBED_DIM)


def run_ingestion_benchmark():
    files = sorted(DOCS_DIR.glob("*.md"))
    totals = {"chunks_generated": 0, "chunks_stored_new": 0,
              "chunks_deduplicated": 0, "total_tokens": 0}
    per_file = []
    for f in files:
        result = ingest_document(str(f), COLLECTION, chunk_size=300, chunk_overlap=30)
        per_file.append((f.name, result))
        for k in totals:
            totals[k] += result[k]
    return files, per_file, totals


def estimate_token_savings(per_file):
    """Approximate tokens NOT re-embedded thanks to ingestion-time dedup:
    each file's average tokens-per-chunk * chunks it deduplicated."""
    saved = 0
    for _, r in per_file:
        if r["chunks_generated"] == 0:
            continue
        avg_tokens_per_chunk = r["total_tokens"] / r["chunks_generated"]
        saved += avg_tokens_per_chunk * r["chunks_deduplicated"]
    return round(saved)


def run_near_dup_benchmark():
    """Compares raw (exact-dedup-only) vs near-dup-filtered top_k for a query
    that should surface the two differently-worded rollback paragraphs."""
    query = "what should an engineer do if a deploy causes errors"
    vec = embed_query(query)
    ids, scores = vectorstore.search(COLLECTION, vec, top_k=10)
    rows = db.fetch_chunks(ids)

    raw_hits = []
    for chunk_id, score in zip(ids, scores):
        if chunk_id == -1 or chunk_id not in rows:
            continue
        raw_hits.append((chunk_id, score, rows[chunk_id]))

    # Without near-dup filter: exact-hash dedup only.
    seen_hashes = set()
    without_filter = []
    for chunk_id, score, row in raw_hits:
        if row["content_hash"] in seen_hashes:
            continue
        seen_hashes.add(row["content_hash"])
        without_filter.append((chunk_id, score, row))

    # With near-dup filter (same logic as search.py).
    seen_hashes = set()
    accepted_shingles = []
    with_filter = []
    for chunk_id, score, row in raw_hits:
        if row["content_hash"] in seen_hashes:
            continue
        sh = shingles(row["text"])
        if is_near_duplicate(sh, accepted_shingles):
            continue
        seen_hashes.add(row["content_hash"])
        accepted_shingles.append(sh)
        with_filter.append((chunk_id, score, row))

    return query, without_filter, with_filter


def main():
    reset_collection()

    print("=" * 70)
    print("INGESTION-TIME DEDUP (exact content-hash matching)")
    print("=" * 70)
    files, per_file, totals = run_ingestion_benchmark()
    for name, r in per_file:
        print(f"  {name:28s} generated={r['chunks_generated']:3d}  "
              f"new={r['chunks_stored_new']:3d}  dup={r['chunks_deduplicated']:3d}")

    dedup_rate = totals["chunks_deduplicated"] / totals["chunks_generated"] * 100
    token_savings = estimate_token_savings(per_file)
    token_savings_pct = token_savings / totals["total_tokens"] * 100

    print("-" * 70)
    print(f"  Files ingested:            {len(files)}")
    print(f"  Total chunks generated:    {totals['chunks_generated']}")
    print(f"  Chunks actually stored:    {totals['chunks_stored_new']}")
    print(f"  Chunks deduplicated:       {totals['chunks_deduplicated']}")
    print(f"  Dedup rate:                {dedup_rate:.1f}% of chunks skipped re-embedding")
    print(f"  Total tokens (raw):        {totals['total_tokens']}")
    print(f"  Tokens saved from re-embed:~{token_savings} ({token_savings_pct:.1f}%)")

    print()
    print("=" * 70)
    print("RETRIEVAL-TIME NEAR-DUPLICATE FILTERING (word-shingle Jaccard)")
    print("=" * 70)
    query, without_filter, with_filter = run_near_dup_benchmark()
    print(f"  Query: {query!r}")
    print(f"  Raw FAISS candidates fetched: 10")
    print(f"  Distinct results WITHOUT near-dup filter: {len(without_filter)}")
    for cid, score, row in without_filter:
        print(f"    - score={score:.3f} sources={row['sources']}")
        print(f"      {row['text'][:90]!r}")
    print(f"  Distinct results WITH near-dup filter:    {len(with_filter)}")
    for cid, score, row in with_filter:
        print(f"    - score={score:.3f} sources={row['sources']}")
        print(f"      {row['text'][:90]!r}")

    collapsed = len(without_filter) - len(with_filter)
    if collapsed > 0:
        print(f"  -> Near-dup filter removed {collapsed} redundant near-identical "
              f"chunk(s) from the {len(without_filter)} exact-dedup'd results "
              f"({collapsed / len(without_filter) * 100:.0f}% reduction in returned context).")
    else:
        print("  -> No near-duplicates found in this run's top candidates.")


if __name__ == "__main__":
    main()
