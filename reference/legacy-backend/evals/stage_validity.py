from __future__ import annotations

from app.evals.base import EvalContext, get_research_result
from app.evals.schemas import EvalVerdict

_PASS_THRESHOLD = 1.0


async def evaluate(ctx: EvalContext) -> EvalVerdict:
    """Deterministic structural-integrity gate.

    Asserts envelope coherence, referential integrity of source IDs,
    and claim_source_map consistency. Score == 1.0 means every check passed.
    Correctly-failed or ambiguous runs only have their reachable checks applied
    and can still score 1.0 (a valid failure is structurally sound).
    """
    run = ctx.run
    checks: dict[str, bool] = {}

    # ── Envelope presence & coherence ──────────────────────────────────────
    checks["ingest_present"] = run.ingest is not None
    checks["enrich_present"] = run.enrich is not None

    if run.ingest is not None:
        checks["ingest_status_valid"] = run.ingest.status in ("ok", "error")
        if run.ingest.status == "ok":
            checks["ingest_output_present"] = run.ingest.output is not None
        if run.ingest.status == "error":
            checks["ingest_error_has_code"] = (
                run.ingest.error is not None and bool(run.ingest.error.code)
            )

    if run.enrich is not None:
        checks["enrich_status_valid"] = run.enrich.status in ("ok", "error")
        if run.enrich.status == "ok":
            checks["enrich_output_present"] = run.enrich.output is not None

    # ── Completed-run checks ───────────────────────────────────────────────
    if run.status == "completed":
        checks["research_present"] = run.research is not None
        checks["draft_present"] = run.draft is not None
        checks["article_present"] = run.article is not None
        checks["claim_map_present"] = run.claim_source_map is not None

        if run.research is not None:
            checks["research_ok"] = run.research.status == "ok"
            checks["research_output_present"] = run.research.output is not None

        if run.draft is not None:
            checks["draft_ok"] = run.draft.status == "ok"
            checks["draft_output_present"] = run.draft.output is not None

        source_ids = {s.id for s in run.sources}
        checks["sources_deduped"] = len(run.sources) == len(source_ids)

        if run.article is not None and run.claim_source_map is not None:
            claims = run.article.claims
            expected_keys = {str(i) for i in range(len(claims))}
            actual_keys = set(run.claim_source_map.keys())
            checks["claim_map_keys_correct"] = actual_keys == expected_keys

            checks["claim_source_ids_in_sources"] = all(
                sid in source_ids
                for ids in run.claim_source_map.values()
                for sid in ids
            )

            checks["claim_map_consistent_with_claims"] = all(
                run.claim_source_map.get(str(i), []) == claim.source_ids
                for i, claim in enumerate(claims)
            )

        research_result = get_research_result(run)
        if research_result is not None:
            angle = research_result.angle
            checks["angle_source_ids_in_sources"] = all(
                sid in source_ids for sid in angle.supporting_source_ids
            )

    total = len(checks)
    passed_count = sum(1 for v in checks.values() if v)
    score = passed_count / total if total else 1.0
    passed = score >= _PASS_THRESHOLD

    failed = [k for k, v in checks.items() if not v]
    reasoning = (
        f"All {total} structural checks passed."
        if passed
        else f"{len(failed)}/{total} checks failed: {', '.join(failed)}"
    )

    return EvalVerdict(
        name="stage_validity",
        score=round(score, 4),
        passed=passed,
        reasoning=reasoning,
        method="deterministic",
        confidence="high",
        details={"checks": checks, "failed": failed},
    )
