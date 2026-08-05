from importlib.metadata import version as _pkg_version
from pathlib import Path
from urllib.parse import quote

import typer
from rich.console import Console
from rich.table import Table

from .constants import INDEX_DIR_NAME
from .embedding import MissingHFTokenError
from .store import EmptyIndexError, VaultNotFoundError, VectorStore

app = typer.Typer()
console = Console()


def _index_dir(vault_path: str) -> Path:
    return Path(vault_path).expanduser() / INDEX_DIR_NAME


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"mdsearch {_pkg_version('mdsearch-cli')}")
        raise typer.Exit()


def _obsidian_uri(vault_path: str, rel_file: str) -> str:
    """Build an obsidian://open deep link for a chunk's source file."""
    vault_name = Path(vault_path).expanduser().resolve().name
    note_path = rel_file[:-3] if rel_file.endswith(".md") else rel_file
    return f"obsidian://open?vault={quote(vault_name)}&file={quote(note_path)}"


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the mdsearch version and exit.",
    ),
) -> None:
    """mdsearch: semantic search over a markdown (Obsidian) vault."""


@app.command()
def index(
    vault_path: str = typer.Argument(".", help="Vault to index; defaults to the current directory"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-embed every file regardless of content hash"),
):
    """Build or incrementally update the semantic index for a markdown vault.

    The index is stored inside the vault itself, at <vault_path>/.mdsearch.
    """
    store = VectorStore.load(_index_dir(vault_path))

    try:
        stats = store.build_or_update(Path(vault_path), force=force)
    except VaultNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except MissingHFTokenError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    console.print(
        f"[green]Indexed.[/green] added={stats.files_added} updated={stats.files_updated} "
        f"removed={stats.files_removed} unchanged={stats.files_unchanged} "
        f"chunks={stats.chunks_total} ({stats.duration_seconds:.2f}s)"
    )


@app.command()
def search(
    query: str,
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results to return", min=1),
    vault_path: str = typer.Option(".", "--vault-path", help="Vault to search; must already be indexed"),
):
    """Search the indexed vault for chunks semantically relevant to query."""
    store = VectorStore.load(_index_dir(vault_path))

    try:
        results = store.search(query, top_k=top_k)
    except EmptyIndexError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except MissingHFTokenError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    table = Table(show_lines=False)
    table.add_column("File", style="bold", overflow="fold")
    table.add_column("Chunk", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Snippet", overflow="fold")

    for result in results:
        snippet = " ".join(result.chunk.text.split())
        if len(snippet) > 150:
            snippet = snippet[:150] + "..."
        uri = _obsidian_uri(vault_path, result.chunk.file)
        file_cell = f"[link={uri}]{result.chunk.file}[/link]"
        table.add_row(
            file_cell,
            str(result.chunk.chunk_id),
            f"{result.score:.3f}",
            snippet,
        )

    console.print(table)


if __name__ == "__main__":
    app()
