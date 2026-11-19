"""Writes the API's OpenAPI schema to `backend/openapi.json`. No server, no key, no network.

The frontend's types are generated from this file (decisions/0008), and a test fails if
the file is not what the code would write.

    cd backend && uv run --locked python -m tools.write_openapi
"""

import json
from pathlib import Path
from typing import Any

from app.main import create_app
from app.settings import Settings

OPENAPI_PATH = Path(__file__).resolve().parents[1] / "openapi.json"


def schema() -> dict[str, Any]:
    # Default settings, read from nothing: the schema must not depend on the environment.
    return create_app(Settings()).openapi()


def render() -> str:
    return json.dumps(schema(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> None:
    OPENAPI_PATH.write_text(render())
    print(f"wrote {OPENAPI_PATH.name}: {len(schema()['paths'])} paths")


if __name__ == "__main__":
    main()
