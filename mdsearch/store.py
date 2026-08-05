from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

from .chunking import chunk_file
from .constants import INDEX_FILENAME, MANIFEST_FILENAME, METADATA_FILENAME
from .embedding import DEFAULT_MODEL_NAME, Embedder
from .hashing import hash_file


class VaultNotFoundError(Exception):
    pass


class EmptyIndexError(Exception):
    pass


@dataclass(frozen=True)
class Chunk:
    file: str
    chunk_id: int
    text: str


@dataclass(frozen=True)
class SearchResult:
    chunk: Chunk
    score: float


@dataclass(frozen=True)
class IndexStats:
    files_added: int
    files_updated: int
    files_removed: int
    files_unchanged: int
    chunks_total: int
    duration_seconds: float


class VectorStore:
    def __init__(self, index_dir: Path, model_name: str = DEFAULT_MODEL_NAME) -> None:
        self.index_dir = Path(index_dir)
        self.model_name = model_name
        self._index: faiss.Index | None = None
        self._chunks: list[Chunk] = []
        self._manifest: dict = {"model_name": model_name, "dim": None, "files": {}}
        self._embedder: Embedder | None = None

    # -- loading / persistence ------------------------------------------------

    @classmethod
    def load(cls, index_dir: Path, model_name: str = DEFAULT_MODEL_NAME) -> "VectorStore":
        """Load a store from index_dir. If no index has been built yet, returns
        a valid, empty store rather than raising."""
        store = cls(index_dir, model_name=model_name)

        index_path = store.index_dir / INDEX_FILENAME
        metadata_path = store.index_dir / METADATA_FILENAME
        manifest_path = store.index_dir / MANIFEST_FILENAME

        if not (index_path.exists() and metadata_path.exists() and manifest_path.exists()):
            return store

        store._index = faiss.read_index(str(index_path))

        chunks = []
        with open(metadata_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                chunks.append(Chunk(file=obj["file"], chunk_id=obj["chunk_id"], text=obj["text"]))
        store._chunks = chunks

        with open(manifest_path, "r", encoding="utf-8") as f:
            store._manifest = json.load(f)
        store.model_name = store._manifest.get("model_name", model_name)

        return store

    def save(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)

        if self._index is not None:
            faiss.write_index(self._index, str(self.index_dir / INDEX_FILENAME))

        with open(self.index_dir / METADATA_FILENAME, "w", encoding="utf-8") as f:
            for chunk in self._chunks:
                f.write(json.dumps({"file": chunk.file, "chunk_id": chunk.chunk_id, "text": chunk.text}) + "\n")

        with open(self.index_dir / MANIFEST_FILENAME, "w", encoding="utf-8") as f:
            json.dump(self._manifest, f, indent=2)

    # -- properties -------------------------------------------------------------

    @property
    def num_chunks(self) -> int:
        return len(self._chunks)

    @property
    def is_empty(self) -> bool:
        return self.num_chunks == 0

    def _get_embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = Embedder(self.model_name)
        return self._embedder

    # -- indexing ---------------------------------------------------------------

    def build_or_update(self, vault_path: Path, force: bool = False) -> IndexStats:
        start = time.monotonic()
        vault_path = Path(vault_path).expanduser()

        if not vault_path.exists():
            raise VaultNotFoundError(f"Vault path does not exist: {vault_path}")

        md_files = sorted(vault_path.rglob("*.md"))
        current_rel_paths = {f.relative_to(vault_path).as_posix() for f in md_files}

        old_manifest_files: dict = {} if force else dict(self._manifest.get("files", {}))
        old_index = self._index

        old_rows_by_file: dict[str, list[int]] = {}
        for row_id, chunk in enumerate(self._chunks):
            old_rows_by_file.setdefault(chunk.file, []).append(row_id)

        files_added = 0
        files_updated = 0
        files_unchanged = 0

        new_manifest_files: dict = {}
        new_chunks: list[Chunk] = []
        new_vectors: list[np.ndarray | None] = []
        texts_to_embed: list[str] = []
        pending_slots: list[int] = []

        for file in md_files:
            rel_path = file.relative_to(vault_path).as_posix()
            file_hash = hash_file(file)
            chunks = chunk_file(file)

            old_entry = old_manifest_files.get(rel_path)
            unchanged = (
                not force
                and old_entry is not None
                and old_entry.get("hash") == file_hash
                and old_index is not None
                and rel_path in old_rows_by_file
                and len(old_rows_by_file[rel_path]) == len(chunks)
            )

            if unchanged:
                files_unchanged += 1
                for i, row_id in enumerate(old_rows_by_file[rel_path]):
                    new_chunks.append(Chunk(file=rel_path, chunk_id=i, text=chunks[i]))
                    new_vectors.append(old_index.reconstruct(row_id))
            else:
                files_added += 1 if old_entry is None else 0
                files_updated += 1 if old_entry is not None else 0
                for i, text in enumerate(chunks):
                    new_chunks.append(Chunk(file=rel_path, chunk_id=i, text=text))
                    new_vectors.append(None)
                    pending_slots.append(len(new_chunks) - 1)
                    texts_to_embed.append(text)

            new_manifest_files[rel_path] = {"hash": file_hash, "chunk_count": len(chunks)}

        files_removed = sum(1 for rel in old_manifest_files if rel not in current_rel_paths)

        dim = self._manifest.get("dim")
        if texts_to_embed:
            embedder = self._get_embedder()
            dim = embedder.dim
            embedded = embedder.encode(texts_to_embed, show_progress=True)
            for slot, vector in zip(pending_slots, embedded):
                new_vectors[slot] = vector

        new_index = None
        if new_chunks:
            final_vectors = np.array(new_vectors, dtype="float32")
            new_index = faiss.IndexFlatIP(dim)
            new_index.add(final_vectors)

        self._index = new_index
        self._chunks = new_chunks
        self._manifest = {
            "model_name": self.model_name,
            "dim": dim,
            "files": new_manifest_files,
            "indexed_at": time.time(),
        }

        self.save()

        return IndexStats(
            files_added=files_added,
            files_updated=files_updated,
            files_removed=files_removed,
            files_unchanged=files_unchanged,
            chunks_total=len(new_chunks),
            duration_seconds=time.monotonic() - start,
        )

    # -- search -------------------------------------------------------------------

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if self.is_empty or self._index is None:
            raise EmptyIndexError("Index is empty. Run `mdsearch index <vault_path>` first.")

        top_k = max(1, min(top_k, self.num_chunks))

        embedder = self._get_embedder()
        query_vector = embedder.encode([query])

        scores, ids = self._index.search(query_vector, top_k)

        results = []
        for score, row_id in zip(scores[0], ids[0]):
            if row_id < 0:
                continue
            results.append(SearchResult(chunk=self._chunks[row_id], score=float(score)))

        results.sort(key=lambda r: r.score, reverse=True)
        return results
