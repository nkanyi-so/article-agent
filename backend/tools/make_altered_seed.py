"""Makes the recordings for the demo run whose draft was altered by hand.

FREE: it calls no model. It copies two real recordings of the Korvath seed (the extract
and the draft) under the requests the altered seed makes, and changes the draft in two
places, so that a visitor can watch the ground check remove something false:

- "fertiliser spend is down 11 percent" becomes "17 percent" (the transcript says 11);
- the sentence about the project's cost loses its citation.

Everything else is the model's draft as it was recorded. The judge's verdict on the
altered article is a real call, recorded afterwards by `tools/record_missing.py`.

    cd backend && uv run --locked python -m tools.make_altered_seed
"""

import copy
from typing import Any

from app.model.convert import response_from_api
from app.model.fixture import RECORDINGS_DIR, Recording, load_recording, save_recording
from app.model.payload import request_key
from app.model.types import ModelRequest, ModelResponse
from app.pipeline.draft import build_draft_request
from app.pipeline.extract import build_extract_request, parse_extract
from app.pipeline.ground import ground
from app.pipeline.ingest import ingest
from app.seeds import ALTERED_SEED, seed

WRONG_NUMBER = ("down 11 percent", "down 17 percent")
UNCITED = "the Ellsmoor project cost 310,000 euros"
NOTE = "Altered by hand for the demo (tools/make_altered_seed.py): not the model's draft."


def _read(raw: dict[str, Any], request: ModelRequest, original: Recording) -> ModelResponse:
    return response_from_api(
        raw, request, latency_ms=original.response.latency_ms, attempts=original.response.attempts
    )


def main() -> None:
    original, altered = seed("korvath-greenhouses"), seed(ALTERED_SEED)
    source = ingest(original.text(), original.title)
    target = ingest(altered.text(), altered.title)

    extract_from = load_recording(
        RECORDINGS_DIR / f"{request_key(build_extract_request(source))}.json"
    )
    extract_request = build_extract_request(target)
    # The raw response is kept with each recording, and a test checks that the stored
    # response is what the raw one converts to. So the raw response is what is altered,
    # and the stored response is read from it like any other.
    extract_raw = copy.deepcopy(extract_from.raw_response) | {"_note": NOTE}
    save_recording(
        RECORDINGS_DIR,
        extract_request,
        _read(extract_raw, extract_request, extract_from),
        extract_raw,
    )
    extract = parse_extract(extract_from.response, len(source.segments))

    draft_from = load_recording(
        RECORDINGS_DIR / f"{request_key(build_draft_request(source, extract))}.json"
    )
    draft_raw = copy.deepcopy(draft_from.raw_response) | {"_note": NOTE}
    changed = []
    for block in draft_raw["content"]:
        if block.get("type") != "text":
            continue
        if WRONG_NUMBER[0] in block["text"]:
            block["text"] = block["text"].replace(*WRONG_NUMBER)
            changed.append("number")
        if UNCITED in block["text"]:
            block["citations"] = None
            changed.append("citation")
    if changed != ["number", "citation"]:
        raise SystemExit(f"Expected to change one number and one citation; changed {changed}.")
    draft_request = build_draft_request(target, extract)
    response = _read(draft_raw, draft_request, draft_from)
    save_recording(RECORDINGS_DIR, draft_request, response, draft_raw)
    blocks = response.blocks

    result = ground(blocks, target.segments, extract.corrections, target.title)
    for unit in result.removed:
        print(f"removed ({unit.reason} {unit.detail}): {unit.text}")
    print(f"kept {len(result.claims)}, removed {len(result.removed)}")


if __name__ == "__main__":
    main()
