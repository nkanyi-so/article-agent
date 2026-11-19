"""Test-wide isolation.

Set before any app module is imported, so no test can load the developer's `.env`
by constructing settings early. Sockets are blocked by pytest-socket (see pyproject).
"""

import os
import tempfile

os.environ["APP_ENV_FILE"] = ""
# Importing the app builds it once at module level. Point that at a throwaway file, or
# collecting the tests would open (and tidy) the database a running dev server is using.
os.environ["APP_DATABASE_PATH"] = os.path.join(
    tempfile.mkdtemp(prefix="article-agent-tests-"), "import.sqlite3"
)

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def a_database_of_its_own(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test gets its own SQLite file, so no test sees another's runs."""
    monkeypatch.setenv("APP_DATABASE_PATH", str(tmp_path / "runs.sqlite3"))
