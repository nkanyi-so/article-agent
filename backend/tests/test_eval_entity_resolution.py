import pytest

from app.evals.base import EvalContext
from app.evals.entity_resolution import evaluate
from app.schemas import (
    EnrichResult,
    FormRequest,
    PersonFacts,
    Run,
    StageOutput,
)


async def test_apollo_degraded_is_honest(sample_run_completed):
    # sample_run_completed uses form-input stub (Apollo 403)
    ctx = EvalContext(run=sample_run_completed)
    verdict = await evaluate(ctx)

    assert verdict.name == "entity_resolution"
    assert verdict.score == 0.5        # "can't verify" score
    assert verdict.passed is False
    assert verdict.degraded is True
    assert verdict.confidence == "low"
    assert any("Apollo" in c or "unavailable" in c.lower() for c in verdict.caveats)


async def test_real_match_name_passes(sample_run_completed):
    import copy

    run = copy.deepcopy(sample_run_completed)
    # Inject a real Apollo match (no form-input stub)
    run.enrich.output = {
        "status": "matched",
        "person": {
            "apollo_id": "ap_123",
            "name": "Sam Altman",
            "title": "CEO",
            "organization": "OpenAI",
            "organization_domain": "openai.com",
            "linkedin_url": None,
            "location": "San Francisco",
            "raw": {},  # no _source=form-input → real match path
        },
        "candidates": [],
    }
    ctx = EvalContext(run=run)
    verdict = await evaluate(ctx)

    # name_match signal: "sam altman" vs "sam altman" → high overlap
    assert verdict.score >= 0.6
    assert verdict.passed is True


async def test_ambiguous_status_is_degraded(sample_run_completed):
    import copy

    run = copy.deepcopy(sample_run_completed)
    run.enrich.output = {
        "status": "ambiguous",
        "person": None,
        "candidates": [
            {"apollo_id": "a1", "name": "Sam A", "title": None, "organization": None,
             "linkedin_url": None, "confidence": 1.0},
            {"apollo_id": "a2", "name": "Sam A", "title": None, "organization": None,
             "linkedin_url": None, "confidence": 0.5},
        ],
    }
    ctx = EvalContext(run=run)
    verdict = await evaluate(ctx)

    assert verdict.score == 0.3
    assert verdict.passed is False
    assert verdict.degraded is True
    assert verdict.details["candidate_count"] == 2


async def test_enrich_error_stage_scores_zero(sample_run_failed):
    import copy

    run = copy.deepcopy(sample_run_failed)
    run.enrich.status = "error"
    run.enrich.output = None
    ctx = EvalContext(run=run)
    verdict = await evaluate(ctx)

    assert verdict.score == 0.0
    assert verdict.passed is False
    assert verdict.degraded is True


async def test_real_match_with_linkedin_and_org():
    import json
    from pathlib import Path

    from app.schemas import Run

    raw = json.loads(
        (Path(__file__).parent / "fixtures" / "sample_run_completed.json").read_text()
    )
    run = Run.model_validate(raw)

    # Inject a match with all three signals agreeing
    run.input = FormRequest(
        name="Sam Altman",
        linkedin_url="https://www.linkedin.com/in/samaltman",
        company="OpenAI",
    )
    run.enrich.output = {
        "status": "matched",
        "person": {
            "apollo_id": "ap_123",
            "name": "Sam Altman",
            "title": "CEO",
            "organization": "OpenAI",
            "organization_domain": "openai.com",
            "linkedin_url": "https://www.linkedin.com/in/samaltman",
            "location": "SF",
            "raw": {},
        },
        "candidates": [],
    }
    ctx = EvalContext(run=run)
    verdict = await evaluate(ctx)

    assert verdict.confidence == "high"
    assert verdict.score >= 0.8
    assert verdict.passed is True
