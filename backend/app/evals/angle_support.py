from __future__ import annotations

from app.evals.base import EvalContext, get_research_result
from app.evals.schemas import EvalVerdict

_PASS_THRESHOLD = 0.60
_THIN_SNIPPET_CHARS = 80


async def evaluate(ctx: EvalContext) -> EvalVerdict:
    """LLM-judge eval: is the chosen angle actually backed by the evidence?

    Deterministic pre-check: supporting_source_ids ⊆ run.sources.
    Judge output is clamped to the valid id set.
    """
    run = ctx.run
    research_result = get_research_result(run)

    if research_result is None:
        return EvalVerdict(
            name="angle_support",
            score=0.0,
            passed=False,
            reasoning="No research stage output to evaluate.",
            method="llm_judge",
            confidence="low",
            degraded=True,
            caveats=["No research stage output — run did not complete research."],
        )

    if research_result.angle_fallback:
        return EvalVerdict(
            name="angle_support",
            score=0.0,
            passed=False,
            reasoning="Angle fell back to positional sources — Claude returned no valid source IDs.",
            method="deterministic",
            confidence="high",
            degraded=True,
            caveats=["Angle supporting sources were selected by positional fallback, not by Claude."],
        )

    if ctx.judge is None:
        raise ValueError("angle_support eval requires a JudgeClient")

    angle = research_result.angle
    source_map = {s.id: s for s in run.sources}

    bad_ids = [sid for sid in angle.supporting_source_ids if sid not in source_map]
    valid_ids = [sid for sid in angle.supporting_source_ids if sid in source_map]
    supporting_sources = [source_map[sid] for sid in valid_ids]

    caveats: list[str] = []
    confidence: str = "high"
    if bad_ids:
        caveats.append(
            f"Angle cited {len(bad_ids)} source id(s) not in run.sources."
        )
        confidence = "medium"

    thin = any(
        not s.snippet or len(s.snippet) < _THIN_SNIPPET_CHARS
        for s in supporting_sources
    )
    if thin:
        caveats.append("Supporting source snippets are short; judge may be under-informed.")
        confidence = "low"

    if not supporting_sources:
        return EvalVerdict(
            name="angle_support",
            score=0.0,
            passed=False,
            reasoning="No valid supporting sources found for the angle.",
            method="llm_judge",
            confidence="low",
            degraded=True,
            caveats=caveats + ["No valid supporting sources available for judge."],
        )

    judge_out = await ctx.judge.judge_angle_support(
        headline=angle.headline,
        angle=angle.angle,
        rationale=angle.rationale,
        supporting_sources=supporting_sources,
    )

    # Clamp: judge can only reference the ids we gave it
    valid_set = set(valid_ids)
    judge_out.supporting_source_ids = [
        sid for sid in judge_out.supporting_source_ids if sid in valid_set
    ]
    score = max(0.0, min(1.0, judge_out.score))

    return EvalVerdict(
        name="angle_support",
        score=round(score, 4),
        passed=judge_out.supported and score >= _PASS_THRESHOLD,
        reasoning=judge_out.reasoning,
        method="llm_judge",
        confidence=confidence,  # type: ignore[arg-type]
        degraded=bool(caveats),
        caveats=caveats,
        details={
            "supported": judge_out.supported,
            "angle_headline": angle.headline,
            "supporting_source_ids": judge_out.supporting_source_ids,
        },
    )
