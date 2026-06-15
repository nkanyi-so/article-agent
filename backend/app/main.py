from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import CORS_ORIGINS
from app.evals.schemas import EvalReport  # noqa: F401 — resolves Run.evals forward ref
from app.runs import get_all_runs, get_run, run_form_pipeline, stream_form_pipeline
from app.schemas import FormRequest, HealthResponse, Run, RunResponse, RunsResponse

# EvalReport must be imported before model_rebuild so the forward reference in
# Run.evals: EvalReport | None resolves when FastAPI builds the OpenAPI schema.
Run.model_rebuild()

app = FastAPI(title="article-agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="article-agent", version="0.1.0")


@app.get("/api/runs", response_model=RunsResponse)
async def list_runs() -> RunsResponse:
    return RunsResponse(runs=get_all_runs())


@app.get("/api/runs/{run_id}", response_model=RunResponse)
async def get_run_by_id(run_id: str) -> RunResponse:
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    return RunResponse(run=run)


@app.post("/api/runs", response_model=RunResponse, status_code=201)
async def create_run(
    form: FormRequest,
    evaluate: bool = Query(False, description="Run LLM-judge evals (groundedness + angle_support) in addition to the inline deterministic evals."),
) -> RunResponse:
    """Execute the form-door pipeline and return the resulting Run.

    - 201 + run on success (status "completed").
    - 200 + run on ambiguous Apollo match (status "needs_disambiguation").
    - HTTP error (4xx/5xx) when status == "failed", with {code, message, retryable}.

    Pass ?evaluate=true to also run the two LLM-judge evals and attach a full
    EvalReport (all four verdicts) to run.evals.
    """
    run = await run_form_pipeline(form, evaluate=evaluate)

    if run.status == "failed" and run.error:
        raise HTTPException(
            status_code=run.error.http_status,
            detail=run.error.model_dump(exclude={"http_status"}),
        )

    return RunResponse(run=run)


@app.post("/api/runs/stream")
async def stream_run(
    form: FormRequest,
    evaluate: bool = Query(False, description="Also run LLM-judge evals (groundedness + angle_support)."),
) -> StreamingResponse:
    """Execute the pipeline and stream SSE events as each stage completes.

    Returns a ``text/event-stream`` response. Events emitted in order:

    .. code-block:: text

        event: run_started
        data: {"run_id": "...", "created_at": "...", "input": {...}}

        event: stage_started
        data: {"name": "ingest"}

        event: stage_completed
        data: {"stage": {"name": "ingest", "status": "ok", ...}}

        ... (stage_started / stage_completed for enrich, research, draft)

        event: evaluating       # only when ?evaluate=true
        data: {}

        event: run_completed    # terminal — success
        data: {"run": {...}}

        # OR

        event: needs_disambiguation   # terminal — user must pick a candidate
        data: {"run_id": "...", "candidates": [...]}

        # OR

        event: run_failed       # terminal — pipeline error
        data: {"run": {...}}

    The run is stored in the in-memory store on every terminal event so that
    GET /api/runs/{id} is immediately available after the stream ends.
    """

    async def _event_stream() -> AsyncIterator[str]:
        async for event_name, payload in stream_form_pipeline(form, evaluate=evaluate):
            yield f"event: {event_name}\ndata: {payload.model_dump_json()}\n\n"

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/runs/{run_id}/evals", response_model=RunResponse)
async def run_evals_for_stored_run(run_id: str) -> RunResponse:
    """Score a stored run with all four evals (including both LLM judges).

    Looks up the stored run, runs all evals with a real Opus judge, writes
    the EvalReport back into the store, and returns the updated run.

    404 if the run id is not in the in-memory store.
    """
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

    try:
        from app.clients import ClaudeClient
        from app.evals.base import run_all_evals
        from app.evals.judge import JudgeClient

        claude = ClaudeClient()
        judge = JudgeClient(claude)
        run.evals = await run_all_evals(run, judge)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Eval failed: {exc}") from exc

    return RunResponse(run=run)
