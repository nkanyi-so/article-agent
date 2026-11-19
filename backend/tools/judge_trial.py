"""Phase 6 trial: what would the judge say if it were shown a cited answer's question, and
a headline against the whole kept article?

PAID (about 45 cents). It changed nothing in the product. It is kept as the record of how
the numbers in docs/decisions/0014 were produced; both changes were then approved and
built into the judge, so running it again would put the question in twice.

It replayed the second eval run's articles from the recordings, put each to the live judge
again under a trial prompt, and saved every request and answer under `trials/phase6/`.
Nothing is sent without `--yes-spend`; the Phase 6 ledger stops it before the owner's limit.

    cd backend && uv run --locked --group live python -m tools.judge_trial --yes-spend

The two changes on trial, both for the owner to decide (docs/decisions/0014):

- context: for each cited line that opens a turn, the question it was answering (the last
  line of the turn before, when that line ends with a question mark) is shown to the judge
  as context. It is never evidence: a verdict still has to rest on a cited line.
- whole body: a headline is judged against the cited lines of every kept sentence, not
  only of the sentences that share a name or a figure with it.
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from app.errors import AppError
from app.evals import judge
from app.evals.cases import lines_of, load_cases, load_pairs
from app.evals.schemas import EvalReport
from app.model.fixture import FixtureModelClient
from app.model.types import ModelRequest, ModelResponse, TextPart
from app.pipeline.extract import as_data
from app.pipeline.ingest import ingest
from app.pipeline.runner import RunState, run_pipeline
from app.schemas import Segment
from tools import spend
from tools.prompt_trial import load_key

OUT = Path(__file__).resolve().parents[2] / "trials" / "phase6" / "judge-trial.json"

TRIAL_RULE = (
    "Some items also have <context> lines. A program added them: each is the question that a "
    "cited line was answering. Read a cited answer together with its question, as a reader of "
    "the transcript would. A context line is never evidence by itself: do not name it as "
    "support, and a sentence that only a context line supports is not supported.\n\n"
)
TRIAL_SYSTEM = judge.JUDGE_SYSTEM.replace("Return one verdict", TRIAL_RULE + "Return one verdict")


def questions_answered(cited: tuple[Segment, ...], segments: list[Segment]) -> list[Segment]:
    """For each cited line that opens a turn, the question the turn before ended on."""
    have = {segment.index for segment in cited}
    found: dict[int, Segment] = {}
    for segment in cited:
        if segment.index == 0:
            continue
        before = segments[segment.index - 1]
        is_question = before.turn != segment.turn and before.text.rstrip().endswith("?")
        if is_question and before.index not in have:
            found[before.index] = before
    return [found[index] for index in sorted(found)]


def _lines(lines: list[Segment] | tuple[Segment, ...]) -> str:
    return "\n".join(f"[{s.index}] {as_data(s.speaker)}: {as_data(s.text)}" for s in lines)


def trial_request(items: list[judge.JudgeItem], segments: list[list[Segment]]) -> ModelRequest:
    parts = []
    for number, (item, transcript) in enumerate(zip(items, segments, strict=True)):
        context = questions_answered(item.cited, transcript)
        extra = f"<context>\n{_lines(context)}\n</context>\n" if context else ""
        parts.append(
            f'<item number="{number}">\n<sentence>{as_data(item.sentence)}</sentence>\n'
            f"<cited>\n{_lines(item.cited)}\n</cited>\n{extra}</item>"
        )
    base = judge.build_judge_request(items)
    return base.model_copy(
        update={
            "system": TRIAL_SYSTEM,
            "content": [TextPart(text="<items>\n" + "\n".join(parts) + "\n</items>")],
        }
    )


async def ask(
    client: Any, what: str, items: list[judge.JudgeItem], segments: list[list[Segment]]
) -> list[judge.Judgement] | str:
    spend.PHASE6.check_room(spend.WORST_JUDGE_CALL_USD)
    request = trial_request(items, segments)
    try:
        response: ModelResponse = await client.complete(request)
        return judge.parse_judgement(response, items)
    except AppError as error:
        print(f"{what}: {error.code}")
        return error.code


async def run() -> None:
    from app.model.live import LiveModelClient

    def billed(request: ModelRequest, cost: float | None) -> None:
        worst = spend.WORST_JUDGE_CALL_USD
        spend.PHASE6.record("judge-trial", worst if cost is None else cost)

    client = LiveModelClient(load_key(), on_billed=billed)
    logging.disable(logging.CRITICAL)
    cases = load_cases()
    out: dict[str, Any] = {"cases": [], "calibration": []}
    for case in cases:
        if case.expect_error:
            continue
        state = RunState(run_id=f"trial-{case.id}")
        async for _ in run_pipeline(case.text(), case.title, FixtureModelClient(), state):
            pass
        assert state.result is not None  # noqa: S101
        result = state.result
        segments = ingest(case.text(), case.title).segments
        as_specified = EvalReport.model_validate(state.stages[-1].output).judge
        items = [
            judge.JudgeItem(claim.text, tuple(segments[i] for i in claim.segment_indexes))
            for claim in result.claims
        ]
        if result.headline.source == "model":
            body = sorted({i for claim in result.claims for i in claim.segment_indexes})
            items.append(judge.JudgeItem(result.headline.text, tuple(segments[i] for i in body)))
        answers = await ask(client, case.id, items, [segments] * len(items))
        row: dict[str, Any] = {
            "id": case.id,
            "as_specified": [v.model_dump() for v in as_specified.verdicts],
        }
        if isinstance(answers, str):
            row["error"] = answers
        else:
            row["trial"] = [
                {
                    "claim": None if n == len(result.claims) else n,
                    "sentence": item.sentence,
                    "supported": answer.supported,
                    "reason": answer.reason,
                    "context": [s.index for s in questions_answered(item.cited, segments)],
                }
                for n, (item, answer) in enumerate(zip(items, answers, strict=True))
            ]
        out["cases"].append(row)
        OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        print(f"{case.id}: done, ${spend.PHASE6.spent():.4f} spent in Phase 6")

    pairs = load_pairs()
    transcripts = {c.id: ingest(c.text(), c.title).segments for c in cases if not c.expect_error}
    for start in range(0, len(pairs), 13):
        batch = pairs[start : start + 13]
        items = [judge.JudgeItem(pair.sentence, lines_of(pair, cases)[0]) for pair in batch]
        answers = await ask(client, "calibration", items, [transcripts[p.case] for p in batch])
        if isinstance(answers, str):
            out["calibration"].append({"error": answers})
            continue
        out["calibration"] += [
            {
                "id": pair.id,
                "expected": pair.supported,
                "judged": answer.supported,
                "reason": answer.reason,
            }
            for pair, answer in zip(batch, answers, strict=True)
        ]
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"Written to {OUT}. Phase 6 spend so far: ${spend.PHASE6.spent():.4f}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--yes-spend", action="store_true")
    if not parser.parse_args().yes_spend:
        print(f"Would make 12 judge calls, about 45 cents. Spent: ${spend.PHASE6.spent():.4f}.")
        raise SystemExit(2)
    asyncio.run(run())


if __name__ == "__main__":
    main()
