"""The app factory and the HTTP surface. Importing this module needs no key."""

import asyncio
import ipaddress
import logging
import uuid
from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable, Mapping
from contextlib import aclosing
from datetime import datetime
from typing import Annotated, Literal, cast

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.sse import EventSourceResponse
from pydantic import BaseModel, Field, model_validator
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Receive, Scope, Send

from app import __version__
from app.errors import (
    AppError,
    DailyBudgetExhausted,
    InvalidRequest,
    MethodNotAllowed,
    NotFound,
    PasteDisabledInDemo,
    RateLimited,
    RequestTooLarge,
    RunNotFound,
    SeedNotFound,
)
from app.evals.schemas import EvalReport
from app.events import RunEvent, RunFailed
from app.model.fixture import FixtureModelClient
from app.model.types import ModelClient
from app.pipeline.ingest import MAX_WORDS, MIN_TURNS, MIN_WORDS
from app.pipeline.runner import (
    RUN_CEILING_S,
    STAGE_NAMES,
    Resume,
    RunnableStage,
    RunState,
    run_pipeline,
)
from app.schemas import Claim, GroundResult, Headline, RemovedUnit, Segment, StageRecord
from app.seeds import SEEDS, seed
from app.settings import Mode, Settings, load_settings
from app.store import WORST_RUN_USD, RunRow, Store, StoredModelCall, StoredRun, utc_now

logger = logging.getLogger(__name__)

# How a demo run's id says what it is: "s--<seed>--<8 hex>" for a seeded transcript, or
# "<parent id>--r-<stage>--<8 hex>" for a re-run of another run from a stage. Read by
# splitting, never by a pattern that can backtrack: the id comes from an address.
_ID_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-")
_HEX = frozenset("0123456789abcdef")


def read_recipe(run_id: str) -> tuple[Literal["seed", "replay"], str, str] | None:
    """("seed", seed id, "") or ("replay", parent id, stage), or None if it is neither."""
    if len(run_id) > MAX_RECIPE_CHARS + 10 or not set(run_id) <= _ID_CHARS:
        return None
    parts = run_id.rsplit("--", 2)
    if len(parts) != 3 or len(parts[2]) != 8 or not set(parts[2]) <= _HEX:
        return None
    head, middle, _ = parts
    if head == "s" and middle and "--" not in middle:
        return "seed", middle, ""
    if head and middle.startswith("r-") and middle[2:] in STAGE_NAMES:
        return "replay", head, middle[2:]
    return None


MAX_RECIPE_CHARS = 110
MAX_RECIPE_DEPTH = 4

MAX_TRANSCRIPT_CHARS = 200_000


class HealthResponse(BaseModel):
    status: Literal["ok"]
    mode: Mode
    version: str
    store: bool = Field(description="Whether the database answered.")


class SeedSummary(BaseModel):
    id: str
    title: str
    note: str | None = Field(
        default=None, description="Said beside the seed, for example that it was altered."
    )


class SeedText(SeedSummary):
    text: str


class Limits(BaseModel):
    min_turns: int
    min_words: int
    max_words: int
    runs_per_minute: int
    daily_budget_usd: float
    run_ceiling_seconds: float


class ConfigResponse(BaseModel):
    mode: Mode
    paste_enabled: bool
    seeds: list[SeedSummary]
    limits: Limits


class StartRun(BaseModel):
    """Start a run from a seeded transcript, or (in live mode only) from pasted text."""

    seed_id: str | None = Field(default=None, max_length=100)
    transcript: str | None = Field(default=None, max_length=MAX_TRANSCRIPT_CHARS)
    title: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def one_source(self) -> StartRun:
        if (self.seed_id is None) == (self.transcript is None):
            raise ValueError("give either seed_id or transcript, not both and not neither")
        return self


class ReplayRequest(BaseModel):
    from_stage: RunnableStage


class RunsResponse(BaseModel):
    runs: list[RunRow]


class Article(BaseModel):
    """What the ground stage kept and removed, with the transcript sentences it points at.
    Derived from the stored stage records each time; it is not stored twice."""

    headline: Headline
    claims: list[Claim]
    removed: list[RemovedUnit]


class RunDetail(BaseModel):
    run: RunRow
    cost_usd: float
    stages: list[StageRecord]
    model_calls: list[StoredModelCall]
    segments: list[Segment]
    note: str | None = Field(
        default=None,
        description="Said with the run, for example that its draft was altered by hand.",
    )
    article: Article | None
    evaluation: EvalReport | None = Field(
        description="The run's own checks and the judge's verdicts; null until it is evaluated."
    )


