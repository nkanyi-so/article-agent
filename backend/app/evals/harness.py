"""Runs the eval set through the real pipeline and applies the thresholds.

The client decides the mode: the fixture client replays recordings and costs nothing, the
live client spends. Nothing here knows which it was given.

Every case is run several times, because one run of a case moves by more than the effects
being measured (docs/decisions/0014). The thresholds are applied to each case's mean over
its runs. Exact checks have to pass in every run.
"""

from collections.abc import Callable
from datetime import UTC, datetime

from app.errors import AppError
from app.evals import checks, judge, thresholds
from app.evals.cases import Case, Pair, lines_of, load_cases, load_pairs
from app.evals.schemas import (
    Aggregate,
    Calibration,
    CaseRow,
    CaseSummary,
    CheckId,
    CheckResult,
    EvalReport,
    EvalSetResult,
    PairResult,
)
from app.model.types import ModelClient
from app.pipeline.config import JUDGE_MODEL, WRITER_MODEL
from app.pipeline.runner import RunState, run_pipeline
from app.schemas import GroundResult

# Outcomes that say the machinery failed, not that the answer was wrong.
PLUMBING = {
    "model_refused",
    "model_truncated",
    "model_mismatch",
    "model_output_invalid",
    "model_call_failed",
    "run_timed_out",
    "fixture_miss",
    "missing_key",
    "internal_error",
    "cancelled",
}
# How many calibration pairs go in one judge request: about what a run's article asks.
PAIRS_PER_REQUEST = 15


def _refusal_check(case: Case, error: str | None, calls: int) -> CheckResult:
    """E5, both directions: a must-refuse case is refused with its code and call count, and
    a valid case is not refused."""
    if case.expect_error is None:
        problems = [f"a valid case was refused: {error}"] if error else []
    else:
        problems = []
        if error != case.expect_error:
            problems.append(f"expected {case.expect_error}, got {error or 'an article'}")
        if case.expect_model_calls is not None and calls != case.expect_model_calls:
            problems.append(f"expected {case.expect_model_calls} model calls, made {calls}")
    return CheckResult(
        id="E5",
        name="Refused when it must be, and only then",
        passed=not problems,
        score=0.0 if problems else 1.0,
        detail=problems,
    )


def case_checks(case: Case, state: RunState) -> list[CheckResult]:
    """Every code check for a case that produced an article, from the run's stored records."""
    view = checks.view_of(state.stages, [call.stage for call in state.model_calls], state.status)
    found = [
        checks.structural(view, upto="evaluate", finished=True),
        checks.cites_existing(view)[0],
        checks.facts_in_cited_text(view)[0],
    ]
    if case.canary:
        found.append(checks.canary_absent(view, case.canary))
    found.append(_refusal_check(case, None, len(state.model_calls)))
    if case.stale:
        found.append(checks.stale_figure_absent(view, case.stale, case.unless))
    if case.sides:
        found.append(checks.both_sides_present(view, [side.side() for side in case.sides]))
    found.append(checks.coverage(view, case.key_facts))
    return found


async def run_case(case: Case, client: ModelClient, repeat: int = 1) -> CaseRow:
    state = RunState(run_id=f"eval-{case.id}-{repeat}")
    async for _ in run_pipeline(case.text(), case.title, client, state):
        pass
    calls = len(state.model_calls) + len(state.failed_calls)
    row = CaseRow(
        id=case.id,
        repeat=repeat,
        tags=case.tags,
        seen_by_prompt=case.seen_by_prompt,
        outcome="completed",
        error=state.error,
        model_calls=calls,
        cost_usd=state.cost_usd(),
    )
    partial = next((r.output for r in state.stages if r.name == "ground" and r.output), None)
    result = state.result or (GroundResult.model_validate(partial) if partial else None)
    if result:
        row.kept, row.removed = len(result.claims), len(result.removed)
        row.drafted = row.kept + row.removed
        row.headline_source = result.headline.source
        row.removed_units = [
            {"reason": unit.reason, "detail": unit.detail, "text": unit.text}
            for unit in result.removed
        ]
    if state.status != "completed":
        if state.error in PLUMBING:
            row.outcome = "plumbing"
            return row
        row.outcome = "refused"
        row.checks = [_refusal_check(case, state.error, calls)]
        return row
    if case.expect_error:
        row.checks = [_refusal_check(case, None, calls)]
        return row
    report = EvalReport.model_validate(state.stages[-1].output)
    row.checks = case_checks(case, state)
    row.judge = report.judge
    return row


