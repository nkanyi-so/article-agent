"""The runner: the only place that knows the stage order.

It calls each stage in turn, writes a stage record before and after each one, keeps a
record of every model call, and yields events. Whatever happens (a refusal, a model
error, a timeout, an unexpected exception) the stream ends with exactly one terminal
event. If the consumer goes away mid-run no event can be sent, so the run's stored
state is closed as failed instead: a run is never left "running".
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from app.errors import AppError, FixtureMiss, ReplayNotPossible, RunTimedOut
from app.evals import checks, judge
from app.evals.schemas import EvalReport, JudgeResult
from app.events import (
    AnyRunEvent,
    RunCompleted,
    RunFailed,
    RunStarted,
    StageCompleted,
    StageStarted,
)
from app.model.payload import request_key
from app.model.types import ModelClient, ModelRequest, ModelResponse
from app.pipeline.draft import build_draft_request
from app.pipeline.extract import build_extract_request, parse_extract
from app.pipeline.ground import ground
from app.pipeline.ingest import ingest
from app.schemas import (
    DraftBlock,
    ExtractResult,
    GroundResult,
    IngestResult,
    StageName,
    StageRecord,
)

logger = logging.getLogger(__name__)

# A hard ceiling on a whole run, in seconds (decisions/0005).
RUN_CEILING_S = 240.0


class ModelCallRecord(BaseModel):
    """One call to a model: the request and response in full, and what it cost."""

    stage: StageName
    request_key: str
    source: Literal["live", "fixture"]
    model_requested: str
    model_served: str
    stop_reason: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    attempts: int
    request: ModelRequest
    response: ModelResponse


class FailedModelCall(BaseModel):
    """A model call that was billed although its response could not be used."""

    stage: StageName
    request_key: str
    source: Literal["live", "fixture"]
    model_requested: str
    error: str
    cost_usd: float


class RunState(BaseModel):
    """Everything a run has stored so far. Created before the first event."""

    run_id: str
    status: Literal["running", "completed", "failed"] = "running"
    error: str | None = None
    stages: list[StageRecord] = []
    model_calls: list[ModelCallRecord] = []
    failed_calls: list[FailedModelCall] = []
    result: GroundResult | None = None

    def cost_usd(self) -> float:
        """Everything this run was billed, including calls whose responses were unusable."""
        calls = sum(call.cost_usd for call in self.model_calls)
        return round(calls + sum(call.cost_usd for call in self.failed_calls), 6)


@dataclass
class _Context:
    text: str
    title: str
    client: ModelClient
    state: RunState
    ingested: IngestResult | None = None
    extract: ExtractResult | None = None
    draft_blocks: list[DraftBlock] | None = None
    stage_input: dict[str, Any] = field(default_factory=dict)

    async def call_model(self, stage: StageName, request: ModelRequest) -> ModelResponse:
        try:
            response = await self.client.complete(request)
        except AppError as error:
            if error.cost_usd is not None:
                self.state.failed_calls.append(
                    FailedModelCall(
                        stage=stage,
                        request_key=request_key(request),
                        source=self.client.source,
                        model_requested=request.model,
                        error=error.code,
                        cost_usd=error.cost_usd,
                    )
                )
            raise
        self.state.model_calls.append(
            ModelCallRecord(
                stage=stage,
                request_key=request_key(request),
                source=self.client.source,
                model_requested=request.model,
                model_served=response.model,
                stop_reason=response.stop_reason,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                cost_usd=response.cost_usd,
                latency_ms=response.latency_ms,
                attempts=response.attempts,
                request=request,
                response=response,
            )
        )
        return response


Stage = Callable[[_Context], Awaitable[dict[str, Any]]]


async def _ingest(ctx: _Context) -> dict[str, Any]:
    ctx.stage_input = {"title": ctx.title, "transcript": ctx.text}
    ctx.ingested = ingest(ctx.text, ctx.title)
    return ctx.ingested.model_dump(mode="json")


async def _extract(ctx: _Context) -> dict[str, Any]:
    assert ctx.ingested is not None  # noqa: S101
    ctx.stage_input = {"segments": len(ctx.ingested.segments), "title": ctx.ingested.title}
    response = await ctx.call_model("extract", build_extract_request(ctx.ingested))
    ctx.extract = parse_extract(response, len(ctx.ingested.segments))
    return ctx.extract.model_dump(mode="json")


async def _draft(ctx: _Context) -> dict[str, Any]:
    assert ctx.ingested is not None and ctx.extract is not None  # noqa: S101
    ctx.stage_input = {"extract": ctx.extract.model_dump(mode="json")}
    response = await ctx.call_model("draft", build_draft_request(ctx.ingested, ctx.extract))
    ctx.draft_blocks = response.blocks
    return {"blocks": [block.model_dump(mode="json") for block in ctx.draft_blocks]}


async def _ground(ctx: _Context) -> dict[str, Any]:
    assert ctx.ingested is not None and ctx.extract is not None  # noqa: S101
    assert ctx.draft_blocks is not None  # noqa: S101
    ctx.stage_input = {
        "blocks": [block.model_dump(mode="json") for block in ctx.draft_blocks],
        "corrections": [c.model_dump(mode="json") for c in ctx.extract.corrections],
    }
    result = ground(
        ctx.draft_blocks, ctx.ingested.segments, ctx.extract.corrections, ctx.ingested.title
    )
    ctx.state.result = result
    return result.model_dump(mode="json")


async def _judge(ctx: _Context, failed_in_code: set[int]) -> JudgeResult:
    """Asks the judge about the sentences the code has not already failed. A judge that
    cannot be used is recorded as that, and the article stands: it is not a verdict."""
    assert ctx.ingested is not None and ctx.state.result is not None  # noqa: S101
    decided, ask = judge.questions(ctx.state.result, ctx.ingested.segments, failed_in_code)
    items = [item for _, item in ask]
    if not items:
        # Every sentence failed a code check and there is no model headline: nothing to ask,
        # so no call is made and nothing is billed. The code's verdicts are the result.
        return JudgeResult(
            outcome="judged",
            verdicts=decided,
            score=judge.score(decided),
            score_alone=judge.score_alone(decided),
        )
    request = judge.build_judge_request(items)
    try:
        response = await ctx.call_model("evaluate", request)
        judgements = judge.parse_judgement(response, items)
    except FixtureMiss:
        # A missing recording is a broken setup, not a judge that failed. Say so loudly.
        raise
    except AppError as error:
        return JudgeResult(outcome="failed", error=error.code, model=request.model)
    verdicts = judge.verdicts_from(decided, ask, judgements)
    return JudgeResult(
        outcome="judged",
        model=response.model,
        verdicts=verdicts,
        score=judge.score(verdicts),
        score_alone=judge.score_alone(verdicts),
    )


async def _evaluate(ctx: _Context) -> dict[str, Any]:
    """Checks the run from its own stored records, then asks the judge."""
    assert ctx.state.result is not None  # noqa: S101
    ctx.stage_input = {"claims": len(ctx.state.result.claims)}
    view = checks.view_of(
        ctx.state.stages[:-1], [call.stage for call in ctx.state.model_calls], ctx.state.status
    )
    cites, uncited = checks.cites_existing(view)
    facts, unsupported = checks.facts_in_cited_text(view)
    drafted, removed = checks.removal(view)
    report = EvalReport(
        checks=[checks.structural(view, upto="ground", finished=False), cites, facts],
        judge=await _judge(ctx, uncited | unsupported),
        drafted=drafted,
        removed=removed,
        removal_rate=removed / drafted if drafted else 0.0,
    )
    return report.model_dump(mode="json")


STAGES: tuple[tuple[StageName, Stage], ...] = (
    ("ingest", _ingest),
    ("extract", _extract),
    ("draft", _draft),
    ("ground", _ground),
    ("evaluate", _evaluate),
)


STAGE_NAMES: tuple[StageName, ...] = tuple(name for name, _ in STAGES)
# The stages a run can be re-run from: the ones this runner executes. Keep in step with STAGES.
RunnableStage = Literal["ingest", "extract", "draft", "ground", "evaluate"]


@dataclass(frozen=True)
class Resume:
    """Re-run from `from_stage`: earlier stages are copied from the parent run's records,
    and the stages from there on are executed again from what those records stored."""

    from_stage: RunnableStage
    parent_run_id: str
    parent_stages: list[StageRecord]


def _restore(ctx: _Context, name: StageName, output: dict[str, Any]) -> None:
    """Puts a copied stage's stored output back where the later stages read it."""
    if name == "ingest":
        ctx.ingested = IngestResult.model_validate(output)
    elif name == "extract":
        ctx.extract = ExtractResult.model_validate(output)
    elif name == "draft":
        ctx.draft_blocks = [DraftBlock.model_validate(block) for block in output["blocks"]]
    elif name == "ground":
        ctx.state.result = GroundResult.model_validate(output)


