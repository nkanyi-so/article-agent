"""The fixture client: replays recorded responses, keyed by the exact request.

Used by tests, CI, `make check` and demo mode. A miss is an error. It never falls back
to a live call, and it cannot: this module does not know the live client exists.
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from app.errors import FixtureMiss
from app.model.payload import request_key
from app.model.types import ModelRequest, ModelResponse

RECORDINGS_DIR = Path(__file__).resolve().parents[2] / "recordings"


class Recording(BaseModel):
    """One live call: the request as the pipeline built it, the response as the pipeline
    read it, and the API's raw response for anyone who wants to check the reading."""

    request: ModelRequest
    response: ModelResponse
    raw_response: dict[str, Any]


def save_recording(
    folder: Path, request: ModelRequest, response: ModelResponse, raw_response: dict[str, Any]
) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{request_key(request)}.json"
    recording = Recording(request=request, response=response, raw_response=raw_response)
    path.write_text(
        json.dumps(recording.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
    )
    return path


def load_recording(path: Path) -> Recording:
    recording = Recording.model_validate_json(path.read_text())
    if request_key(recording.request) != path.stem:
        # A recording edited by hand, or filed under the wrong name, must not be replayed.
        raise FixtureMiss(f"{path.stem[:12]} does not match the request stored in it")
    return recording


class FixtureModelClient:
    source: Literal["fixture"] = "fixture"

    def __init__(self, folder: Path = RECORDINGS_DIR, latency_factor: float = 0.0) -> None:
        self.folder = folder
        # A replay returns at once. To let a run be watched, it can wait for a fraction of
        # the time the recorded call really took. Zero in tests and by default.
        self.latency_factor = latency_factor

    async def complete(self, request: ModelRequest) -> ModelResponse:
        key = request_key(request)
        path = self.folder / f"{key}.json"
        if not path.exists():
            raise FixtureMiss(f"no recording for request {key[:12]} ({request.model})")
        response = load_recording(path).response
        if self.latency_factor > 0:
            await asyncio.sleep(response.latency_ms / 1000 * self.latency_factor)
        return response
