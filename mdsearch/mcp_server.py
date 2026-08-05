"""MCP server exposing semantic search over an indexed Obsidian vault.

Which vault the server serves is controlled by the ``MDSEARCH_VAULT_PATH``
environment variable, read once at import time. If unset, the server falls
back to the current working directory of the process that launched it.

The vault must already be indexed (see ``mdsearch index <vault_path>``) —
this server only reads an existing index at ``<vault_path>/.mdsearch``, it
does not build one implicitly.

Run directly with:

    python -m mdsearch.mcp_server

or via the installed console script ``mdsearch-mcp``. Both use the stdio
transport, which is what MCP clients such as Claude Desktop expect.
"""

from __future__ import annotations

import dataclasses
import os
from pathlib import Path

# The high-level ergonomic server class in the installed `mcp` SDK
# (v2.0.0) is `mcp.server.mcpserver.MCPServer` — the successor to the
# `mcp.server.fastmcp.FastMCP` class from the 1.x SDK (that module no
# longer exists in 2.0.0). The decorator-based API (`@mcp.tool()`,
# `mcp.run()`) is unchanged, so the rest of this module reads the same
# either way.
from mcp.server.mcpserver import MCPServer

from .constants import INDEX_DIR_NAME
from .store import EmptyIndexError, VaultNotFoundError, VectorStore

# Resolved once at import time — not re-read per call, so changing the env
# var after the server has started has no effect on a running process.
VAULT_PATH = Path(os.environ.get("MDSEARCH_VAULT_PATH", ".")).expanduser().resolve()

mcp = MCPServer("mdsearch")

# Lazily-initialized singleton. The VectorStore loads a sentence-transformer
# model, which is slow — we want to pay that cost once per server process,
# not once per tool call.
_store: VectorStore | None = None


def _index_dir() -> Path:
    return VAULT_PATH / INDEX_DIR_NAME


def _get_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore.load(_index_dir())
    return _store


@mcp.tool()
def search_vault(query: str, top_k: int = 5) -> list[dict]:
    """Semantically search the indexed Obsidian vault for relevant note chunks.

    Args:
        query: Natural-language search query.
        top_k: Maximum number of results to return.

    Returns:
        A list of dicts, each with keys: file, chunk_id, score, text.
    """
    store = _get_store()

    try:
        results = store.search(query, top_k=top_k)
    except EmptyIndexError:
        raise RuntimeError(
            f"The index at {_index_dir()} is empty or does not exist. "
            f"Run `mdsearch index {VAULT_PATH}` first, then retry."
        )

    return [
        {
            "file": result.chunk.file,
            "chunk_id": result.chunk.chunk_id,
            "score": result.score,
            "text": result.chunk.text,
        }
        for result in results
    ]


@mcp.tool()
def index_vault(vault_path: str, force: bool = False) -> dict:
    """Build or incrementally update the semantic index for a markdown vault.

    Note: this indexes the vault passed in `vault_path`, which may differ
    from the vault this server was started against (MDSEARCH_VAULT_PATH).
    To search the freshly-indexed vault via `search_vault`, restart the
    server with MDSEARCH_VAULT_PATH pointed at it.

    Args:
        vault_path: Path to the markdown vault to index.
        force: Re-embed every file regardless of content hash.

    Returns:
        A dict of index statistics (files added/updated/removed/unchanged,
        total chunks, duration in seconds).
    """
    target = Path(vault_path).expanduser()
    store = VectorStore.load(target / INDEX_DIR_NAME)

    try:
        stats = store.build_or_update(target, force=force)
    except VaultNotFoundError as e:
        raise ValueError(str(e))

    return dataclasses.asdict(stats)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