def _utc_now() -> datetime:
    return datetime.now(UTC)


async def run_pipeline(
    text: str,
    title: str,
    client: ModelClient,
    state: RunState,
    *,
    ceiling_s: float = RUN_CEILING_S,
    now: Callable[[], datetime] = _utc_now,
    resume: Resume | None = None,
) -> AsyncIterator[AnyRunEvent]:
    """Runs the stages in order, writing to `state` and yielding events.

    With `resume`, the stages before `resume.from_stage` are not executed: their records
    are copied from the parent run and marked as copies.
    """
    ctx = _Context(text=text, title=title, client=client, state=state)
    deadline = time.monotonic() + ceiling_s
    seq = 0
    record: StageRecord | None = None

    def next_seq() -> int:
        nonlocal seq
        seq += 1
        return seq

    def fail(code: str, output: dict[str, Any] | None = None) -> RunFailed:
        if record is not None and record.status == "running":
            record.status = "failed"
            record.error = code
            record.input = record.input or ctx.stage_input
            record.output = output
        state.status = "failed"
        state.error = code
        stage = record.name if record is not None else None
        return RunFailed(seq=next_seq(), run_id=state.run_id, error=code, stage=stage)

    try:
        yield RunStarted(seq=0, run_id=state.run_id)
        if resume and resume.from_stage not in STAGE_NAMES:
            # Not a stage this runner executes. Refuse with a terminal event, not an exception.
            yield fail(ReplayNotPossible.code)
            return
        copy_until = STAGE_NAMES.index(resume.from_stage) if resume else 0
        for position, (name, stage) in enumerate(STAGES):
            if resume and position < copy_until:
                parent = next((r for r in resume.parent_stages if r.name == name), None)
                if parent is None or parent.status != "completed" or parent.output is None:
                    # The parent never finished this stage, so there is nothing to copy.
                    record = None
                    yield fail(ReplayNotPossible.code)
                    return
                try:
                    _restore(ctx, name, parent.output)
                except ValidationError, KeyError, TypeError:
                    record = None
                    yield fail(ReplayNotPossible.code)
                    return
                state.stages.append(
                    StageRecord(
                        run_id=state.run_id,
                        seq=len(state.stages),
                        name=name,
                        status="completed",
                        started_at=now(),
                        duration_ms=parent.duration_ms,
                        input=parent.input,
                        output=parent.output,
                        copied_from_run_id=resume.parent_run_id,
                    )
                )
                yield StageCompleted(
                    seq=next_seq(),
                    run_id=state.run_id,
                    stage=name,
                    duration_ms=parent.duration_ms or 0,
                    copied_from_run_id=resume.parent_run_id,
                )
                continue
            if time.monotonic() >= deadline:
                # The ceiling is on the whole run. Checked here as well as inside the stage,
                # because a stage that never waits on anything would never notice it.
                record = None
                yield fail(RunTimedOut.code)
                return
            ctx.stage_input = {}
            record = StageRecord(
                run_id=state.run_id,
                seq=len(state.stages),
                name=name,
                status="running",
                started_at=now(),
            )
            state.stages.append(record)
            yield StageStarted(seq=next_seq(), run_id=state.run_id, stage=name)
            started = time.monotonic()
            try:
                async with asyncio.timeout(max(deadline - started, 0)):
                    output = await stage(ctx)
            except TimeoutError:
                yield fail(RunTimedOut.code)
                return
            except AppError as error:
                partial = getattr(error, "result", None)
                detail = getattr(error, "detail", "")
                logger.warning("run %s failed in %s: %s %s", state.run_id, name, error.code, detail)
                yield fail(error.code, partial.model_dump(mode="json") if partial else None)
                return
            except Exception:
                # The reason goes to the server's log. A client gets a code, never exception text.
                logger.exception("run %s failed in %s", state.run_id, name)
                yield fail("internal_error")
                return
            record.status = "completed"
            record.duration_ms = round((time.monotonic() - started) * 1000)
            record.input = ctx.stage_input
            record.output = output
            yield StageCompleted(
                seq=next_seq(), run_id=state.run_id, stage=name, duration_ms=record.duration_ms
            )
        state.status = "completed"
        yield RunCompleted(seq=next_seq(), run_id=state.run_id)
    finally:
        # Reached with the run still open only if the consumer went away (the generator was
        # closed or cancelled). No event can be sent now; close the stored run instead.
        if state.status == "running":
            fail("cancelled")