class ErrorInfo(BaseModel):
    code: str
    message: str
    retryable: bool
    request_id: str | None


class ErrorBody(BaseModel):
    error: ErrorInfo


class Prepared(BaseModel):
    """A run that is allowed to start: checked before the stream opens, so a refusal is an
    HTTP error with a code and not a broken stream."""

    run: RunRow
    text: str
    title: str
    resume: Resume | None = None

    model_config = {"arbitrary_types_allowed": True}


def build_model_client(settings: Settings) -> ModelClient:
    """The mode is chosen once, here. Demo mode never loads the live client's module."""
    if settings.mode == "live":
        from app.model.live import LiveModelClient

        key = settings.anthropic_api_key
        return LiveModelClient(key.get_secret_value() if key else None)
    return FixtureModelClient(latency_factor=settings.replay_latency)


def _error_response(error: AppError, request: Request) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    body = ErrorBody(
        error=ErrorInfo(
            code=error.code, message=error.message, retryable=error.retryable, request_id=request_id
        )
    )
    # The header is set here as well as by the middleware: a response built by the
    # outermost error handler never passes back through the middleware.
    headers = {"x-request-id": request_id} if request_id else {}
    if isinstance(error, RateLimited):
        headers["retry-after"] = "60"  # the limit is counted over one minute
    return JSONResponse(body.model_dump(), status_code=error.http_status, headers=headers)


