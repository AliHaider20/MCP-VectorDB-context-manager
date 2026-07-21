from pathlib import Path
from typing import Literal, Optional

from mcp.server.fastmcp import FastMCP

from vectordb_mcp import db, vectorstore
from vectordb_mcp import ingest as ingest_mod
from vectordb_mcp import search as search_mod
from vectordb_mcp.config import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_COLLECTION,
    EMBED_DIM,
)

mcp = FastMCP("vectordb-mcp")


@mcp.tool()
def ingest_local_document(
    filepath: str,
    collection_name: str = DEFAULT_COLLECTION,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> str:
    """Read a local text file, chunk it, embed the chunks, and store them in
    the vector DB collection. Exact-duplicate chunks (e.g. repeated
    boilerplate across files) are deduplicated automatically and not
    re-embedded or re-stored."""
    result = ingest_mod.ingest_document(
        filepath, collection_name, chunk_size, chunk_overlap
    )
    dedup_note = (
        f", {result['chunks_deduplicated']} deduplicated"
        if result["chunks_deduplicated"]
        else ""
    )
    return (
        f"Successfully ingested {Path(filepath).name} into '{collection_name}'. "
        f"Generated {result['chunks_generated']} chunks "
        f"({result['chunks_stored_new']} new{dedup_note}), "
        f"~{result['total_tokens']} tokens."
    )


@mcp.tool()
def vector_search(
    query: str,
    collection_name: str = DEFAULT_COLLECTION,
    top_k: int = 5,
) -> str:
    """Embed the query, search the FAISS index for the nearest chunks in the
    given collection, and return the most relevant, deduplicated text chunks
    with their source file paths."""
    results = search_mod.vector_search(query, collection_name, top_k)
    if not results:
        return f"No results found in collection '{collection_name}'."

    blocks = []
    for i, r in enumerate(results, 1):
        sources = ", ".join(s for s in r["sources"] if s) or "unknown"
        blocks.append(
            f"[{i}] score={r['score']:.3f} source={sources}\n{r['text']}"
        )
    return "\n\n".join(blocks)


@mcp.tool()
def manage_collections(
    action: Literal["list", "delete", "reset"],
    collection_name: Optional[str] = None,
) -> str:
    """List available collections, delete a collection entirely, or reset
    (empty but keep) a collection."""
    if action == "list":
        collections = db.list_collections()
        if not collections:
            return "No collections found."
        lines = [
            f"- {c['name']}: {c['chunk_count']} chunks (created {c['created_at']})"
            for c in collections
        ]
        return "\n".join(lines)

    if action not in ("delete", "reset"):
        return f"Unknown action '{action}'. Use 'list', 'delete', or 'reset'."

    if not collection_name:
        return f"collection_name is required for '{action}'."

    db.delete_collection(collection_name)
    vectorstore.delete_collection(collection_name)

    if action == "reset":
        db.ensure_collection(collection_name, EMBED_DIM)
        return f"Reset collection '{collection_name}'."
    return f"Deleted collection '{collection_name}'."


def main() -> None:
    db.init_db()
    mcp.run()


if __name__ == "__main__":
    main()
