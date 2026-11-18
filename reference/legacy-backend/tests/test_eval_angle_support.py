import pytest

from app.evals.angle_support import evaluate
from app.evals.base import EvalContext


async def test_completed_run_passes(sample_run_completed, mock_judge):
    ctx = EvalContext(run=sample_run_completed, judge=mock_judge)
    verdict = await evaluate(ctx)

    assert verdict.name == "angle_support"
    assert verdict.score == pytest.approx(0.9, abs=0.01)
    assert verdict.passed is True
    assert verdict.method == "llm_judge"


async def test_no_research_result_is_degraded(sample_run_failed, mock_judge):
    # sample_run_failed has no research output
    ctx = EvalContext(run=sample_run_failed, judge=mock_judge)
    verdict = await evaluate(ctx)

    assert verdict.score == 0.0
    assert verdict.passed is False
    assert verdict.degraded is True
    assert mock_judge.judge_angle_support.call_count == 0  # type: ignore[attr-defined]


async def test_no_judge_raises(sample_run_completed):
    ctx = EvalContext(run=sample_run_completed, judge=None)
    with pytest.raises(ValueError, match="JudgeClient"):
        await evaluate(ctx)


async def test_bad_angle_source_ids_logged_as_caveat(sample_run_completed, mock_judge):
    import copy

    run = copy.deepcopy(sample_run_completed)
    # Inject a bad source id into the angle
    run.research.output["angle"]["supporting_source_ids"] = ["exa:0", "exa:FAKE"]
    ctx = EvalContext(run=run, judge=mock_judge)
    verdict = await evaluate(ctx)

    # Should note the bad id as a caveat and lower confidence
    assert any("source id" in c.lower() or "not in run" in c.lower() for c in verdict.caveats)
    assert verdict.confidence in ("medium", "low")


async def test_judge_not_supported_fails(sample_run_completed):
    from unittest.mock import AsyncMock, MagicMock

    from app.evals.judge import JudgeClient
    from app.evals.schemas import AngleSupportJudgeOutput

    judge = MagicMock(spec=JudgeClient)
    judge.judge_angle_support = AsyncMock(
        return_value=AngleSupportJudgeOutput(
            supported=False,
            score=0.3,
            supporting_source_ids=[],
            reasoning="Angle not evidenced by snippets.",
        )
    )
    ctx = EvalContext(run=sample_run_completed, judge=judge)
    verdict = await evaluate(ctx)

    assert verdict.passed is False
    assert verdict.score == pytest.approx(0.3, abs=0.01)
