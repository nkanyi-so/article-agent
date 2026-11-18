"""Runs a seeded transcript end to end from recordings and prints the article.

Free and offline: it uses the fixture client, so a prompt that no longer matches its
recording fails loudly instead of replaying a stale answer.

    cd backend && uv run --locked python -m tools.run_seed korvath-greenhouses
"""

import asyncio
import sys

from app.model.fixture import FixtureModelClient
from app.pipeline.runner import RunState, run_pipeline
from app.seeds import SEEDS, seed


async def run(seed_id: str) -> int:
    chosen = seed(seed_id)
    state = RunState(run_id=f"cli-{seed_id}")
    async for event in run_pipeline(chosen.text(), chosen.title, FixtureModelClient(), state):
        stage = getattr(event, "stage", None)
        print(f"[{event.type}{' ' + stage if stage else ''}]")
    if state.status != "completed" or state.result is None:
        print(f"\nRun failed: {state.error}")
        return 1

    result = state.result
    source = "the model's" if result.headline.source == "model" else "the transcript's title"
    print(f"\n{result.headline.text}\n(headline: {source})\n")
    paragraph = -1
    for claim in result.claims:
        if claim.paragraph != paragraph:
            paragraph = claim.paragraph
            print()
        cited = ", ".join(str(i) for i in claim.segment_indexes)
        print(f"{claim.text}  [{cited}]")
    print(f"\nRemoved by the ground check: {len(result.removed)}")
    for unit in result.removed:
        detail = f" {unit.detail}" if unit.detail else ""
        print(f"  - {unit.reason}{detail}: {unit.text}")
    calls = ", ".join(f"{c.stage} {c.source} ${c.cost_usd:.4f}" for c in state.model_calls)
    print(f"\nModel calls (replayed, cost as recorded): {calls}")
    return 0


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {s.id for s in SEEDS}:
        print("usage: python -m tools.run_seed <seed>   seeds: " + ", ".join(s.id for s in SEEDS))
        raise SystemExit(2)
    raise SystemExit(asyncio.run(run(sys.argv[1])))


if __name__ == "__main__":
    main()