class BodyLimitMiddleware:
    """Refuses a request whose declared length is over the limit, before any of it is read,
    in the same error shape as everything else.

    A body sent in chunks with no declared length, or with a false one, is counted as it
    is read by the framework's own limit, set on each route that takes a body; its 413 is
    put in that same shape by the error handlers.
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            declared = dict(scope["headers"]).get(b"content-length", b"").decode("latin-1")
            if declared.isdigit() and int(declared) > self.max_bytes:
                request_id = uuid.uuid4().hex[:12]
                error = RequestTooLarge()
                body = ErrorBody(
                    error=ErrorInfo(
                        code=error.code,
                        message=error.message,
                        retryable=error.retryable,
                        request_id=request_id,
                    )
                )
                response = JSONResponse(
                    body.model_dump(),
                    status_code=error.http_status,
                    headers={"x-request-id": request_id},
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def client_address(headers: Mapping[str, str], peer: str, *, trust_proxy: bool) -> str:
    """The address a run is counted against.

    Without a trusted proxy it is the connection's peer. Behind one, it is the header the
    platform sets, or failing that the right-most forwarded entry, which is the one the
    proxy itself added; the left-most is whatever the caller chose to send. An IPv6
    address is counted by its /64, since one subscriber usually holds the whole block.
    """
    candidate = peer
    if trust_proxy:
        forwarded = headers.get("x-real-ip") or headers.get("x-forwarded-for", "").split(",")[-1]
        candidate = forwarded.strip() or peer
    try:
        address = ipaddress.ip_address(candidate)
    except ValueError:
        return peer
    if isinstance(address, ipaddress.IPv6Address):
        return str(ipaddress.ip_network(f"{address}/64", strict=False))
    return str(address)


def _seed_note(seed_id: str | None) -> str | None:
    try:
        return seed(seed_id).note if seed_id else None
    except KeyError:
        return None


def _detail(stored: StoredRun) -> RunDetail:
    by_name = {record.name: record for record in stored.stages}
    segments: list[Segment] = []
    ingest_record = by_name.get("ingest")
    if ingest_record and ingest_record.output:
        segments = [Segment.model_validate(s) for s in ingest_record.output["segments"]]
    article: Article | None = None
    ground_record = by_name.get("ground")
    if ground_record and ground_record.output:
        result = GroundResult.model_validate(ground_record.output)
        article = Article(headline=result.headline, claims=result.claims, removed=result.removed)
    evaluation: EvalReport | None = None
    evaluate_record = by_name.get("evaluate")
    if evaluate_record and evaluate_record.status == "completed" and evaluate_record.output:
        evaluation = EvalReport.model_validate(evaluate_record.output)
    return RunDetail(
        run=stored.run,
        cost_usd=round(sum(call.cost_usd for call in stored.model_calls), 6),
        stages=stored.stages,
        model_calls=stored.model_calls,
        segments=segments,
        note=_seed_note(stored.run.seed_id),
        article=article,
        evaluation=evaluation,
    )


def create_app(
    settings: Settings | None = None,
    *,
    model_client: ModelClient | None = None,
    now: Callable[[], datetime] = utc_now,
) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="article-agent", version=__version__)
    client = model_client or build_model_client(settings)
    store = Store(settings.database_path)
    store.close_abandoned_runs()
    app.state.model_client = client
    app.state.store = store
    seeding = asyncio.Lock()
    rebuilding = asyncio.Lock()
    seeded = False

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_methods=["GET", "POST"],
        allow_headers=["content-type"],
        expose_headers=["x-request-id"],
    )

    @app.middleware("http")
    async def request_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = uuid.uuid4().hex[:12]
        response = await call_next(request)
        response.headers["x-request-id"] = request.state.request_id
        return response

    # Added last, so it is outermost and sees the body before anything reads it.
    app.add_middleware(BodyLimitMiddleware, max_bytes=settings.max_body_bytes)

    # ------------------------------------------------------------------ errors: one shape
    #
    # A client gets a code, a fixed message and a request id. Never an upstream body, a
    # stack trace, exception text, or its own input echoed back.

    @app.exception_handler(AppError)
    async def app_error(request: Request, error: AppError) -> JSONResponse:
        return _error_response(error, request)

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, _: RequestValidationError) -> JSONResponse:
        return _error_response(InvalidRequest(), request)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, error: StarletteHTTPException) -> JSONResponse:
        if error.status_code == 405:
            return _error_response(MethodNotAllowed(), request)
        if error.status_code == 404:
            return _error_response(NotFound(), request)
        if error.status_code == 413:
            return _error_response(RequestTooLarge(), request)
        generic = AppError()
        generic.http_status = error.status_code
        return _error_response(generic, request)

    @app.exception_handler(Exception)
    async def unexpected(request: Request, error: Exception) -> JSONResponse:
        logger.exception("unhandled error on %s", request.url.path, exc_info=error)
        return _error_response(AppError(), request)

    # ------------------------------------------------------------------ seeded runs

    async def stream_run(prepared: Prepared) -> AsyncIterator[RunEvent]:
        """Runs the pipeline for a prepared run, storing as it goes.

        The run row is written before the first event. Whatever ends the stream, the
        stored run is closed, and if the stream is still open it gets a terminal event:
        that holds even when it is the store itself that fails part-way.
        """
        await asyncio.to_thread(store.create_run, prepared.run)
        await asyncio.to_thread(store.prune_runs, settings.max_stored_runs)
        state = RunState(run_id=prepared.run.id)
        runner = run_pipeline(
            prepared.text, prepared.title, client, state, now=now, resume=prepared.resume
        )
        last_seq = 0
        store_failed = False
        try:
            # `aclosing`, so that if this stream is abandoned the runner is closed at once
            # and marks the run failed, instead of being left for the garbage collector.
            async with aclosing(runner) as events:  # type: ignore[type-var]
                async for event in events:
                    try:
                        await asyncio.to_thread(store.save_state, state, now())
                    except Exception:
                        logger.exception("could not store run %s", state.run_id)
                        store_failed = True
                        break
                    last_seq = event.seq
                    yield RunEvent(event)
            if store_failed:
                state.status, state.error = "failed", "internal_error"
                yield RunEvent(
                    RunFailed(seq=last_seq + 1, run_id=state.run_id, error="internal_error")
                )
        finally:
            try:
                await asyncio.shield(asyncio.to_thread(store.save_state, state, now()))
                await asyncio.shield(asyncio.to_thread(store.prune_runs, settings.max_stored_runs))
            except Exception:
                logger.exception("could not store the final state of run %s", state.run_id)

    async def ensure_seeded() -> None:
        """Creates the seeded runs once per process, by running the real pipeline over the
        recordings, under stable ids so their links always resolve."""
        nonlocal seeded
        if seeded:
            return
        async with seeding:
            if seeded:
                return
            replay = FixtureModelClient()  # always the recordings, even in live mode
            for item in SEEDS:
                run = RunRow(
                    id=f"seed-{item.id}",
                    created_at=now(),
                    mode=settings.mode,
                    source="seed",
                    title=item.title,
                    seed_id=item.id,
                    status="running",
                    pinned=True,
                )
                await asyncio.to_thread(store.create_run, run)
                state = RunState(run_id=run.id)
                async for _ in run_pipeline(item.text(), item.title, replay, state, now=now):
                    pass
                await asyncio.to_thread(store.save_state, state, now())
            seeded = True

    Ready = Annotated[None, Depends(ensure_seeded)]

    # ------------------------------------------------------------------ guards

    def run_guard(request: Request) -> None:
        """Every route that can start a run depends on this: a per-address rate limit, then
        the daily budget against what live calls have cost today and what the live runs
        still going might cost. Decided and recorded in one transaction, so requests that
        arrive together cannot all slip through."""
        admission = store.admit_run(
            address_of(request),
            now(),
            settings.runs_per_minute,
            settings.daily_budget_usd,
            # Only a live run can spend. In demo mode nothing is held back.
            reserve_usd=WORST_RUN_USD if settings.mode == "live" else 0.0,
        )
        if admission == "rate_limited":
            raise RateLimited
        if admission == "budget_exhausted":
            raise DailyBudgetExhausted

    app.state.run_guard = run_guard
    Guarded = Annotated[None, Depends(run_guard)]

    def new_run(
        source: Literal["seed", "paste", "replay"], title: str, recipe: str | None = None
    ) -> RunRow:
        # In demo mode a run is a replay of recordings, so its id can say how to make it
        # again ("s--<seed>" or "<parent>--r-<stage>"). On the host every instance has its
        # own scratch database, and that is what lets any of them answer for the run.
        run_id = uuid.uuid4().hex[:12]
        if settings.mode == "demo" and recipe and len(recipe) <= MAX_RECIPE_CHARS:
            run_id = f"{recipe}--{uuid.uuid4().hex[:8]}"
        return RunRow(
            id=run_id,
            created_at=now(),
            mode=settings.mode,
            source=source,
            title=title,
            status="running",
        )

    def prepare_start(body: StartRun, _ready: Ready, _guard: Guarded) -> Prepared:
        if body.transcript is not None:
            if settings.mode == "demo":
                raise PasteDisabledInDemo
            title = " ".join((body.title or "Untitled transcript").split())
            return Prepared(run=new_run("paste", title), text=body.transcript, title=title)
        try:
            chosen = seed(body.seed_id or "")
        except KeyError:
            raise SeedNotFound from None
        run = new_run("seed", chosen.title, recipe=f"s--{chosen.id}")
        run.seed_id = chosen.id
        return Prepared(run=run, text=chosen.text(), title=chosen.title)

    def address_of(request: Request) -> str:
        peer = request.client.host if request.client else "unknown"
        return client_address(request.headers, peer, trust_proxy=settings.trust_proxy)

    async def find_run(run_id: str, address: str, depth: int = 0) -> StoredRun | None:
        """A stored run, or in demo mode one made again from what its id says.

        Only in demo mode, where making it again costs nothing and gives the same article:
        every call is a recording. The id is matched against two exact shapes before
        anything is done with it, and a chain of re-runs is followed a few steps at most.
        """
        stored = await asyncio.to_thread(store.get_run, run_id)
        if stored is not None or settings.mode != "demo" or depth > MAX_RECIPE_DEPTH:
            return stored
        recipe = read_recipe(run_id)
        if recipe is None:
            return None
        kind, subject, stage = recipe
        if depth == 0:
            # Making a run again is work, and anyone can ask for it. It counts against the
            # asker's allowance like starting a run does; reading a stored run stays free.
            admitted = await asyncio.to_thread(
                store.admit_run,
                address,
                now(),
                settings.runs_per_minute,
                settings.daily_budget_usd,
                reserve_usd=0.0,
            )
            if admitted != "ok":
                raise RateLimited
        # The parent is found (or made) first, outside the lock: the lock is not re-entrant.
        parent = await find_run(subject, address, depth + 1) if kind == "replay" else None
        replay = FixtureModelClient()
        async with rebuilding:
            stored = await asyncio.to_thread(store.get_run, run_id)
            if stored is not None:
                return stored
            if kind == "seed":
                try:
                    chosen = seed(subject)
                except KeyError:
                    return None
                run = RunRow(
                    id=run_id,
                    created_at=now(),
                    mode=settings.mode,
                    source="seed",
                    title=chosen.title,
                    seed_id=chosen.id,
                    status="running",
                )
                text, title, resume = chosen.text(), chosen.title, None
            else:
                record = (
                    next((r for r in parent.stages if r.name == "ingest"), None) if parent else None
                )
                if parent is None or parent.run.seed_id is None or not record or not record.input:
                    return None
                run = RunRow(
                    id=run_id,
                    created_at=now(),
                    mode=settings.mode,
                    source="replay",
                    title=parent.run.title,
                    seed_id=parent.run.seed_id,
                    parent_run_id=parent.run.id,
                    replay_from_stage=stage,
                    status="running",
                )
                text = str(record.input.get("transcript", ""))
                title = str(record.input.get("title", parent.run.title))
                resume = Resume(
                    from_stage=cast(RunnableStage, stage),
                    parent_run_id=parent.run.id,
                    parent_stages=parent.stages,
                )
            await asyncio.to_thread(store.create_run, run)
            state = RunState(run_id=run_id)
            async for _ in run_pipeline(text, title, replay, state, now=now, resume=resume):
                pass
            await asyncio.to_thread(store.save_state, state, now())
            await asyncio.to_thread(store.prune_runs, settings.max_stored_runs)
            return await asyncio.to_thread(store.get_run, run_id)

    async def prepare_replay(
        run_id: str, body: ReplayRequest, request: Request, _ready: Ready, _guard: Guarded
    ) -> Prepared:
        parent = await find_run(run_id, address_of(request))
        if parent is None:
            raise RunNotFound
        if settings.mode == "demo" and parent.run.seed_id is None:
            # A run made from pasted text, in a database shared with live mode. Re-running
            # it would be running pasted text, which demo mode refuses.
            raise PasteDisabledInDemo
        ingest_record = next((r for r in parent.stages if r.name == "ingest"), None)
        if ingest_record is None or not ingest_record.input:
            raise RunNotFound
        run = new_run("replay", parent.run.title, recipe=f"{parent.run.id}--r-{body.from_stage}")
        run.parent_run_id = parent.run.id
        run.replay_from_stage = body.from_stage
        run.seed_id = parent.run.seed_id
        resume = Resume(
            from_stage=body.from_stage, parent_run_id=parent.run.id, parent_stages=parent.stages
        )
        return Prepared(
            run=run,
            text=str(ingest_record.input.get("transcript", "")),
            title=str(ingest_record.input.get("title", parent.run.title)),
            resume=resume,
        )

    app.state.stream_run = stream_run

    # ------------------------------------------------------------------ routes

    # The reading routes are plain functions, so the framework runs them in a worker
    # thread and a slow database never blocks the streams on the event loop.

    @app.get("/health")
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok", mode=settings.mode, version=__version__, store=store.reachable()
        )

    @app.get("/api/config")
    def config() -> ConfigResponse:
        return ConfigResponse(
            mode=settings.mode,
            paste_enabled=settings.mode == "live",
            seeds=[SeedSummary(id=s.id, title=s.title, note=s.note) for s in SEEDS],
            limits=Limits(
                min_turns=MIN_TURNS,
                min_words=MIN_WORDS,
                max_words=MAX_WORDS,
                runs_per_minute=settings.runs_per_minute,
                daily_budget_usd=settings.daily_budget_usd,
                run_ceiling_seconds=RUN_CEILING_S,
            ),
        )

    @app.get("/api/seeds/{seed_id}")
    def seed_text(seed_id: str) -> SeedText:
        try:
            chosen = seed(seed_id)
        except KeyError:
            raise SeedNotFound from None
        return SeedText(id=chosen.id, title=chosen.title, text=chosen.text())

    @app.post(
        "/api/runs/stream",
        response_class=EventSourceResponse,
        max_body_size=settings.max_body_bytes,
    )
    async def start_run(
        prepared: Annotated[Prepared, Depends(prepare_start)],
    ) -> AsyncIterable[RunEvent]:
        async for event in stream_run(prepared):
            yield event

    @app.post(
        "/api/runs/{run_id}/replay/stream",
        response_class=EventSourceResponse,
        max_body_size=settings.max_body_bytes,
    )
    async def replay_run(
        prepared: Annotated[Prepared, Depends(prepare_replay)],
    ) -> AsyncIterable[RunEvent]:
        async for event in stream_run(prepared):
            yield event

    @app.get("/api/runs")
    def list_runs(_ready: Ready) -> RunsResponse:
        return RunsResponse(runs=store.list_runs())

    @app.get("/api/runs/{run_id}")
    async def get_run(run_id: str, request: Request, _ready: Ready) -> RunDetail:
        stored = await find_run(run_id, address_of(request))
        if stored is None:
            raise RunNotFound
        return _detail(stored)

    return app


# The host's Python runtime looks for a module-level ASGI application.
app = create_app()
