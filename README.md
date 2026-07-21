# vectordb-mcp

Local RAG over your own files, exposed to Claude Desktop and Claude Code as
an MCP server. Chunking via LangChain's `RecursiveCharacterTextSplitter`,
embeddings via `jinaai/jina-embeddings-v5-text-nano` (local, no API key),
vectors in FAISS, text/metadata in SQLite.

## Setup

```powershell
cd vectordb-mcp
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

First run downloads the embedding model (~1GB) from Hugging Face and caches
it locally (`%USERPROFILE%\.cache\huggingface`).

Data files (`data/vectordb.sqlite3`, `data/<collection>.index`) are created
under the project's `data/` folder on first use — nothing global, easy to
wipe by deleting the folder.

## Register with Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vectordb-mcp": {
      "command": "C:\\Users\\Kiran\\OneDrive\\Desktop\\Projects\\vectordb-mcp\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\Kiran\\OneDrive\\Desktop\\Projects\\vectordb-mcp\\run.py"]
    }
  }
}
```

Restart Claude Desktop; the three tools (`ingest_local_document`,
`vector_search`, `manage_collections`) should appear under the hammer icon.

## Register with Claude Code

From the project directory (or any directory, using absolute paths):

```powershell
claude mcp add vectordb-mcp -- "C:\Users\Kiran\OneDrive\Desktop\Projects\vectordb-mcp\.venv\Scripts\python.exe" "C:\Users\Kiran\OneDrive\Desktop\Projects\vectordb-mcp\run.py"
```

Verify with `claude mcp list` / `/mcp` inside a session.

## Tools

- **ingest_local_document**(filepath, collection_name="main", chunk_size=512, chunk_overlap=50)
- **vector_search**(query, collection_name="main", top_k=5)
- **manage_collections**(action: "list" | "delete" | "reset", collection_name=None)

## Deduplication

Two layers, see `vectordb_mcp/dedup.py`:

- **Ingestion-time (exact):** each chunk is hashed (normalized, sha256) and
  checked against a `UNIQUE(collection, content_hash)` index in SQLite.
  Duplicate content (repeated boilerplate/footers across files) is embedded
  and stored once; re-ingesting the same or overlapping content just links
  the new source file to the existing chunk row.
- **Retrieval-time (exact + near-duplicate):** `vector_search` over-fetches
  candidates from FAISS, drops exact hash repeats as a safety net, and also
  drops near-duplicates via word-shingle Jaccard similarity (default
  threshold 0.7) so overlap-adjacent chunks that differ by only a few words
  don't both make it into the `top_k` results returned to Claude.