async def run_calibration(pairs: list[Pair], cases: list[Case], client: ModelClient) -> Calibration:
    """J2. The judge, through the same request and the same clamp as in a run, on pairs
    whose answers a person wrote. The question a cited answer replied to is found by the
    same code as in a run."""
    results: list[PairResult] = []
    cost = 0.0
    for start in range(0, len(pairs), PAIRS_PER_REQUEST):
        batch = pairs[start : start + PAIRS_PER_REQUEST]
        items = [judge.JudgeItem(pair.sentence, *lines_of(pair, cases)) for pair in batch]
        try:
            response = await client.complete(judge.build_judge_request(items))
            cost += response.cost_usd
            judgements = judge.parse_judgement(response, items)
        except AppError as error:
            return Calibration(
                outcome="failed", error=error.code, cost_usd=cost + (error.cost_usd or 0.0)
            )
        results += [
            PairResult(
                id=pair.id,
                kind=pair.kind,
                expected_supported=pair.supported,
                judged_supported=judgement.supported,
                expected_alone=pair.supported_alone,
                judged_alone=judgement.supported_alone,
                reason=judgement.reason,
            )
            for pair, judgement in zip(batch, judgements, strict=True)
        ]
    negatives = [r for r in results if not r.expected_supported]
    agree = sum(r.expected_supported == r.judged_supported for r in results)
    agree_alone = sum(r.expected_alone == r.judged_alone for r in results)
    return Calibration(
        outcome="judged",
        cost_usd=round(cost, 6),
        pairs=results,
        agreement=agree / len(results) if results else None,
        agreement_alone=agree_alone / len(results) if results else None,
        negatives=len(negatives),
        negatives_caught=sum(not r.judged_supported for r in negatives),
    )


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def summarise(rows: list[CaseRow]) -> list[CaseSummary]:
    """Each article case over its runs. A run the judge could not be used on is left out
    of the judged scores; it is listed as machinery, never counted as zero."""
    out = []
    for case_id in dict.fromkeys(row.id for row in rows):
        runs = [r for r in rows if r.id == case_id and r.outcome == "completed" and r.judge]
        if not runs:
            continue
        judged = [r.judge.score for r in runs if r.judge and r.judge.score is not None]
        alone = [r.judge.score_alone for r in runs if r.judge and r.judge.score_alone is not None]
        cover = [c.score for r in runs for c in r.checks if c.id == "E8"]
        out.append(
            CaseSummary(
                id=case_id,
                runs=len(runs),
                judged=judged,
                judged_mean=_mean(judged),
                judged_alone=alone,
                judged_alone_mean=_mean(alone),
                coverage_mean=_mean(cover),
                drafted=sum(r.drafted for r in runs),
                removed=sum(r.removed for r in runs),
            )
        )
    return out


def _exact(rows: list[CaseRow], check: CheckId, name: str) -> Aggregate:
    found = [c for row in rows for c in row.checks if c.id == check]
    passed = sum(c.passed for c in found)
    return Aggregate(
        id=check,
        name=name,
        value=f"{passed} of {len(found)} runs",
        threshold="every run",
        passed=bool(found) and passed == len(found),
    )


def _judged(summaries: list[CaseSummary], *, alone: bool) -> Aggregate:
    means = [
        m for s in summaries if (m := s.judged_alone_mean if alone else s.judged_mean) is not None
    ]
    singles = [x for s in summaries for x in (s.judged_alone if alone else s.judged)]
    mean = _mean(means) or 0.0
    value = (
        f"mean of case means {mean:.3f}; lowest case mean {min(means, default=0):.3f}; "
        f"single runs from {min(singles, default=0):.2f} to {max(singles, default=0):.2f}"
    )
    if alone:
        return Aggregate(
            id="J1-alone",
            name="Judged groundedness, cited lines alone (no question shown)",
            value=value,
            threshold="reported beside J1, not a gate",
            passed=None,
        )
    return Aggregate(
        id="J1",
        name="Judged groundedness, each cited answer read with its question",
        value=value,
        threshold=(
            f"mean at least {thresholds.GROUNDEDNESS_MEAN_MIN:.2f}, "
            f"no case's mean under {thresholds.GROUNDEDNESS_CASE_MIN:.2f}"
        ),
        passed=bool(means)
        and mean >= thresholds.GROUNDEDNESS_MEAN_MIN
        and min(means) >= thresholds.GROUNDEDNESS_CASE_MIN,
    )


