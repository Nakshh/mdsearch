from pathlib import Path

DEFAULT_MAX_CHARS = 1000


def chunk_text(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> list[str]:
    """Split markdown text into chunks, preferring to break at '#' headings.

    Falls back to a hard split once the current chunk exceeds max_chars.
    Chunks shorter than 5 characters (after stripping) are dropped.
    """
    chunks = []
    current: list[str] = []

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


def chunk_file(path: Path, max_chars: int = DEFAULT_MAX_CHARS) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return chunk_text(text, max_chars=max_chars)
