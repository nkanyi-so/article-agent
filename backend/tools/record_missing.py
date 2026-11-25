"""Records only the calls that have no recording, after a change that altered a few
requests (a new ground rule, a new seed).

PAID, a few cents a call. It replays every recording there is and calls a model only on
a miss, saving the answer as a recording. Nothing is sent without `--yes-spend`; the
re-recording ledger stops it before its limit, checked before every call at the most
that call could cost. This is a tool: demo mode, the tests and `make check` never fall
back to a live call.

    cd backend && uv run --locked --group live python -m tools.record_missing --yes-spend
"""

import argparse
import asyncio
import logging
from pathlib import Path
from typing import Any, Literal

from app.errors import FixtureMiss
from app.evals import thresholds
from app.evals.cases import recordings_dir
from app.evals.harness import run_set
from app.model.fixture import FixtureModelClient, save_recording
from app.model.payload import request_key
from app.model.types import ModelClient, ModelRequest, ModelResponse
from app.pipeline.config import JUDGE_MODEL
from app.pipeline.runner import RunState, run_pipeline
from app.seeds import SEEDS
from tools import spend
from tools.key import load_key


class RecordOnMiss:
    """Replays a folder of recordings; on a miss, asks the live model and records it."""

    source: Literal["fixture"] = "fixture"

    def __init__(self, folder: Path, live: ModelClient | None) -> None:
        self.folder = folder
        self.fixture = FixtureModelClient(folder)
        self.live = live
        self.missed: list[str] = []

    async def complete(self, request: ModelRequest) -> ModelResponse:
        try:
            return await self.fixture.complete(request)
        except FixtureMiss:
            self.missed.append(f"{request.model} {request_key(request)[:12]}")
            if self.live is None:
                raise
            is_judge = request.model == JUDGE_MODEL
            spend.RERECORD.check_room(
                spend.WORST_JUDGE_CALL_USD if is_judge else spend.WORST_CALL_USD
            )
            return await self.live.complete(request)


async def run(spend_money: bool) -> None:
    logging.disable(logging.CRITICAL)
    clients: dict[int, RecordOnMiss] = {}

    def client_for(repeat: int) -> RecordOnMiss:
        if repeat not in clients:
            live: ModelClient | None = None
            if spend_money:
                from app.model.live import LiveModelClient

                folder = recordings_dir(repeat)

                def keep(q: ModelRequest, a: ModelResponse, raw: dict[str, Any]) -> None:
                    save_recording(folder, q, a, raw)

                def billed(q: ModelRequest, cost: float | None) -> None:
                    worst = spend.WORST_JUDGE_CALL_USD
                    spend.RERECORD.record(
                        f"record-missing/{q.model}", worst if cost is None else cost
                    )

                live = LiveModelClient(load_key(), on_raw=keep, on_billed=billed)
            clients[repeat] = RecordOnMiss(recordings_dir(repeat), live)
        return clients[repeat]

    await run_set(client_for, repeats=thresholds.REPEATS)
    for seed in SEEDS:
        state = RunState(run_id=f"seed-{seed.id}")
        async for _ in run_pipeline(seed.text(), seed.title, client_for(1), state):
            pass
        print(f"seed {seed.id}: {state.status} {state.error or ''}")
    missed = [f"pass {n}: {m}" for n, c in clients.items() for m in c.missed]
    print(f"{len(missed)} calls had no recording:", *missed, sep="\n  ")
    print(f"Re-recording spend: ${spend.RERECORD.spent():.4f} of ${spend.RERECORD.limit_usd:.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--yes-spend", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.yes_spend))
    if not args.yes_spend:
        print("Nothing was sent. Pass --yes-spend to record the calls listed above.")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
