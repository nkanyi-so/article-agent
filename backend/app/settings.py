"""Settings come from the environment. The `.env` file is a local convenience only."""

import os
import re
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator
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

    model_config = SettingsConfigDict(
        env_prefix="APP_", env_file=None, extra="ignore", populate_by_name=True
    )

    mode: Mode = "demo"
    # Read from ANTHROPIC_API_KEY, without the APP_ prefix. Needed in live mode only.
    anthropic_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("ANTHROPIC_API_KEY", "anthropic_api_key")
    )
    # Comma-separated origins allowed to call the API from a browser. A wildcard is refused.
    cors_origins: str = "http://localhost:3000"
    # Where the SQLite file lives. The default is the system's scratch folder: on the hosted
    # demo that is the only writable place, and it goes when the instance does.
    database_path: Path = Path(tempfile.gettempdir()) / "article-agent.sqlite3"
    # Guards on every route that can start a run.
    runs_per_minute: int = Field(default=10, ge=1)
    daily_budget_usd: float = Field(default=2.0, ge=0)
    # How many runs other than the seeded ones are kept. Older ones are pruned, so the
    # hosted demo's scratch disk cannot be filled by starting runs.
    max_stored_runs: int = Field(default=200, ge=1)
    # Largest request body accepted, in bytes.
    max_body_bytes: int = Field(default=262_144, ge=1024)
    # Behind a platform proxy the client's address is in a header the platform sets.
    # Off by default: trusting that header anywhere else lets a caller choose its address.
    trust_proxy: bool = False
    # Demo mode replays recordings at once. This makes it wait for a fraction of the time
    # each recorded call really took, so a run can be watched. Zero by default.
    replay_latency: float = Field(default=0.0, ge=0, le=1)

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
