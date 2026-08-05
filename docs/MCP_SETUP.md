# MCP server setup

`mdsearch` ships an [MCP](https://modelcontextprotocol.io) server so an
assistant like Claude Desktop can search your Obsidian vault directly, as a
tool call, instead of you running the CLI yourself.

The server is stateless with respect to *which* vault it serves: it reads
that from the `MDSEARCH_VAULT_PATH` environment variable at startup (falling
back to the current working directory if unset), and only ever reads an
index that already exists at `<vault>/.mdsearch/`. It does not build an
index on its own unless you use the optional `index_vault` tool (see below).

## 1. Index your vault first

Before the server can answer searches, build the index with the CLI:

```bash
mdsearch index ~/path/to/your/vault
```

This creates `~/path/to/your/vault/.mdsearch/`. Re-run the same command any
time notes change — it's incremental (unchanged files are skipped) unless
you pass `--force`.

If you skip this step, `search_vault` will fail with a clear error telling
you to run `mdsearch index <vault_path>` — it won't crash with a raw
traceback.

## 2. Configure Claude Desktop

Add an entry to your `claude_desktop_config.json` (Claude menu → Settings →
Developer → Edit Config on macOS). Use a stdio-transport block pointing at
the Python interpreter that has `mdsearch` and its dependencies installed —
e.g. the project's virtualenv — and set `MDSEARCH_VAULT_PATH` to the vault
you indexed in step 1:

```json
{
  "mcpServers": {
    "mdsearch": {
      "command": "/absolute/path/to/mdsearch/.venv/bin/python",
      "args": ["-m", "mdsearch.mcp_server"],
      "env": {
        "MDSEARCH_VAULT_PATH": "/absolute/path/to/your/vault"
      }
    }
  }
}
```

If you installed `mdsearch` as a package (so the `mdsearch-mcp` console
script is on `PATH`), you can use that entrypoint instead:

```json
{
  "mcpServers": {
    "mdsearch": {
      "command": "/absolute/path/to/mdsearch/.venv/bin/mdsearch-mcp",
      "env": {
        "MDSEARCH_VAULT_PATH": "/absolute/path/to/your/vault"
      }
    }
  }
}
```

Restart Claude Desktop after editing the config. The server exposes:

- **`search_vault(query, top_k=5)`** — semantic search over indexed note
  chunks. Returns a list of `{file, chunk_id, score, text}` dicts.
- **`index_vault(vault_path, force=False)`** *(optional/stretch tool)* —
  builds or updates the index for a vault on demand, returning the same
  stats the CLI prints (`files_added`, `files_updated`, `files_removed`,
  `files_unchanged`, `chunks_total`, `duration_seconds`). Useful if you want
  Claude to be able to (re)index without you running the CLI, but note it
  indexes whatever `vault_path` you pass it, which may differ from the
  vault this server process was started against — restart the server with
  `MDSEARCH_VAULT_PATH` pointed at the newly-indexed vault to search it.

The sentence-transformer model is loaded lazily, on the first tool call, and
cached for the lifetime of the server process — so the first search after
startup is slower than subsequent ones.

## 3. Sanity-check manually with the MCP Inspector

Before wiring the server into Claude Desktop, you can drive it directly with
the [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```bash
MDSEARCH_VAULT_PATH=/absolute/path/to/your/vault \
  mcp dev mdsearch/mcp_server.py
```

This opens the Inspector's web UI, where you can call `search_vault` with a
test query and confirm you get back relevant chunks with sane cosine-
similarity scores, and call `index_vault` if you want to exercise that path
too.

If `mcp dev` has trouble locating a working directory's `mdsearch` package
(e.g. it's not installed in the environment `mcp` itself runs in), run it
from the repo root with `PYTHONPATH` set explicitly:

```bash
PYTHONPATH="$(pwd)" MDSEARCH_VAULT_PATH=/absolute/path/to/your/vault \
  mcp dev mdsearch/mcp_server.py
```

## Troubleshooting

- **"The index at ... is empty or does not exist"** — run `mdsearch index
  <vault_path>` (step 1) before starting the server, or before calling
  `search_vault`.
- **Wrong vault getting searched** — double check `MDSEARCH_VAULT_PATH` in
  your `claude_desktop_config.json`'s `env` block; it's read once at server
  startup, so editing it requires restarting the server (in Claude Desktop,
  restart the app).
- **Slow first response** — expected. The embedding model loads lazily on
  first use and is kept in memory afterward.
