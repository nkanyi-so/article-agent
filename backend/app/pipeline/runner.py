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

from pydantic import BaseModel

from app.errors import AppError, RunTimedOut
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
from app.schemas import ExtractResult, GroundResult, IngestResult, StageName, StageRecord

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
    draft: ModelResponse | None = None
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
    ctx.draft = await ctx.call_model("draft", build_draft_request(ctx.ingested, ctx.extract))
    return {"blocks": [block.model_dump(mode="json") for block in ctx.draft.blocks]}


async def _ground(ctx: _Context) -> dict[str, Any]:
    assert ctx.ingested is not None and ctx.extract is not None  # noqa: S101
    assert ctx.draft is not None  # noqa: S101
    ctx.stage_input = {
        "blocks": [block.model_dump(mode="json") for block in ctx.draft.blocks],
        "corrections": [c.model_dump(mode="json") for c in ctx.extract.corrections],
    }
    result = ground(
        ctx.draft.blocks, ctx.ingested.segments, ctx.extract.corrections, ctx.ingested.title
    )
    ctx.state.result = result
    return result.model_dump(mode="json")


# The evaluate stage joins this list in Phase 6.
STAGES: tuple[tuple[StageName, Stage], ...] = (
    ("ingest", _ingest),
    ("extract", _extract),
    ("draft", _draft),
    ("ground", _ground),
)


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
) -> AsyncIterator[AnyRunEvent]:
    """Runs the stages in order, writing to `state` and yielding events."""
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
        for name, stage in STAGES:
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
