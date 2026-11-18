"""A ledger of every paid call made by the tools in this folder, and the stop that reads it.

The tools are the only code in the repository that can spend. Each one checks the ledger
before a call and appends to it after, so the limit holds across tools and across runs.
"""

import json
from pathlib import Path

LEDGER = Path(__file__).resolve().parents[2] / "trials" / "phase4" / "spend.jsonl"
# The owner's limit for Phase 4's paid calls: $1.50 on 2026-11-18, raised to $2.00 on 2026-11-19.
LIMIT_USD = 2.00
# The most one more writer call could cost: a full max_tokens of output plus a generous input.
WORST_CALL_USD = (16_000 * 10.0 + 20_000 * 2.0) / 1_000_000


def spent() -> float:
    if not LEDGER.exists():
        # A missing ledger must not read as "nothing spent": that would reset the stop.
        raise SystemExit(f"STOP: the spend ledger {LEDGER} is missing. Nothing sent.")
    lines = [line for line in LEDGER.read_text().splitlines() if line]
    return sum(float(json.loads(line)["cost_usd"]) for line in lines)


def check_room() -> None:
    total = spent()
    if total + WORST_CALL_USD > LIMIT_USD:
        raise SystemExit(
            f"STOP: ${total:.4f} spent of ${LIMIT_USD:.2f}; one more call could pass the limit. "
            "Nothing sent."
        )


def record(what: str, cost_usd: float) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as ledger:
        ledger.write(json.dumps({"what": what, "cost_usd": cost_usd}) + "\n")
