"""The shapes that pass between stages and into storage. One set, used everywhere."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

StageName = Literal["ingest", "extract", "draft", "ground", "evaluate"]


class Segment(BaseModel):
    """One sentence of the transcript. `index` is its block index in the citable document."""

    index: int = Field(ge=0)
    turn: int = Field(ge=0)
    speaker: str
    line: int = Field(ge=1, description="Line of the source text where the turn starts.")
    text: str


class IngestResult(BaseModel):
    title: str
    segments: list[Segment]


class Correction(BaseModel):
    """A later statement that replaces an earlier one, as named by the extract stage."""

    superseded: int = Field(ge=0)
    replaced_by: int = Field(ge=0)


class Point(BaseModel):
    """Something said in the transcript that an article could report."""

    text: str
    segments: list[int]


class Disagreement(BaseModel):
    topic: str
    side_a: list[int]
    side_b: list[int]


class ExtractResult(BaseModel):
    """What the extract stage found. Every segment index in it has been range-checked."""

    points: list[Point]
    corrections: list[Correction]
    disagreements: list[Disagreement]
    angle: str


class Citation(BaseModel):
    """A pointer into the transcript: segments from `start_segment` up to, not including,
    `end_segment`."""

    start_segment: int = Field(ge=0)
    end_segment: int = Field(ge=1)
    cited_text: str


class DraftBlock(BaseModel):
    """One text block of the draft response, with whatever citations the model attached."""

    text: str
    citations: list[Citation] = []


class NameResolution(BaseModel):
    """A surname that passed the name check through its owner's first name: the cited text
    has the first name, and exactly one speaker of the transcript has that first name."""

    name: str
    first_name: str
    speaker: str


class Claim(BaseModel):
    """A sentence of the draft that passed the ground check."""

    text: str
    paragraph: int = Field(ge=0)
    citations: list[Citation]
    segment_indexes: list[int]
    name_resolutions: list[NameResolution] = Field(
        default=[], description="Names kept by the first-name rule, so the trace shows it."
    )
    question_segments: list[int] = Field(
        default=[],
        description=(
            "Added by code, not cited by the model: for each cited line that opens a turn, "
            "the question the turn before ended on. Shown to the reader and to the judge as "
            "context. Never evidence: no ground rule reads it."
        ),
    )


RemovalReason = Literal[
    "no_citation",
    "invalid_citation",
    "unsupported_number",
    "unsupported_name",
    "misquote",
    "rests_on_corrected_segment",
    "wrong_speaker",
]


class RemovedUnit(BaseModel):
    """A sentence the ground check removed. Kept as written, with the reason, never patched."""

    text: str
    paragraph: int = Field(ge=0)
    reason: RemovalReason
    detail: list[str] = Field(default=[], description="What was missing, for example the numbers.")
    segment_indexes: list[int] = []


HeadlineFailure = Literal[
    "headline_missing",
    "headline_unsupported_number",
    "headline_unsupported_name",
    "headline_misquote",
    "headline_superseded_number",
]


class Headline(BaseModel):
    """The article's headline: the model's if it passed its check, otherwise the title."""

    text: str
    source: Literal["model", "title"]
    supporting_claims: list[int] = Field(
        default=[], description="Indexes into `claims` of the kept sentences that support it."
    )
    rejected_text: str | None = Field(
        default=None, description="The model's headline, if it failed."
    )
    failure: HeadlineFailure | None = None
    failure_detail: list[str] = []


class GroundResult(BaseModel):
    headline: Headline
    claims: list[Claim]
    removed: list[RemovedUnit]


class StageRecord(BaseModel):
    """What one stage of one run was given and what it produced."""

    run_id: str
    seq: int = Field(ge=0)
    name: StageName
    status: Literal["running", "completed", "failed"]
    started_at: datetime
    duration_ms: int | None = Field(default=None, ge=0)
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    error: str | None = Field(default=None, description="An error code, never exception text.")
    copied_from_run_id: str | None = None
