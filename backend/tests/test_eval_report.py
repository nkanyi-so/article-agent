import pytest

from app.evals.base import (
    EVAL_WEIGHTS,
    run_all_evals,
    run_deterministic_evals,
)


async def test_run_deterministic_evals_produces_two_verdicts(sample_run_completed):
    report = await run_deterministic_evals(sample_run_completed)

    assert report.complete is False
    assert len(report.verdicts) == 2
    names = {v.name for v in report.verdicts}
    assert names == {"entity_resolution", "stage_validity"}
    assert report.judge_model is None


async def test_run_all_evals_produces_four_verdicts(sample_run_completed, mock_judge):
    report = await run_all_evals(sample_run_completed, mock_judge)

    assert report.complete is True
    assert len(report.verdicts) == 4
    names = {v.name for v in report.verdicts}
    assert names == {"groundedness", "entity_resolution", "angle_support", "stage_validity"}
    assert report.judge_model == "claude-opus-4-8"


async def test_overall_score_is_weighted_mean(sample_run_completed, mock_judge):
    report = await run_all_evals(sample_run_completed, mock_judge)

    verdicts_by_name = {v.name: v for v in report.verdicts}
    total_weight = sum(EVAL_WEIGHTS[n] for n in verdicts_by_name)
    expected = sum(
        verdicts_by_name[n].score * EVAL_WEIGHTS[n] for n in verdicts_by_name
    ) / total_weight

    assert report.overall_score == pytest.approx(expected, abs=0.001)


async def test_deterministic_report_score_renormalized_over_two_verdicts(sample_run_completed):
    report = await run_deterministic_evals(sample_run_completed)

    # Only entity_resolution (0.15) and stage_validity (0.30) are present
    present_weights = {v.name: EVAL_WEIGHTS[v.name] for v in report.verdicts}
    total = sum(present_weights.values())
    expected = sum(v.score * present_weights[v.name] for v in report.verdicts) / total

    assert report.overall_score == pytest.approx(expected, abs=0.001)


async def test_degraded_verdict_rolls_up_to_report(sample_run_completed):
    # sample_run_completed uses form-input stub → entity_resolution is degraded
    report = await run_deterministic_evals(sample_run_completed)

    assert report.degraded is True
    # Caveats from the degraded verdict should be rolled up
    assert len(report.caveats) > 0


async def test_passed_is_false_if_any_verdict_fails(sample_run_completed):
    # stage_validity passes but entity_resolution does not (degraded, passed=False)
    report = await run_deterministic_evals(sample_run_completed)

    assert report.passed is False


async def test_failed_run_deterministic_evals(sample_run_failed):
    report = await run_deterministic_evals(sample_run_failed)

    assert report.complete is False
    assert len(report.verdicts) == 2
    # stage_validity should pass for a correctly-failed run
    sv = next(v for v in report.verdicts if v.name == "stage_validity")
    assert sv.passed is True
