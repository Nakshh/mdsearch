from pathlib import Path

import typer
from rich.console import Console

from .constants import INDEX_DIR_NAME
from .store import EmptyIndexError, VaultNotFoundError, VectorStore

app = typer.Typer()
console = Console()


def _index_dir() -> Path:
    return Path(INDEX_DIR_NAME)


@app.command()
def index(vault_path: str, force: bool = typer.Option(False, "--force", "-f", help="Re-embed every file regardless of content hash")):
    """Build or incrementally update the semantic index for a markdown vault."""
    store = VectorStore.load(_index_dir())

    try:
        stats = store.build_or_update(Path(vault_path), force=force)
    except VaultNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    console.print(
        f"[green]Indexed.[/green] added={stats.files_added} updated={stats.files_updated} "
        f"removed={stats.files_removed} unchanged={stats.files_unchanged} "
        f"chunks={stats.chunks_total} ({stats.duration_seconds:.2f}s)"
    )


@app.command()
def search(query: str, top_k: int = 5):
    """Search the indexed vault for chunks semantically relevant to query."""
    store = VectorStore.load(_index_dir())

    try:
        results = store.search(query, top_k=top_k)
    except EmptyIndexError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    for result in results:
        console.print(f"[bold]{result.chunk.file}[/bold] (chunk {result.chunk.chunk_id}, score={result.score:.3f})")
        console.print(result.chunk.text)
        console.print()


if __name__ == "__main__":
    app()
