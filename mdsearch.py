import pickle
from pathlib import Path

import typer
from rich.console import Console

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
def hello():
    console.print("Is my mic on????")


if __name__ == "__main__":
    app()
