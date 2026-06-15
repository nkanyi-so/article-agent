from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, model_validator

if TYPE_CHECKING:
    from app.evals.schemas import EvalReport


# ---------------------------------------------------------------------------
# Existing response models (unchanged)
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


# ---------------------------------------------------------------------------
# Pipeline primitives
# ---------------------------------------------------------------------------


class Source(BaseModel):
    """A single retrieved source that grounds a factual claim."""

    id: str  # stable slug, e.g. "apollo:person:<id>", "exa:3"
    kind: Literal["apollo", "exa"]
    url: str | None = None
    title: str | None = None
    snippet: str | None = None  # excerpt actually used for grounding
    retrieved_at: datetime


class StageError(BaseModel):
    """Serialisable error record attached to a failed stage or Run."""

    code: str
    message: str
    retryable: bool = False
    http_status: int = 500  # used by the route handler to pick the response status


class StageOutput(BaseModel):
    """Envelope wrapping any stage's typed output with timing and sources.

    ``output`` is typed as Any because Python generic specialisations
    (StageOutput[Brief] etc.) are expensive at runtime and unnecessary here —
    the stage functions themselves carry full typed signatures, and the JSON
    serialisation is identical regardless of the type parameter.
    Type aliases below document the expected output type for each stage.
    """

    name: str
    status: Literal["ok", "error"]
    duration_ms: int
    sources: list[Source] = []
    output: Any = None  # Brief | EnrichResult | ResearchResult | DraftResult
    error: StageError | None = None


# Aliases — for documentation / IDE hints (not runtime specialisations).
IngestStage = StageOutput    # output: Brief
EnrichStage = StageOutput    # output: EnrichResult
ResearchStage = StageOutput  # output: ResearchResult
DraftStage = StageOutput     # output: DraftResult


# ---------------------------------------------------------------------------
# Stage 1 — Ingest
# ---------------------------------------------------------------------------


class Brief(BaseModel):
    """Normalised form input ready for downstream stages."""

    name: str | None = None
    linkedin_url: str | None = None
    company: str | None = None
    display_name: str
    search_terms: list[str]


# ---------------------------------------------------------------------------
# Stage 2 — Enrich (Apollo)
# ---------------------------------------------------------------------------


class PersonFacts(BaseModel):
    """High-confidence Apollo person record."""

    apollo_id: str | None = None
    name: str | None = None
    title: str | None = None
    organization: str | None = None
    organization_domain: str | None = None
    linkedin_url: str | None = None
    location: str | None = None
    raw: dict[str, Any] = {}  # trimmed Apollo payload kept for traceability


class EnrichCandidate(BaseModel):
    """One Apollo search hit returned when the match is ambiguous."""

    apollo_id: str | None = None
    name: str | None = None
    title: str | None = None
    organization: str | None = None
    linkedin_url: str | None = None
    confidence: float | None = None  # rank-based heuristic (1 = best)


class EnrichResult(BaseModel):
    status: Literal["matched", "ambiguous"]
    person: PersonFacts | None = None      # set when status == "matched"
    candidates: list[EnrichCandidate] = [] # set when status == "ambiguous"


# ---------------------------------------------------------------------------
# Stage 3 — Research (Exa + Claude)
# ---------------------------------------------------------------------------


class ChosenAngle(BaseModel):
    """Claude's structured pick of the best newsworthy angle.

    ``supporting_source_ids`` must be a non-empty subset of the Exa source
    IDs passed in the prompt — validated by the research stage after parsing.
    """

    headline: str
    angle: str          # one-sentence newsworthy hook
    rationale: str
    supporting_source_ids: list[str]


class ResearchResult(BaseModel):
    angle: ChosenAngle
    sources: list[Source]  # Exa hits given to Claude
    angle_fallback: bool = False  # True when Claude returned no valid source IDs


# ---------------------------------------------------------------------------
# Stage 4 — Draft (Claude)
# ---------------------------------------------------------------------------


class Claim(BaseModel):
    """One factual claim in the article body, linked to supporting sources."""

    text: str
    source_ids: list[str]  # ≥1; each must be a real source id


class DraftArticle(BaseModel):
    """Claude's structured article output."""

    title: str
    body: str
    claims: list[Claim]


class DraftResult(BaseModel):
    article: DraftArticle
    claim_source_map: dict[str, list[str]]  # claim index ("0","1",…) → source_ids
    sources: list[Source]                    # sources actually cited


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------


class FormRequest(BaseModel):
    name: str | None = None
    linkedin_url: str | None = None
    company: str | None = None

    @model_validator(mode="after")
    def require_name_or_linkedin(self) -> "FormRequest":
        if not self.name and not self.linkedin_url:
            raise ValueError("Provide at least one of 'name' or 'linkedin_url'.")
        return self


# ---------------------------------------------------------------------------
# Top-level Run
# ---------------------------------------------------------------------------


class Run(BaseModel):
    id: str
    created_at: datetime
    input: FormRequest
    status: Literal["completed", "failed", "needs_disambiguation"]
    ingest: StageOutput
    enrich: StageOutput
    research: StageOutput | None = None
    draft: StageOutput | None = None
    article: DraftArticle | None = None             # convenience copy from draft
    claim_source_map: dict[str, list[str]] | None = None
    sources: list[Source] = []                      # deduped union across all stages
    error: StageError | None = None                 # set when status == "failed"
    evals: EvalReport | None = None                 # attached by the eval layer


# ---------------------------------------------------------------------------
# Response wrappers (suffix convention: *Response)
# ---------------------------------------------------------------------------


class RunResponse(BaseModel):
    run: Run


class RunsResponse(BaseModel):
    runs: list[Run]


# ---------------------------------------------------------------------------
# SSE pipeline event payloads (emitted by stream_form_pipeline)
# ---------------------------------------------------------------------------


class RunStartedEvent(BaseModel):
    """First event — the run has been assigned an id and is starting."""

    run_id: str
    created_at: datetime
    input: FormRequest


class StageStartedEvent(BaseModel):
    """A stage has begun executing."""

    name: str


class StageCompletedEvent(BaseModel):
    """A stage finished (ok or error)."""

    stage: StageOutput


class NeedsDisambiguationEvent(BaseModel):
    """Terminal — Apollo returned multiple candidates; user must pick one."""

    run_id: str
    candidates: list[EnrichCandidate]


class EvaluatingEvent(BaseModel):
    """Emitted just before the LLM-judge evals run (only when evaluate=True)."""


class RunCompletedEvent(BaseModel):
    """Terminal — the run completed successfully."""

    run: Run


class RunFailedEvent(BaseModel):
    """Terminal — the run failed; partial trace included."""

    run: Run
