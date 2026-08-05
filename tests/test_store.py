from pathlib import Path

import pytest

from mdsearch.store import EmptyIndexError, VaultNotFoundError, VectorStore

EXPECTED_TOTAL_CHUNKS = 6  # 3 fixture files, 2 headings/chunks each


def test_build_or_update_initial_build(sample_vault: Path, tmp_path: Path):
    store = VectorStore(tmp_path / "idx")
    stats = store.build_or_update(sample_vault)

    assert stats.files_added == 3
    assert stats.files_updated == 0
    assert stats.files_removed == 0
    assert stats.files_unchanged == 0
    assert stats.chunks_total == EXPECTED_TOTAL_CHUNKS
    assert store.num_chunks == EXPECTED_TOTAL_CHUNKS
    assert not store.is_empty


def test_build_or_update_raises_for_missing_vault(tmp_path: Path):
    store = VectorStore(tmp_path / "idx")

    with pytest.raises(VaultNotFoundError):
        store.build_or_update(tmp_path / "does-not-exist")


def test_rerun_with_no_changes_is_a_noop(sample_vault: Path, tmp_path: Path):
    store = VectorStore(tmp_path / "idx")
    store.build_or_update(sample_vault)

    stats = store.build_or_update(sample_vault)

    assert stats.files_unchanged == 3
    assert stats.files_added == 0
    assert stats.files_updated == 0
    assert stats.files_removed == 0
    assert stats.chunks_total == EXPECTED_TOTAL_CHUNKS


def test_editing_a_file_triggers_update_only_for_that_file(sample_vault: Path, tmp_path: Path):
    store = VectorStore(tmp_path / "idx")
    store.build_or_update(sample_vault)

    programming_md = sample_vault / "programming.md"
    programming_md.write_text(
        programming_md.read_text(encoding="utf-8")
        + "\nType hints can also help catch bugs before runtime.\n",
        encoding="utf-8",
    )

    stats = store.build_or_update(sample_vault)

    assert stats.files_updated == 1
    assert stats.files_unchanged == 2
    assert stats.files_added == 0
    assert stats.files_removed == 0


def test_deleting_a_file_removes_its_chunks(sample_vault: Path, tmp_path: Path):
    store = VectorStore(tmp_path / "idx")
    store.build_or_update(sample_vault)

    (sample_vault / "hiking.md").unlink()

    stats = store.build_or_update(sample_vault)

    assert stats.files_removed == 1
    assert stats.files_unchanged == 2
    assert stats.files_added == 0
    assert stats.files_updated == 0
    assert store.num_chunks == 4

    results = store.search("trail", top_k=store.num_chunks)
    assert all(result.chunk.file != "hiking.md" for result in results)


def test_search_on_never_built_store_raises_empty_index_error(tmp_path: Path):
    store = VectorStore(tmp_path / "idx")

    with pytest.raises(EmptyIndexError):
        store.search("anything")


def test_search_on_loaded_empty_dir_raises_empty_index_error(tmp_path: Path):
    store = VectorStore.load(tmp_path / "idx")

    with pytest.raises(EmptyIndexError):
        store.search("anything")


def test_load_on_never_built_dir_returns_valid_empty_store(tmp_path: Path):
    store = VectorStore.load(tmp_path / "idx")

    assert store.is_empty
    assert store.num_chunks == 0


def test_semantic_search_finds_the_right_topic(sample_vault: Path, tmp_path: Path):
    store = VectorStore(tmp_path / "idx")
    store.build_or_update(sample_vault)

    results = store.search("how do I bake bread", top_k=1)

    assert len(results) == 1
    assert results[0].chunk.file == "cooking.md"


def test_save_and_load_round_trip(sample_vault: Path, tmp_path: Path):
    index_dir = tmp_path / "idx"
    store = VectorStore(index_dir)
    store.build_or_update(sample_vault)  # build_or_update already calls save()

    before = store.search("how do I bake bread", top_k=1)[0]

    loaded = VectorStore.load(index_dir)

    assert loaded.num_chunks == store.num_chunks
    assert not loaded.is_empty

    after = loaded.search("how do I bake bread", top_k=1)[0]

    assert after.chunk.file == before.chunk.file
    assert after.chunk.chunk_id == before.chunk.chunk_id
    assert after.score == pytest.approx(before.score, abs=1e-4)
