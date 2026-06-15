from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

EvalName = Literal["groundedness", "entity_resolution", "angle_support", "stage_validity"]


class ClaimGroundedness(BaseModel):
    """Claim-level groundedness verdict — one row in the groundedness breakdown."""

    claim_index: int
    claim_text: str
    supported: bool
    cited_source_ids: list[str]      # ids the claim points at
    supporting_source_ids: list[str] # subset the judge confirms actually support it (⊆ cited)
    reasoning: str


class EvalVerdict(BaseModel):
    """The per-eval result object attached to a Run."""

    name: EvalName
    score: float                              # 0.0..1.0
    passed: bool
    reasoning: str
    method: Literal["deterministic", "llm_judge"]
    confidence: Literal["high", "medium", "low"]
    degraded: bool = False                    # True when eval ran but signal is unreliable
    caveats: list[str] = []                   # explicit reasons for degraded / low-confidence
    details: dict[str, Any] = {}              # structured, eval-specific payload


class EvalReport(BaseModel):
    """Aggregated result from running one or more evals against a Run."""

    overall_score: float                      # weighted mean, renormalized over present verdicts
    passed: bool                              # all present evals passed
    complete: bool                            # True when all four evals ran
    verdicts: list[EvalVerdict]
    degraded: bool                            # any verdict is degraded
    caveats: list[str]                        # rolled-up across verdicts (deduped)
    evaluated_at: datetime
    judge_model: str | None = None            # set when an LLM judge ran


# ---------------------------------------------------------------------------
# Judge structured-output models (output_format for ClaudeClient.parse)
# No min/max numeric constraints — structured-output-safe per Anthropic SDK rules.
# ---------------------------------------------------------------------------


class ClaimJudgement(BaseModel):
    claim_index: int
    supported: bool
    supporting_source_ids: list[str]
    reasoning: str


class GroundednessJudgeOutput(BaseModel):
    claims: list[ClaimJudgement]
    overall_reasoning: str


class AngleSupportJudgeOutput(BaseModel):
    supported: bool
    score: float       # 0..1, judge's own estimate of evidential support
    supporting_source_ids: list[str]
    reasoning: str
