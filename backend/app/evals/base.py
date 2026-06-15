from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.evals.schemas import EvalReport, EvalVerdict
from app.schemas import Brief, EnrichResult, ResearchResult, Run

if TYPE_CHECKING:
    from app.evals.judge import JudgeClient

# ---------------------------------------------------------------------------
# Weights and thresholds
# ---------------------------------------------------------------------------

EVAL_WEIGHTS: dict[str, float] = {
    "groundedness": 0.40,
    "stage_validity": 0.30,
    "entity_resolution": 0.15,
    "angle_support": 0.15,
}

PASS_THRESHOLDS: dict[str, float] = {
    "groundedness": 0.80,
    "stage_validity": 1.0,
    "entity_resolution": 0.60,
    "angle_support": 0.60,
}


# ---------------------------------------------------------------------------
# Shared context
# ---------------------------------------------------------------------------


@dataclass
class EvalContext:
    run: Run
    judge: "JudgeClient | None" = field(default=None)


# ---------------------------------------------------------------------------
# Output coercion helpers
# StageOutput.output is typed as Any; when loaded from JSON it's a plain dict.
# These helpers ensure eval functions always receive proper model instances.
# ---------------------------------------------------------------------------


def get_enrich_result(run: Run) -> EnrichResult | None:
    out = run.enrich.output if run.enrich else None
    if out is None:
        return None
    if isinstance(out, dict):
        return EnrichResult.model_validate(out)
    return out  # type: ignore[return-value]


def get_research_result(run: Run) -> ResearchResult | None:
    if run.research is None or run.research.output is None:
        return None
    out = run.research.output
    if isinstance(out, dict):
        return ResearchResult.model_validate(out)
    return out  # type: ignore[return-value]


def get_ingest_brief(run: Run) -> Brief | None:
    if run.ingest is None or run.ingest.output is None:
        return None
    out = run.ingest.output
    if isinstance(out, dict):
        return Brief.model_validate(out)
    return out  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------


def _build_report(
    verdicts: list[EvalVerdict],
    *,
    complete: bool,
    judge_model: str | None,
) -> EvalReport:
    present_weights = {v.name: EVAL_WEIGHTS[v.name] for v in verdicts}
    total_weight = sum(present_weights.values())

    overall_score = (
        sum(v.score * present_weights[v.name] for v in verdicts) / total_weight
        if total_weight
        else 0.0
    )

    passed = all(v.passed for v in verdicts)
    degraded = any(v.degraded for v in verdicts)
    # Deduplicate caveats while preserving order
    seen: set[str] = set()
    all_caveats: list[str] = []
    for v in verdicts:
        for c in v.caveats:
            if c not in seen:
                seen.add(c)
                all_caveats.append(c)

    return EvalReport(
        overall_score=round(overall_score, 4),
        passed=passed,
        complete=complete,
        verdicts=verdicts,
        degraded=degraded,
        caveats=all_caveats,
        evaluated_at=datetime.now(timezone.utc),
        judge_model=judge_model,
    )


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


async def run_deterministic_evals(run: Run) -> EvalReport:
    """Run entity_resolution + stage_validity (no judge, no API cost)."""
    from app.evals.entity_resolution import evaluate as eval_entity
    from app.evals.stage_validity import evaluate as eval_stage

    ctx = EvalContext(run=run)
    verdicts = [
        await eval_entity(ctx),
        await eval_stage(ctx),
    ]
    return _build_report(verdicts, complete=False, judge_model=None)


async def run_all_evals(run: Run, judge: "JudgeClient") -> EvalReport:
    """Run all four evals including the two LLM judges."""
    from app.evals.angle_support import evaluate as eval_angle
    from app.evals.entity_resolution import evaluate as eval_entity
    from app.evals.groundedness import evaluate as eval_ground
    from app.evals.stage_validity import evaluate as eval_stage

    ctx = EvalContext(run=run, judge=judge)
    verdicts = [
        await eval_ground(ctx),
        await eval_entity(ctx),
        await eval_angle(ctx),
        await eval_stage(ctx),
    ]
    return _build_report(verdicts, complete=True, judge_model="claude-opus-4-8")
