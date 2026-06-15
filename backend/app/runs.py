from __future__ import annotations

import logging
import time
import uuid
from asyncio import CancelledError
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from pydantic import BaseModel

from app.clients import Clients
from app.errors import PipelineError
from app.schemas import (
    DraftResult,
    EnrichResult,
    EvaluatingEvent,
    FormRequest,
    NeedsDisambiguationEvent,
    Run,
    RunCompletedEvent,
    RunFailedEvent,
    RunStartedEvent,
    Source,
    StageCompletedEvent,
    StageError,
    StageOutput,
    StageStartedEvent,
)
from app.stages.draft import draft
from app.stages.enrich import enrich
from app.stages.ingest import ingest
from app.stages.research import research

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory run store  (lost on restart — Phase-1 scope)
# ---------------------------------------------------------------------------

_store: dict[str, Run] = {}


def get_all_runs() -> list[Run]:
    return list(_store.values())


def get_run(run_id: str) -> Run | None:
    return _store.get(run_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ms(t0: float) -> int:
    """Elapsed milliseconds since t0 (from time.perf_counter())."""
    return int((time.perf_counter() - t0) * 1000)


def _error_envelope(name: str, t0: float, exc: PipelineError) -> StageOutput:
    """Build a failed StageOutput for the stage that raised exc."""
    return StageOutput(
        name=name,
        status="error",
        duration_ms=_ms(t0),
        error=StageError(
            code=exc.code,
            message=str(exc),
            retryable=exc.retryable,
            http_status=exc.http_status,
        ),
    )


def _placeholder_stage(name: str) -> StageOutput:
    """Placeholder for a stage that was never reached due to an earlier failure."""
    return StageOutput(
        name=name,
        status="error",
        duration_ms=0,
        error=StageError(
            code="not_reached",
            message="Stage not reached — an earlier stage failed.",
            http_status=500,
        ),
    )


def _dedup_sources(sources: list[Source]) -> list[Source]:
    seen: set[str] = set()
    out: list[Source] = []
    for s in sources:
        if s.id not in seen:
            seen.add(s.id)
            out.append(s)
    return out


# ---------------------------------------------------------------------------
# Streaming pipeline (async generator — the source of truth)
# ---------------------------------------------------------------------------


async def stream_form_pipeline(
    form: FormRequest,
    *,
    evaluate: bool = False,
) -> AsyncIterator[tuple[str, BaseModel]]:
    """Four-stage pipeline that yields SSE events as each stage progresses.

    Yields ``(event_name, payload)`` pairs:
      run_started          → RunStartedEvent
      stage_started        → StageStartedEvent        (before every stage)
      stage_completed      → StageCompletedEvent      (after every stage)
      needs_disambiguation → NeedsDisambiguationEvent  (terminal)
      evaluating           → EvaluatingEvent           (only when evaluate=True)
      run_completed        → RunCompletedEvent         (terminal, success)
      run_failed           → RunFailedEvent            (terminal, failure)

    The final Run is stored in _store before the terminal event is yielded so
    that GET /api/runs/{id} is immediately available.

    Cancellation (client disconnect) propagates via CancelledError; the
    ``finally`` block closes Clients regardless.
    """
    run_id = uuid.uuid4().hex
    created_at = datetime.now(timezone.utc)
    all_sources: list[Source] = []

    ingest_stage = _placeholder_stage("ingest")
    enrich_stage = _placeholder_stage("enrich")
    research_stage: StageOutput | None = None
    draft_stage: StageOutput | None = None
    clients: Clients | None = None

    yield "run_started", RunStartedEvent(
        run_id=run_id, created_at=created_at, input=form
    )

    try:
        clients = Clients()

        # ── Stage 1: Ingest ────────────────────────────────────────────────
        yield "stage_started", StageStartedEvent(name="ingest")
        t0 = time.perf_counter()
        try:
            brief, _ = await ingest(form)
            ingest_stage = StageOutput(
                name="ingest",
                status="ok",
                duration_ms=_ms(t0),
                output=brief,
            )
        except PipelineError as exc:
            ingest_stage = _error_envelope("ingest", t0, exc)
            yield "stage_completed", StageCompletedEvent(stage=ingest_stage)
            raise
        yield "stage_completed", StageCompletedEvent(stage=ingest_stage)

        # ── Stage 2: Enrich ────────────────────────────────────────────────
        yield "stage_started", StageStartedEvent(name="enrich")
        t0 = time.perf_counter()
        try:
            enrich_result, enrich_sources = await enrich(brief, clients.apollo)
            enrich_stage = StageOutput(
                name="enrich",
                status="ok",
                duration_ms=_ms(t0),
                sources=enrich_sources,
                output=enrich_result,
            )
            all_sources.extend(enrich_sources)
        except PipelineError as exc:
            enrich_stage = _error_envelope("enrich", t0, exc)
            yield "stage_completed", StageCompletedEvent(stage=enrich_stage)
            raise
        yield "stage_completed", StageCompletedEvent(stage=enrich_stage)

        # Ambiguous — surface candidates and stop.
        if enrich_result.status == "ambiguous":
            run = Run(
                id=run_id,
                created_at=created_at,
                input=form,
                status="needs_disambiguation",
                ingest=ingest_stage,
                enrich=enrich_stage,
                sources=_dedup_sources(all_sources),
            )
            _store[run_id] = run
            yield "needs_disambiguation", NeedsDisambiguationEvent(
                run_id=run_id, candidates=enrich_result.candidates
            )
            return

        # ── Stage 3: Research ──────────────────────────────────────────────
        yield "stage_started", StageStartedEvent(name="research")
        t0 = time.perf_counter()
        try:
            research_result, research_sources = await research(
                brief, enrich_result, clients.exa, clients.claude
            )
            research_stage = StageOutput(
                name="research",
                status="ok",
                duration_ms=_ms(t0),
                sources=research_sources,
                output=research_result,
            )
            all_sources.extend(research_sources)
        except PipelineError as exc:
            research_stage = _error_envelope("research", t0, exc)
            yield "stage_completed", StageCompletedEvent(stage=research_stage)
            raise
        yield "stage_completed", StageCompletedEvent(stage=research_stage)

        # ── Stage 4: Draft ─────────────────────────────────────────────────
        yield "stage_started", StageStartedEvent(name="draft")
        t0 = time.perf_counter()
        try:
            draft_result, draft_sources = await draft(
                brief, enrich_result, research_result, clients.claude
            )
            draft_stage = StageOutput(
                name="draft",
                status="ok",
                duration_ms=_ms(t0),
                sources=draft_sources,
                output=draft_result,
            )
            all_sources.extend(draft_sources)
        except PipelineError as exc:
            draft_stage = _error_envelope("draft", t0, exc)
            yield "stage_completed", StageCompletedEvent(stage=draft_stage)
            raise
        yield "stage_completed", StageCompletedEvent(stage=draft_stage)

        run = Run(
            id=run_id,
            created_at=created_at,
            input=form,
            status="completed",
            ingest=ingest_stage,
            enrich=enrich_stage,
            research=research_stage,
            draft=draft_stage,
            article=draft_result.article,
            claim_source_map=draft_result.claim_source_map,
            sources=_dedup_sources(all_sources),
        )

        # ── Evals ─────────────────────────────────────────────────────────
        try:
            from app.evals.base import run_all_evals, run_deterministic_evals
            from app.evals.judge import JudgeClient

            if evaluate:
                yield "evaluating", EvaluatingEvent()
                judge = JudgeClient(clients.claude)
                run.evals = await run_all_evals(run, judge)
            else:
                run.evals = await run_deterministic_evals(run)
        except CancelledError:
            raise
        except Exception:
            logger.exception("Eval layer failed — run still stored without evals")

        _store[run_id] = run
        yield "run_completed", RunCompletedEvent(run=run)

    except CancelledError:
        # Client disconnected — don't store a partial run.
        logger.info("Stream cancelled for run %s", run_id)
        raise

    except PipelineError as exc:
        stage_err = StageError(
            code=exc.code,
            message=str(exc),
            retryable=exc.retryable,
            http_status=exc.http_status,
        )
        run = Run(
            id=run_id,
            created_at=created_at,
            input=form,
            status="failed",
            ingest=ingest_stage,
            enrich=enrich_stage,
            research=research_stage,
            draft=draft_stage,
            sources=_dedup_sources(all_sources),
            error=stage_err,
        )
        _store[run_id] = run
        yield "run_failed", RunFailedEvent(run=run)

    finally:
        if clients is not None:
            await clients.aclose()


# ---------------------------------------------------------------------------
# Non-streaming wrapper (keeps existing tests + harness working unchanged)
# ---------------------------------------------------------------------------


async def run_form_pipeline(form: FormRequest, *, evaluate: bool = False) -> Run:
    """Drain the streaming generator and return the final Run.

    Preserves the original API used by tests, the harness, and the existing
    POST /api/runs endpoint so nothing external needs to change.
    """
    final_run: Run | None = None

    async for event_name, payload in stream_form_pipeline(form, evaluate=evaluate):
        if event_name in ("run_completed", "run_failed"):
            assert isinstance(payload, (RunCompletedEvent, RunFailedEvent))
            final_run = payload.run
        elif event_name == "needs_disambiguation":
            assert isinstance(payload, NeedsDisambiguationEvent)
            # Reconstruct the partial Run stored in _store for disambiguation.
            final_run = get_run(payload.run_id)

    if final_run is None:  # pragma: no cover
        raise RuntimeError("Pipeline generator completed without a terminal event.")

    return final_run
