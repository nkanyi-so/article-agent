"""Phase 4 prompt trial: does a draft prompt change reduce what the ground check removes?

PAID. Runs the real extract and draft stages against the live model, several times per
transcript and prompt, and saves every request and response under `trials/phase4/`.
Nothing is sent without `--yes-spend`; a run that already has a saved result is skipped;
the shared ledger in `tools/spend.py` stops it before the owner's limit.

    cd backend && uv run --locked --group live python -m tools.prompt_trial \
        --variant baseline --variant cite-all --repeats 3 --yes-spend

`python -m tools.trial_report` reads the results and needs no key and no SDK.
"""

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from app.errors import AppError
from app.model.types import ModelRequest, ModelResponse
from app.pipeline.draft import DRAFT_SYSTEM, build_draft_request
from app.pipeline.extract import build_extract_request, parse_extract
from app.pipeline.ingest import ingest
from app.schemas import ExtractResult, IngestResult
from app.seeds import SEEDS
from tools import spend

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "trials" / "phase4"
CORRECTION = (
    ROOT / "backend" / "tests" / "fixtures" / "transcripts" / "02-hartwell-lane-correction.txt"
)

# The draft prompt as it was in the Phase 1 spike, before the change this trial measures.
BASELINE_SYSTEM = """You write short news briefs from meeting and interview transcripts.

The transcript is attached as a document. Every statement in your brief must come from it.
Do not add background, context, explanation or opinion that the speakers did not give.

Format:
- First line: a headline, on its own line, no trailing full stop.
- Then three to five short paragraphs, 200 to 350 words in total.
- Plain news-brief voice, third person. Name the speaker when attributing a statement.
- If a speaker corrected an earlier statement, report the corrected version as the fact.
- If speakers disagree, report both positions and who holds each.
- Plain text only: no markdown, no bullet points, no notes to the reader."""

# The prompt now in the code. The earlier rounds' prompts ("cite-all", "cite-all-2",
# "cite-all-3") are not kept here: each saved run under trials/phase4/ holds the exact
# request that produced it, system prompt included.
VARIANTS = {"baseline": BASELINE_SYSTEM, "neutral": DRAFT_SYSTEM}


def transcripts() -> dict[str, IngestResult]:
    found = {s.id: ingest(s.text(), s.title) for s in SEEDS}
    found["hartwell-correction"] = ingest(
        CORRECTION.read_text(), "Hartwell Lane Bakery Supply: third-quarter operations review"
    )
    return found


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


async def call(client: Any, what: str, request: ModelRequest, path: Path) -> ModelResponse | None:
    """One paid call, saved with its request, or the saved result if it was made before."""
    if path.exists():
        saved = json.loads(path.read_text())
        return ModelResponse.model_validate(saved["response"]) if saved.get("response") else None
    spend.check_room()
    record: dict[str, Any] = {"what": what, "request": request.model_dump(mode="json")}
    response: ModelResponse | None = None
    try:
        response = await client.complete(request)
    except Exception as error:
        # A refusal, a truncation, a mismatch, a failed call or anything unforeseen. Keep
        # what came back, and count the cost: the error's own figure if it has one,
        # otherwise the worst case, never nothing.
        code = error.code if isinstance(error, AppError) else type(error).__name__
        cost = getattr(error, "cost_usd", None)
        cost = spend.WORST_CALL_USD if cost is None else cost
        record |= {"error": code, "detail": getattr(error, "detail", ""), "raw": client.last_raw}
        spend.record(what, cost)
        print(f"error {what}: {code}, counted ${cost:.4f}")
        if not isinstance(error, AppError):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
            raise
    else:
        assert response is not None  # noqa: S101
        record |= {"response": response.model_dump(mode="json"), "raw": client.last_raw}
        spend.record(what, response.cost_usd)
        print(
            f"ok    {what}: in={response.usage.input_tokens} out={response.usage.output_tokens} "
            f"${response.cost_usd:.4f} {response.latency_ms / 1000:.1f}s "
            f"total=${spend.spent():.4f}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    return response


async def run(variants: list[str], repeats: int, only: str | None) -> None:
    from app.model.live import LiveModelClient

    client = LiveModelClient(load_key())
    for name, ingested in transcripts().items():
        if only and name != only:
            continue
        request = build_extract_request(ingested)
        response = await call(client, f"extract/{name}", request, OUT / "extract" / f"{name}.json")
        if response is None:
            continue
        extract: ExtractResult = parse_extract(response, len(ingested.segments))
        for variant in variants:
            for n in range(1, repeats + 1):
                draft = build_draft_request(ingested, extract, system=VARIANTS[variant])
                what = f"draft/{variant}/{name}-{n}"
                await call(client, what, draft, OUT / "draft" / variant / f"{name}-{n}.json")
    print(f"Spent in Phase 4 so far: ${spend.spent():.4f} of ${spend.LIMIT_USD:.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--variant", action="append", choices=sorted(VARIANTS), required=True)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--only", help="one transcript id")
    parser.add_argument("--yes-spend", action="store_true")
    args = parser.parse_args()
    if not args.yes_spend:
        calls = len(transcripts()) * (1 + len(args.variant) * args.repeats)
        print(
            f"Would make up to {calls} calls. Spent so far: ${spend.spent():.4f}. Pass --yes-spend."
        )
        # Not success: nothing was done. A script must not take this for a completed run.
        raise SystemExit(2)
    asyncio.run(run(args.variant, args.repeats, args.only))


if __name__ == "__main__":
    main()
