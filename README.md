# mdsearch

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Semantic search over a folder of markdown files — built for Obsidian vaults,
but works on any directory of `.md` notes.

Instead of grepping for exact words, `mdsearch` finds notes that are *about*
what you're asking, even if they never use your exact phrasing. It chunks
your notes, embeds each chunk with a local sentence-transformers model,
stores the vectors in a FAISS index, and searches by cosine similarity.

This was originally built so [Claude](https://claude.com) could search an
Obsidian vault intelligently via MCP — see
[docs/MCP_SETUP.md](docs/MCP_SETUP.md) for wiring it up with Claude Desktop.
It works standalone as a CLI too.

## Why

Filename and grep search only find notes that contain your literal words. If
you wrote "used a dictionary to cache API responses" six months ago and
search for "memoization", grep finds nothing — `mdsearch` finds it, because
the embedding model understands the two phrases are related.

## Install

```bash
pip install mdsearch-cli
```

The package is named `mdsearch-cli` on PyPI (`mdsearch` was already taken by
an unrelated project), but it installs the same `mdsearch` command and
`mdsearch.*` Python package.

To install from source instead:

```bash
git clone https://github.com/Nakshh/mdsearch.git
cd mdsearch
pip install -e .
```

Requires Python 3.11+. The first run downloads a small embedding model
(`all-MiniLM-L6-v2`, ~90MB) from Hugging Face and caches it locally.

## Usage

Build (or incrementally update) the index for a vault:

```bash
$ mdsearch index ~/ObsidianVault
Indexed. added=142 updated=0 removed=0 unchanged=0 chunks=891 (38.42s)
```

Search it:

```bash
$ mdsearch search "notes on memoization" --vault-path ~/ObsidianVault --top-k 3
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ File               ┃ Chunk ┃ Score ┃ Snippet                                 ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ caching-notes.md   │     2 │ 0.612 │ # Caching strategies Used a dict as a  │
│                    │       │       │ simple memo table to avoid recomputing │
│                    │       │       │ expensive recursive calls...           │
│ algorithms.md      │     0 │ 0.401 │ # Dynamic programming DP is really     │
│                    │       │       │ just recursion plus caching...         │
│ interview-prep.md  │     5 │ 0.318 │ # Common gotchas Forgetting to cache   │
│                    │       │       │ results leads to exponential blowup... │
└────────────────────┴───────┴───────┴─────────────────────────────────────────┘
```

Re-running `index` on an unchanged vault is a near-instant no-op — every
file's content hash is checked against a manifest, and only changed or new
files get re-embedded:

```bash
$ mdsearch index ~/ObsidianVault
Indexed. added=0 updated=0 removed=0 unchanged=142 chunks=891 (0.01s)
```

### Commands

| Command | Description |
|---|---|
| `mdsearch index <vault_path>` | Build or incrementally update the index for a vault. |
| `mdsearch search <query>` | Search an already-indexed vault. |
| `mdsearch --version` | Print the installed version. |

### `index` options

| Flag | Description |
|---|---|
| `--force`, `-f` | Re-embed every file regardless of content hash. |

### `search` options

| Flag | Description |
|---|---|
| `--top-k`, `-k` | Number of results to return (default 5, must be ≥ 1). |
| `--vault-path` | Vault to search; defaults to the current directory. Must already be indexed. |

The index lives at `<vault_path>/.mdsearch` — inside the vault itself, so it
travels with the vault and doesn't depend on where you run the command from.

## Architecture

```
markdown files -> chunk -> embed -> FAISS index -> search
```

- **Chunking**: each `.md` file is split on heading boundaries, with a hard
  fallback split for oversized sections, so chunks stay small and topical.
- **Embedding**: chunks are encoded with a local `sentence-transformers`
  model (default `all-MiniLM-L6-v2`) — no API calls, no data leaves your
  machine.
- **Indexing**: vectors are L2-normalized and stored in a FAISS
  `IndexFlatIP`, so inner product search is equivalent to cosine similarity.
  It's an exact, brute-force index rather than an approximate one (HNSW,
  IVF, ...) — at the scale of a personal vault (thousands, not millions, of
  chunks) exact search is fast enough and there's no accuracy tradeoff to
  make.
- **Incremental updates**: a per-file sha256 manifest is stored alongside
  the index. On re-index, unchanged files reuse their cached vectors
  instead of being re-embedded, so re-running `index` on a mostly-unchanged
  vault is near-instant.
- **Metadata**: chunk text and file/chunk IDs are stored as human-readable
  JSONL, not pickled, so the index directory is easy to inspect or diff.

## MCP server

`mdsearch` also ships an MCP server so an AI assistant (e.g. Claude Desktop)
can search your vault directly. See [docs/MCP_SETUP.md](docs/MCP_SETUP.md)
for setup instructions.

## License

MIT — see [LICENSE](LICENSE).
