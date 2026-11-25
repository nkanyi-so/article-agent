"""Runs the eval set and applies the thresholds. Every case is run three times.

By default it replays recordings: free, no key, no network. This is what `make check` runs.

    cd backend && uv run --locked python -m tools.run_evals

`--live` is PAID (about $2.20 for the whole set three times: every case through the writer
and the judge). Nothing is sent without `--yes-spend`; the eval ledger stops it before
its limit; every response is saved as a recording, so the free mode can replay the
same run; and the result is written to a dated file under `backend/evals/results/`.

    cd backend && uv run --locked --group live python -m tools.run_evals \
        --live --label third --yes-spend

Exit status: 0 every threshold met; 1 a threshold failed; 2 the machinery failed (a
missing recording, a timeout, a refusal by a model), which is not a wrong answer and is
never reported as one.
"""

import argparse
import asyncio
from pathlib import Path
from typing import Any

from app.evals import thresholds
from app.evals.cases import EVALS_DIR, load_cases, recordings_dir
from app.evals.harness import run_set
from app.evals.schemas import EvalSetResult
from app.model.fixture import FixtureModelClient, save_recording
from app.model.payload import request_key
from app.model.types import ModelClient, ModelRequest, ModelResponse
from app.pipeline.config import JUDGE_MODEL
from tools import spend
from tools.key import load_key

RESULTS_DIR = EVALS_DIR / "results"


class Guarded:
    """The live client behind the spend stop: before every request, the ledger must have
    room for the most that request could cost (a full `max_tokens` of output at its
    model's price). Checked per request, not per case, so no run can pass the limit."""

    def __init__(self, inner: ModelClient, ledger: spend.Ledger) -> None:
        self.inner = inner
        self.ledger = ledger
        self.source = inner.source

    async def complete(self, request: ModelRequest) -> ModelResponse:
        is_judge = request.model == JUDGE_MODEL
        self.ledger.check_room(spend.WORST_JUDGE_CALL_USD if is_judge else spend.WORST_CALL_USD)
        return await self.inner.complete(request)


def live_client(repeat: int) -> ModelClient:
    from app.model.live import LiveModelClient

    folder = recordings_dir(repeat)

    def keep(request: ModelRequest, response: ModelResponse, raw: dict[str, Any]) -> None:
        save_recording(folder, request, response, raw)

    def billed(request: ModelRequest, cost: float | None) -> None:
        # Every response that arrives is counted, usable or not; an unreadable cost is
        # counted at the worst case rather than at nothing.
        worst = spend.WORST_JUDGE_CALL_USD
        what = f"evals/run-{repeat}/{request.model}/{request_key(request)[:12]}"
        spend.EVALS.record(what, worst if cost is None else cost)

    return Guarded(LiveModelClient(load_key(), on_raw=keep, on_billed=billed), spend.EVALS)


def fixture_client(repeat: int) -> ModelClient:
    return FixtureModelClient(recordings_dir(repeat))


def _spread(values: list[float]) -> str:
    return " ".join(f"{value:.2f}" for value in values)


def table(result: EvalSetResult) -> str:
    lines = [
        f"Eval set, {result.mode} mode, {result.ran_at}, every case run {result.repeats} times",
        "",
        "  case                    question shown        cited lines alone     coverage  removed",
        "                          mean  (each run)      mean  (each run)",
    ]
    for s in result.summaries:
        lines.append(
            f"  {s.id:22}  {s.judged_mean or 0:.3f} ({_spread(s.judged):14})  "
            f"{s.judged_alone_mean or 0:.3f} ({_spread(s.judged_alone):14})  "
            f"{s.coverage_mean or 0:.2f}      {s.removed} of {s.drafted}"
        )
    refused = [row for row in result.cases if row.outcome == "refused" or row.judge is None]
    for row in refused:
        if row.outcome != "plumbing":
            ok = all(check.passed for check in row.checks)
            lines.append(
                f"  {row.id:22}  run {row.repeat}: {row.error or 'an article'} "
                f"{'ok' if ok else 'WRONG'}"
            )
    lines.append("")
    for total in result.aggregates:
        mark = {True: "pass", False: "FAIL", None: "    "}[total.passed]
        lines.append(f"  {mark} {total.id} {total.name}: {total.value} (needs {total.threshold})")
    for failure in result.plumbing_failures:
        lines.append(f"  MACHINERY {failure}")
    lines.append(f"\n  cost ${result.cost_usd:.4f}")
    return "\n".join(lines)


def details(result: EvalSetResult) -> str:
    lines = []
    for row in result.cases:
        for check in row.checks:
            if not check.passed or (check.id == "E8" and check.detail):
                lines += [
                    f"  {row.id} run {row.repeat} {check.id}: {item}" for item in check.detail
                ]
        for verdict in row.judge.verdicts if row.judge else []:
            if not verdict.supported:
                which = "headline" if verdict.claim is None else f"claim {verdict.claim}"
                lines.append(
                    f"  {row.id} run {row.repeat} J1 {which} ({verdict.decided_by}): "
                    f"{verdict.reason}"
                )
    for n, calibration in enumerate(result.calibrations, start=1):
        for pair in calibration.pairs:
            if pair.expected_supported != pair.judged_supported:
                lines.append(
                    f"  J2 run {n} {pair.id} ({pair.kind}): judged "
                    f"{'supported' if pair.judged_supported else 'unsupported'}: {pair.reason}"
                )
            elif pair.expected_alone != pair.judged_alone:
                lines.append(
                    f"  J2 run {n} {pair.id} ({pair.kind}), cited lines alone: judged "
                    f"{'supported' if pair.judged_alone else 'unsupported'}: {pair.reason}"
                )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--yes-spend", action="store_true")
    parser.add_argument("--label", help="names the result file, for example 'third'")
    parser.add_argument("--note", default="", help="one line stored in the result file")
    parser.add_argument("--out", type=Path, help="also write the result here (any mode)")
    args = parser.parse_args()

    client_for = fixture_client
    if args.live:
        if not args.yes_spend or not args.label:
            print(
                f"Would run {len(load_cases())} cases and the judge calibration live, "
                f"{thresholds.REPEATS} times, about $2.20. Spent on eval runs so far: "
                f"${spend.EVALS.spent():.4f} of ${spend.EVALS.limit_usd:.2f}. "
                "Pass --label and --yes-spend."
            )
            # Not success: nothing was done. A script must not take this for a completed run.
            raise SystemExit(2)
        client_for = live_client

    result = asyncio.run(run_set(client_for, repeats=thresholds.REPEATS, note=args.note))
    print(table(result))
    print(details(result))
    written = result.model_dump_json(indent=2) + "\n"
    if args.live:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        path = RESULTS_DIR / f"{result.ran_at[:10]}-{args.label}.json"
        path.write_text(written)
        print(f"\nWritten to {path}. Eval spend so far: ${spend.EVALS.spent():.4f}")
    if args.out:
        args.out.write_text(written)
    if result.plumbing_failures:
        raise SystemExit(2)
    if not result.passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
