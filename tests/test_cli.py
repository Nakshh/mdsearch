from pathlib import Path

import pytest
from typer.testing import CliRunner

from mdsearch.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _sandboxed_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Never let the CLI's default '.' vault_path resolve to the real repo.

    Every test here also passes an explicit vault path that lives under
    tmp_path, so this is defense in depth: nothing should ever touch the
    real repo's .mdsearch/ directory.
    """
    monkeypatch.chdir(tmp_path)


def test_index_command_succeeds(sample_vault: Path):
    result = runner.invoke(app, ["index", str(sample_vault)])

    assert result.exit_code == 0, result.output
    assert "added=3" in result.output
    assert "chunks=6" in result.output
    assert (sample_vault / ".mdsearch" / "index.faiss").exists()


def test_index_command_missing_vault_exits_cleanly(tmp_path: Path):
    missing_vault = tmp_path / "no-such-vault"

    result = runner.invoke(app, ["index", str(missing_vault)])

    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "does not exist" in result.output


def test_search_command_succeeds_after_indexing(sample_vault: Path):
    index_result = runner.invoke(app, ["index", str(sample_vault)])
    assert index_result.exit_code == 0, index_result.output

    result = runner.invoke(app, ["search", "how do I bake bread", "--vault-path", str(sample_vault)])

    assert result.exit_code == 0, result.output
    assert "cooking.md" in result.output


def test_search_command_without_index_exits_cleanly(tmp_path: Path):
    unindexed_vault = tmp_path / "unindexed_vault"
    unindexed_vault.mkdir()

    result = runner.invoke(app, ["search", "anything", "--vault-path", str(unindexed_vault)])

    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "Index is empty" in result.output
