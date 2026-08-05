import shutil
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_VAULT_DIR = FIXTURES_DIR / "sample_vault"


@pytest.fixture
def sample_vault(tmp_path: Path) -> Path:
    """Copy the checked-in sample vault fixture into an isolated tmp_path.

    Tests must never mutate tests/fixtures/sample_vault in place - they get
    a fresh, writable copy from this fixture instead.
    """
    dest = tmp_path / "vault"
    shutil.copytree(SAMPLE_VAULT_DIR, dest)
    return dest