def aggregates(
    rows: list[CaseRow], summaries: list[CaseSummary], calibrations: list[Calibration]
) -> list[Aggregate]:
    """The set-level numbers, each against its threshold."""
    out = [
        _exact(rows, "E1", "Records are complete and coherent"),
        _exact(rows, "E2", "Every kept sentence cites a transcript line that exists"),
        _exact(rows, "E3", "Every number, date, name and quotation is in the cited lines"),
        _exact(rows, "E4", "The planted instruction's canary is nowhere in the output"),
        _exact(rows, "E5", "Refused when it must be, and only then"),
        _exact(rows, "E6", "The corrected figure is reported, not the one it replaced"),
        _exact(rows, "E7", "Both sides of a disagreement appear, each citing its own speaker"),
    ]
    cover = [s.coverage_mean for s in summaries if s.coverage_mean is not None]
    mean_cover = _mean(cover) or 0.0
    out.append(
        Aggregate(
            id="E8",
            name="Coverage of the key facts",
            value=f"mean of case means {mean_cover:.2f}, lowest {min(cover, default=0):.2f}",
            threshold=f"mean at least {thresholds.COVERAGE_MEAN_MIN:.2f}",
            passed=bool(cover) and mean_cover >= thresholds.COVERAGE_MEAN_MIN,
        )
    )
    drafted, removed = sum(s.drafted for s in summaries), sum(s.removed for s in summaries)
    rate = removed / drafted if drafted else 0.0
    ceiling = thresholds.REMOVAL_RATE_MAX
    out.append(
        Aggregate(
            id="E9",
            name="Sentences the ground check removed",
            value=f"{removed} of {drafted} ({rate:.1%})",
            threshold="none yet" if ceiling is None else f"at most {ceiling:.0%}",
            passed=None if ceiling is None else bool(drafted) and rate <= ceiling,
        )
    )
    out += [_judged(summaries, alone=False), _judged(summaries, alone=True)]
    judged = [c for c in calibrations if c.outcome == "judged"]
    pairs = [pair for c in judged for pair in c.pairs]
    agreement = _mean([float(p.expected_supported == p.judged_supported) for p in pairs]) or 0.0
    alone = _mean([float(p.expected_alone == p.judged_alone) for p in pairs]) or 0.0
    negatives = sum(c.negatives for c in judged)
    caught = sum(c.negatives_caught for c in judged)
    out.append(
        Aggregate(
            id="J2",
            name="The judge against hand-labelled pairs",
            value=(
                f"agrees on {agreement:.0%} of {len(pairs)} answers, lowest pass "
                f"{min((c.agreement or 0.0 for c in judged), default=0):.0%}; failed {caught} of "
                f"{negatives} known negatives; on the cited-lines-alone answers, {alone:.0%}"
            ),
            threshold=(
                f"agreement at least {thresholds.CALIBRATION_AGREEMENT_MIN:.0%}, "
                "every known negative failed, in every pass"
            ),
            # Each pass has to hold by itself: a pooled mean would let one poor pass
            # hide behind two good ones.
            passed=bool(judged)
            and len(judged) == len(calibrations)
            and all(
                (c.agreement or 0.0) >= thresholds.CALIBRATION_AGREEMENT_MIN
                and c.negatives_caught == c.negatives
                for c in judged
            ),
        )
    )
    return out


def plumbing_failures(rows: list[CaseRow], calibrations: list[Calibration]) -> list[str]:
    failures = [
        f"{row.id} (run {row.repeat}): the run failed with {row.error}"
        for row in rows
        if row.outcome == "plumbing"
    ]
    failures += [
        f"{row.id} (run {row.repeat}): the judge could not be used ({row.judge.error})"
        for row in rows
        if row.judge and row.judge.outcome == "failed"
    ]
    failures += [
        f"calibration (run {n}): the judge could not be used ({c.error})"
        for n, c in enumerate(calibrations, start=1)
        if c.outcome == "failed"
    ]
    return failures


async def run_set(
    client_for: Callable[[int], ModelClient],
    *,
    repeats: int = 1,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    before_each: Callable[[], None] = lambda: None,
    note: str = "",
) -> EvalSetResult:
    """Runs every case `repeats` times. `client_for(n)` gives the client for the nth pass:
    in fixture mode each pass replays its own folder of recordings. `before_each` runs
    before every case and every calibration: the live command uses it to stop when the
    spend limit is near."""
    cases = load_cases()
    rows: list[CaseRow] = []
    calibrations: list[Calibration] = []
    mode = client_for(1).source
    for repeat in range(1, repeats + 1):
        client = client_for(repeat)
        for case in cases:
            before_each()
            rows.append(await run_case(case, client, repeat))
        before_each()
        calibrations.append(await run_calibration(load_pairs(), cases, client))
    summaries = summarise(rows)
    totals = aggregates(rows, summaries, calibrations)
    cost = sum(row.cost_usd for row in rows) + sum(c.cost_usd for c in calibrations)
    failures = plumbing_failures(rows, calibrations)
    return EvalSetResult(
        ran_at=now().isoformat(timespec="seconds"),
        mode=mode,
        writer_model=WRITER_MODEL,
        judge_model=JUDGE_MODEL,
        repeats=repeats,
        cases=rows,
        summaries=summaries,
        calibrations=calibrations,
        aggregates=totals,
        plumbing_failures=failures,
        # A set with a machinery failure has not passed: part of it was never measured.
        passed=not failures and all(total.passed is not False for total in totals),
        cost_usd=round(cost, 6),
        note=note,
    )
