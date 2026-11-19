"""Ledgers of every paid call made by the tools in this folder, and the stop that reads them.

The tools are the only code in the repository that can spend. Each one checks its ledger
before a call and appends to it after, so a limit holds across tools and across runs.
"""

import json
from dataclasses import dataclass
from pathlib import Path

TRIALS = Path(__file__).resolve().parents[2] / "trials"
# The most one more writer call could cost: a full max_tokens of output plus a generous input.
WORST_CALL_USD = (16_000 * 10.0 + 20_000 * 2.0) / 1_000_000
# The same for a judge call, at the judge model's prices.
WORST_JUDGE_CALL_USD = (16_000 * 20.0 + 20_000 * 4.0) / 1_000_000


@dataclass(frozen=True)
class Ledger:
    path: Path
    limit_usd: float

    def spent(self) -> float:
        if not self.path.exists():
            # A missing ledger must not read as "nothing spent": that would reset the stop.
            raise SystemExit(f"STOP: the spend ledger {self.path} is missing. Nothing sent.")
        lines = [line for line in self.path.read_text().splitlines() if line]
        return sum(float(json.loads(line)["cost_usd"]) for line in lines)

    def check_room(self, worst_usd: float = WORST_CALL_USD) -> None:
        total = self.spent()
        if total + worst_usd > self.limit_usd:
            raise SystemExit(
                f"STOP: ${total:.4f} spent of ${self.limit_usd:.2f}; what comes next could "
                "pass the limit. Nothing sent."
            )

    def record(self, what: str, cost_usd: float) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as ledger:
            ledger.write(json.dumps({"what": what, "cost_usd": cost_usd}) + "\n")


# The owner's limit for Phase 4's paid calls: $1.50 on 2026-11-18, raised to $2.00 on 2026-11-19.
PHASE4 = Ledger(TRIALS / "phase4" / "spend.jsonl", 2.00)
# The owner's limit for Phase 6's paid eval runs: $3.00 on 2026-11-19, raised to $4.50 the
# same day for a third run with every case run three times.
PHASE6 = Ledger(TRIALS / "phase6" / "spend.jsonl", 4.50)

# The owner's limit for Phase 8: 50 cents, for recordings that have to be made again.
PHASE8 = Ledger(TRIALS / "phase8" / "spend.jsonl", 0.50)

# The Phase 4 tools (prompt_trial, record) use these.
LEDGER = PHASE4.path
LIMIT_USD = PHASE4.limit_usd
spent = PHASE4.spent
check_room = PHASE4.check_room
record = PHASE4.record
