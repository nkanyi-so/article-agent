import pytest

from app.evals.base import EvalContext
from app.evals.groundedness import evaluate


async def test_completed_run_all_supported(sample_run_completed, mock_judge):
    ctx = EvalContext(run=sample_run_completed, judge=mock_judge)
    verdict = await evaluate(ctx)

    assert verdict.name == "groundedness"
    assert verdict.score == 1.0
    assert verdict.passed is True
    assert verdict.method == "llm_judge"
    assert verdict.details["supported_count"] == 5
    assert verdict.details["total_count"] == 5


async def test_degraded_run_hard_fail_lowers_score(sample_run_degraded, mock_judge):
    # sample_run_degraded has claim 2 citing exa:FAKE (not in run.sources)
    # → hard-fail for claim 2, judge handles 0 and 1 → score = 2/3
    ctx = EvalContext(run=sample_run_degraded, judge=mock_judge)
    verdict = await evaluate(ctx)

    assert verdict.name == "groundedness"
    assert verdict.score == pytest.approx(2 / 3, abs=0.001)
    assert verdict.passed is False  # 0.667 < 0.80 threshold
    assert verdict.details["supported_count"] == 2
    assert verdict.details["total_count"] == 3
    assert any("hard-failed" in c for c in verdict.caveats)


async def test_no_article_returns_score_zero(sample_run_failed, mock_judge):
    ctx = EvalContext(run=sample_run_failed, judge=mock_judge)
    verdict = await evaluate(ctx)

    assert verdict.score == 0.0
    assert verdict.passed is False
    assert verdict.degraded is True
    # Judge should NOT have been called
    assert mock_judge.judge_groundedness.call_count == 0  # type: ignore[attr-defined]


async def test_no_judge_raises(sample_run_completed):
    ctx = EvalContext(run=sample_run_completed, judge=None)
    with pytest.raises(ValueError, match="JudgeClient"):
        await evaluate(ctx)


async def test_judge_marks_claim_unsupported(sample_run_completed):
    from unittest.mock import AsyncMock, MagicMock

    from app.evals.judge import JudgeClient
    from app.evals.schemas import ClaimJudgement, GroundednessJudgeOutput

    # Judge marks all claims as NOT supported
    async def _unsupported(claims, sources_by_id):
        return GroundednessJudgeOutput(
            claims=[
                ClaimJudgement(
                    claim_index=c["index"],
                    supported=False,
                    supporting_source_ids=[],
                    reasoning="Not supported.",
                )
                for c in claims
            ],
            overall_reasoning="Nothing is supported.",
        )

    judge = MagicMock(spec=JudgeClient)
    judge.judge_groundedness = _unsupported
    ctx = EvalContext(run=sample_run_completed, judge=judge)
    verdict = await evaluate(ctx)

    assert verdict.score == 0.0
    assert verdict.passed is False
    assert verdict.details["supported_count"] == 0
