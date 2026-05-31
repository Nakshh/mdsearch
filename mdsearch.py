import os
import pickle
from calendar import c
from pathlib import Path

import numpy as np
import typer
from rich.console import Console
from sentence_tranformers import SentenceTransformer

app = typer.Typer()
console = Console()

# CONSTANTS
INDEX_DIR = Path(".mdsearch")
INDEX_FILE = INDEX_DIR / "index.faiss"
META_FILE = INDEX_DIR / "metadata.pkl"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def chunk_text(text: str, max_chars: int = 1000):
    chunks = []
    current = []

    for line in text.splitlines():
        if line.startswith("#") and current:
            chunks.append("\n".join(current).strip())
            current = []

        current.append(line)

        if len("\n".join(current)) > max_chars:
            chunks.append("\n".join(current).strip())
            current = []

    if current:
        chunks.append("\n".join(current).strip())

    return [chunk for chunk in chunks if len(chunk) > 5]


@app.command()
def test_chunk():
    # Generated sample from chatgpt
    sample = f"""
# Databases

{"hello " * 500}

# Hashing

short section

# Hella short

y
    """

    chunks = chunk_text(sample)

    console.print(f"Created {len(chunks)} chunks")

    for i, chunk in enumerate(chunks):
        console.print(i)
        console.print(chunk)


@app.command()
def index(vault_path: str):
    vault = Path(vault_path).expanduser()

    if not vault.exists():
        console.print(f"[red]Vault path does not exist:[/red] {vault}")
        raise typer.Exit(1)

    INDEX_DIR.mkdir(exist_ok=True)

    model = SentenceTransformer(MODEL_NAME)

    md_files = list(vault.rglob("*.md"))

    console.print(f"{len(md_files)} markdown files found!")

    all_chunks = []
    metadata = []

    for file in md_files:
        text = file.read_text(encoding="utf-8", errors="ignore")
        chunks = chunk_text(text)

        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            metadata.append({"file": str(file), "chunk_id": i, "text": chunk})

    console.print(f"{len(all_chunks)} chunks created!")

    if not all_chunks:
        console.print("[red]No chunks found.[/red]")
        raise typer.Exit(1)

    with open(META_FILE, "wb") as f:
        pickle.dump(metadata, f)

    console.print(f"[green]Saved metadata to {META_FILE}[/green]")

    embeddings = model.encode(all_chunks, show_progress_bar=True)

    embeddings = np.array(embeddings).astype("float32")
    console.print(embeddings.shape)


if __name__ == "__main__":
    app()
