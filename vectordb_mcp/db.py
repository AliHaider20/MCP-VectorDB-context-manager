import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterable, Optional

from vectordb_mcp.config import DB_PATH, ensure_data_dir

_SCHEMA = """
CREATE TABLE IF NOT EXISTS collections (
    name TEXT PRIMARY KEY,
    dim INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection TEXT NOT NULL REFERENCES collections(name),
    text TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(collection, content_hash)
);
CREATE INDEX IF NOT EXISTS idx_chunks_hash ON chunks(collection, content_hash);

CREATE TABLE IF NOT EXISTS chunk_sources (
    chunk_id INTEGER NOT NULL REFERENCES chunks(id),
    filepath TEXT NOT NULL,
    PRIMARY KEY (chunk_id, filepath)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn():
    ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(_SCHEMA)


def ensure_collection(name: str, dim: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO collections (name, dim, created_at) VALUES (?, ?, ?)",
            (name, dim, _now()),
        )


def find_chunk_by_hash(collection: str, content_hash: str) -> Optional[int]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM chunks WHERE collection = ? AND content_hash = ?",
            (collection, content_hash),
        ).fetchone()
        return row["id"] if row else None


def insert_chunk(collection: str, text: str, content_hash: str, token_count: int) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO chunks (collection, text, content_hash, token_count, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (collection, text, content_hash, token_count, _now()),
        )
        return cur.lastrowid


def add_chunk_source(chunk_id: int, filepath: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO chunk_sources (chunk_id, filepath) VALUES (?, ?)",
            (chunk_id, filepath),
        )


def fetch_chunks(ids: Iterable[int]) -> dict:
    ids = [i for i in ids if i is not None and i != -1]
    if not ids:
        return {}
    placeholders = ",".join("?" for _ in ids)
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT c.id, c.text, c.content_hash,
                   GROUP_CONCAT(DISTINCT cs.filepath) AS sources
            FROM chunks c
            LEFT JOIN chunk_sources cs ON cs.chunk_id = c.id
            WHERE c.id IN ({placeholders})
            GROUP BY c.id
            """,
            ids,
        ).fetchall()
        return {
            row["id"]: {
                "text": row["text"],
                "content_hash": row["content_hash"],
                "sources": (row["sources"] or "").split(",") if row["sources"] else [],
            }
            for row in rows
        }


def list_collections() -> list:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT col.name, col.created_at, COUNT(ch.id) AS chunk_count
            FROM collections col
            LEFT JOIN chunks ch ON ch.collection = col.name
            GROUP BY col.name
            ORDER BY col.name
            """
        ).fetchall()
        return [dict(row) for row in rows]


def delete_collection(name: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM chunk_sources WHERE chunk_id IN (SELECT id FROM chunks WHERE collection = ?)",
            (name,),
        )
        conn.execute("DELETE FROM chunks WHERE collection = ?", (name,))
        conn.execute("DELETE FROM collections WHERE name = ?", (name,))
