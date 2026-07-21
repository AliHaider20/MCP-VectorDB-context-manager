from pathlib import Path

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

from vectordb_mcp import db, vectorstore
from vectordb_mcp.config import EMBED_DIM
from vectordb_mcp.dedup import content_hash
from vectordb_mcp.embeddings import embed_documents

_ENCODING = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


def ingest_document(
    filepath: str,
    collection_name: str,
    chunk_size: int,
    chunk_overlap: int,
) -> dict:
    path = Path(filepath).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"No such file: {path}")

    text = path.read_text(encoding="utf-8", errors="ignore")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    chunks = [c for c in splitter.split_text(text) if c.strip()]

    db.ensure_collection(collection_name, EMBED_DIM)

    new_texts: list[str] = []
    new_hashes: list[str] = []

    for chunk in chunks:
        h = content_hash(chunk)
        existing_id = db.find_chunk_by_hash(collection_name, h)
        if existing_id is not None:
            # Exact duplicate already stored (e.g. repeated boilerplate) -
            # skip re-embedding, just record this file as another source.
            db.add_chunk_source(existing_id, str(path))
        else:
            new_texts.append(chunk)
            new_hashes.append(h)

    if new_texts:
        vectors = embed_documents(new_texts)
        new_ids = []
        for text_chunk, h in zip(new_texts, new_hashes):
            chunk_id = db.insert_chunk(
                collection_name, text_chunk, h, _count_tokens(text_chunk)
            )
            db.add_chunk_source(chunk_id, str(path))
            new_ids.append(chunk_id)
        vectorstore.add(collection_name, new_ids, vectors)

    total_tokens = sum(_count_tokens(c) for c in chunks)
    duplicate_count = len(chunks) - len(new_texts)

    return {
        "chunks_generated": len(chunks),
        "chunks_stored_new": len(new_texts),
        "chunks_deduplicated": duplicate_count,
        "total_tokens": total_tokens,
    }
