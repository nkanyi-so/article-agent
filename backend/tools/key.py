"""Reads the API key for the paid tools in this folder."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_key() -> str:
    """Reads only ANTHROPIC_API_KEY, from the environment or the repository's .env.
    Never prints it."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            name, sep, value = line.strip().partition("=")
            if sep and name.strip() == "ANTHROPIC_API_KEY" and value.strip():
                return value.strip().strip("\"'")
    raise SystemExit("No ANTHROPIC_API_KEY in the environment or in .env.")
