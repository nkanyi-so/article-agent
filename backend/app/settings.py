from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from app.errors import MissingKeyError

# Load whichever .env is present — repo root first (the actual location), then
# backend/ (the instruction-stated path). In Docker/Railway real env vars are
# already set, so load_dotenv is a best-effort local-dev convenience only.
# override=False means real env vars always win over the file.
_THIS = Path(__file__).resolve()
for _candidate in (
    _THIS.parents[2] / ".env",   # repo root
    _THIS.parents[1] / ".env",   # backend/
):
    if _candidate.exists():
        load_dotenv(_candidate, override=False)
        break


def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise MissingKeyError(name)
    return val


def anthropic_key() -> str:
    return _require("ANTHROPIC_API_KEY")


def apollo_key() -> str:
    return _require("APOLLO_API_KEY")


def exa_key() -> str:
    return _require("EXA_API_KEY")
