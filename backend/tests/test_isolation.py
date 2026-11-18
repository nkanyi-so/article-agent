"""The two rules every other test relies on: no network, no `.env`."""

import socket
from pathlib import Path

import pytest
from pytest_socket import SocketBlockedError

from app import settings as settings_module
from app.settings import load_settings


# pytest-socket also warns when it blocks; the block is what this test is for.
@pytest.mark.filterwarnings("ignore:A test tried to use socket.socket")
def test_opening_a_network_socket_fails() -> None:
    with pytest.raises(SocketBlockedError):
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def _plant_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    planted = tmp_path / ".env"
    planted.write_text("APP_MODE=live\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings_module, "DEFAULT_ENV_FILE", planted)
    monkeypatch.delenv("APP_MODE", raising=False)
    return planted


def test_a_planted_env_file_is_not_seen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _plant_env_file(tmp_path, monkeypatch)

    assert load_settings().mode == "demo"


def test_the_same_file_is_seen_once_the_test_switch_is_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The control for the test above: without it, that test would pass even if
    # env-file loading were broken rather than switched off.
    _plant_env_file(tmp_path, monkeypatch)
    monkeypatch.delenv("APP_ENV_FILE")

    assert load_settings().mode == "live"
