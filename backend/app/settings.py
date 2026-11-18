"""Settings come from the environment. The `.env` file is a local convenience only."""

import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# The repository root's `.env`, wherever the process was started from.
DEFAULT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# Set to an empty string to switch env-file loading off (the tests do), or to a path.
ENV_FILE_SWITCH = "APP_ENV_FILE"

Mode = Literal["demo", "live"]


class Settings(BaseSettings):
    """Reads environment variables only. Use `load_settings` to also read the env file."""

    model_config = SettingsConfigDict(env_prefix="APP_", env_file=None, extra="ignore")

    mode: Mode = "demo"


def env_file() -> Path | None:
    chosen = os.environ.get(ENV_FILE_SWITCH)
    if chosen is None:
        return DEFAULT_ENV_FILE
    return Path(chosen) if chosen else None


def load_settings() -> Settings:
    # `_env_file` is pydantic-settings' documented per-instance override.
    return Settings(_env_file=env_file())
