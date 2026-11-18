"""Records the seeded transcripts: runs each through the real pipeline against the live
model and saves every request and response under `backend/recordings/`.

PAID (about 4 cents a transcript). Nothing is sent without `--yes-spend`, and the shared
ledger in `tools/spend.py` stops it before the owner's limit. After this, demo mode,
the tests and CI replay these files and never call a model.

    cd backend && uv run --locked --group live python -m tools.record --yes-spend
"""

import argparse
import asyncio
from typing import Any

from app.model.fixture import RECORDINGS_DIR, save_recording
from app.model.payload import request_key
from app.model.types import ModelRequest, ModelResponse
from app.pipeline.runner import RunState, run_pipeline
from app.seeds import SEEDS
from tools import spend
from tools.prompt_trial import load_key


async def record_all(only: str | None) -> None:
    from app.model.live import LiveModelClient

    def keep(request: ModelRequest, response: ModelResponse, raw: dict[str, Any]) -> None:
        save_recording(RECORDINGS_DIR, request, response, raw)

    def billed(request: ModelRequest, cost: float | None) -> None:
        # Called for every response that arrives, usable or not. An unreadable cost is
        # counted at the worst case rather than at nothing.
        spend.record(
            f"record/{request_key(request)[:12]}", spend.WORST_CALL_USD if cost is None else cost
        )

    client = LiveModelClient(load_key(), on_raw=keep, on_billed=billed)
    for seed in SEEDS:
        if only and seed.id != only:
            continue
        spend.check_room()
        state = RunState(run_id=f"record-{seed.id}")
        async for event in run_pipeline(seed.text(), seed.title, client, state):
            if event.type == "stage_started":
                spend.check_room()
        result = state.result
        summary = (
            f"{len(result.claims)} kept, {len(result.removed)} removed, headline from "
            f"{result.headline.source}"
            if result
            else f"FAILED: {state.error}"
        )
        print(f"{seed.id}: {state.status}, {summary}, ${state.cost_usd():.4f}")
    print(f"Spent in Phase 4 so far: ${spend.spent():.4f} of ${spend.LIMIT_USD:.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--only", help="one seed id")
    parser.add_argument("--yes-spend", action="store_true")
    args = parser.parse_args()
    if not args.yes_spend:
        print(
            f"Would record {len(SEEDS)} seeds, two calls each. Spent so far: ${spend.spent():.4f}."
        )
        # Not success: nothing was done. A script must not take this for a completed run.
        raise SystemExit(2)
    asyncio.run(record_all(args.only))


if __name__ == "__main__":
    main()
