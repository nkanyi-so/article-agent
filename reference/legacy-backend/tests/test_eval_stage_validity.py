import pytest

from app.evals.base import EvalContext
from app.evals.stage_validity import evaluate


async def test_completed_run_all_checks_pass(sample_run_completed):
    ctx = EvalContext(run=sample_run_completed)
    verdict = await evaluate(ctx)

    assert verdict.name == "stage_validity"
    assert verdict.score == 1.0
    assert verdict.passed is True
    assert verdict.method == "deterministic"
    assert verdict.details["failed"] == []


async def test_degraded_run_bad_source_id_fails(sample_run_degraded):
    # sample_run_degraded has claim 2 citing exa:FAKE (not in run.sources)
    # → claim_source_ids_in_sources check fails
    ctx = EvalContext(run=sample_run_degraded)
    verdict = await evaluate(ctx)

    assert verdict.passed is False
    assert verdict.score < 1.0
    assert "claim_source_ids_in_sources" in verdict.details["failed"]


async def test_failed_run_scores_1_for_reachable_checks(sample_run_failed):
    # A correctly-failed run has valid envelope structure
    ctx = EvalContext(run=sample_run_failed)
    verdict = await evaluate(ctx)

    assert verdict.score == 1.0
    assert verdict.passed is True
    assert verdict.details["failed"] == []


async def test_missing_claim_map_key_fails(sample_run_completed):
    import copy

    run = copy.deepcopy(sample_run_completed)
    # Remove one claim_source_map key → keys don't match claims
    del run.claim_source_map["4"]
    ctx = EvalContext(run=run)
    verdict = await evaluate(ctx)

    assert verdict.passed is False
    assert "claim_map_keys_correct" in verdict.details["failed"]


async def test_inconsistent_claim_map_fails(sample_run_completed):
    import copy

    run = copy.deepcopy(sample_run_completed)
    # Make claim_source_map disagree with claim.source_ids for claim 0
    run.claim_source_map["0"] = ["exa:2"]  # claim[0].source_ids is ["exa:0"]
    ctx = EvalContext(run=run)
    verdict = await evaluate(ctx)

    assert verdict.passed is False
    assert "claim_map_consistent_with_claims" in verdict.details["failed"]


async def test_duplicate_sources_fails(sample_run_completed):
    import copy

    run = copy.deepcopy(sample_run_completed)
    # Inject a duplicate source
    run.sources = run.sources + [run.sources[0]]
    ctx = EvalContext(run=run)
    verdict = await evaluate(ctx)

    assert verdict.passed is False
    assert "sources_deduped" in verdict.details["failed"]
