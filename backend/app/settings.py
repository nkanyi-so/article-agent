"""Settings come from the environment. The `.env` file is a local convenience only."""

import os
import re
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# An origin is a scheme, a host and an optional port: no path, no wildcard.
ORIGIN = re.compile(r"^https?://[A-Za-z0-9.-]+(:\d+)?$")

# The repository root's `.env`, wherever the process was started from.
DEFAULT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# Set to an empty string to switch env-file loading off (the tests do), or to a path.
ENV_FILE_SWITCH = "APP_ENV_FILE"

Mode = Literal["demo", "live"]


class Settings(BaseSettings):
    """Reads environment variables only. Use `load_settings` to also read the env file."""

    model_config = SettingsConfigDict(env_prefix="APP_", env_file=None, extra="ignore")

    mode: Mode = "demo"
    # Comma-separated origins allowed to call the API from a browser. A wildcard is refused.
    cors_origins: str = "http://localhost:3000"
    # The Phase 2 skeleton routes. Off unless switched on; Phase 5 deletes them.
    skeleton_routes: bool = False
    # Seconds between events of the skeleton stream.
    skeleton_delay_s: float = 2.0

    @field_validator("cors_origins")
    @classmethod
    def only_explicit_origins(cls, value: str) -> str:
        for part in value.split(","):
            origin = part.strip()
            if origin and not ORIGIN.fullmatch(origin):
                raise ValueError(f"cors_origins takes explicit origins only, got {origin!r}")
        return value

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


def env_file() -> Path | None:
    chosen = os.environ.get(ENV_FILE_SWITCH)
    if chosen is None:
        return DEFAULT_ENV_FILE
    return Path(chosen) if chosen else None


def load_settings() -> Settings:
    # `_env_file` is pydantic-settings' documented per-instance override.
    return Settings(_env_file=env_file())
