"""What an evaluation produces: for one run (stored as the evaluate stage's output) and
for a whole eval set (written to a dated result file)."""

from typing import Literal

from pydantic import BaseModel, Field

CheckId = Literal["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "J1", "J1-alone", "J2"]


class CheckResult(BaseModel):
    """One check's verdict on one run. `score` is the share that passed, 0 to 1."""

    id: CheckId
    name: str
    passed: bool
    score: float = Field(ge=0, le=1)
    detail: list[str] = Field(default=[], description="What failed, in words a person can read.")


class Verdict(BaseModel):
    """Whether one sentence is supported by the transcript lines it cites."""

    claim: int | None = Field(description="Index into the run's claims; null for the headline.")
    supported: bool = Field(
        description="Supported, reading each cited answer with the question it replied to."
    )
    supported_alone: bool = Field(
        default=False, description="Supported by the cited lines with no question shown."
    )
    decided_by: Literal["code", "judge"] = Field(
        description="A sentence that fails a code check is scored unsupported without asking."
    )
    supporting_segments: list[int] = Field(
        default=[], description="The cited segments the judge named. Never outside the citation."
    )
    reason: str = ""


class JudgeResult(BaseModel):
    """`failed` means the judge could not be used (a refusal, a timeout, an unusable
    response). It is plumbing, and is never counted as an unsupported sentence."""

    outcome: Literal["judged", "failed"]
    error: str | None = Field(default=None, description="An error code, when it failed.")
    model: str | None = None
    verdicts: list[Verdict] = []
    score: float | None = Field(default=None, description="Share of sentences supported.")
    score_alone: float | None = Field(
        default=None, description="The same share when no question is shown with an answer."
    )


class EvalReport(BaseModel):
    """The evaluate stage's output for one run."""

    checks: list[CheckResult]
    judge: JudgeResult
    drafted: int = Field(description="Sentences the model drafted.")
    removed: int = Field(description="Of those, how many the ground check removed.")
    removal_rate: float


class PairResult(BaseModel):
    id: str
    kind: str
    expected_supported: bool
    judged_supported: bool
    expected_alone: bool
    judged_alone: bool
    reason: str


class Calibration(BaseModel):
    """The judge against pairs whose answer was written by hand."""

    outcome: Literal["judged", "failed"]
    error: str | None = None
    pairs: list[PairResult] = []
    agreement: float | None = None
    negatives: int = 0
    negatives_caught: int = 0
    agreement_alone: float | None = Field(
        default=None, description="Agreement on the answers for cited lines with no question."
    )
    cost_usd: float = 0.0


class CaseRow(BaseModel):
    """One case of the set. `plumbing` and `wrong` are kept apart on purpose."""

    id: str
    repeat: int = Field(default=1, description="Which of the repeated runs of this case.")
    tags: list[str]
    seen_by_prompt: bool
    outcome: Literal["completed", "refused", "plumbing"]
    error: str | None = None
    model_calls: int
    cost_usd: float
    checks: list[CheckResult] = []
    judge: JudgeResult | None = None
    drafted: int = 0
    removed: int = 0
    kept: int = 0
    headline_source: str | None = None
    removed_units: list[dict[str, object]] = []


class Aggregate(BaseModel):
    id: CheckId
    name: str
    value: str
    threshold: str
    passed: bool | None = Field(description="Null when there is no threshold yet.")


class CaseSummary(BaseModel):
    """One case over its repeated runs: the mean of each score, and how far the runs spread."""

    id: str
    runs: int
    judged: list[float] = Field(description="J1 for each run, the question shown.")
    judged_mean: float | None
    judged_alone: list[float] = Field(description="J1 for each run, cited lines alone.")
    judged_alone_mean: float | None
    coverage_mean: float | None
    drafted: int
    removed: int


class EvalSetResult(BaseModel):
    """A whole run of the eval set. This is what a dated result file holds."""

    ran_at: str
    mode: Literal["fixture", "live"]
    writer_model: str
    judge_model: str
    repeats: int = 1
    cases: list[CaseRow]
    summaries: list[CaseSummary] = []
    calibrations: list[Calibration] = []
    aggregates: list[Aggregate]
    plumbing_failures: list[str]
    passed: bool
    cost_usd: float
    note: str = ""
