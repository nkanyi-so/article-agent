from __future__ import annotations

import re

from app.evals.base import EvalContext, get_enrich_result, get_ingest_brief
from app.evals.schemas import EvalVerdict

_PASS_THRESHOLD = 0.60


def _normalize(text: str) -> set[str]:
    return set(re.sub(r"[^\w\s]", "", text.lower()).split())


def _token_overlap(a: str, b: str) -> float:
    """Jaccard-like token overlap between two strings."""
    if not a or not b:
        return 0.0
    ta, tb = _normalize(a), _normalize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


async def evaluate(ctx: EvalContext) -> EvalVerdict:
    """Deterministic entity-resolution eval.

    Reports honestly when Apollo enrichment was skipped (free-plan 403):
    score=0.5, degraded=True, passed=False — "can't verify" is not the same
    as "wrong", but it is not a pass.
    """
    run = ctx.run

    if run.enrich.status == "error" or run.enrich.output is None:
        return EvalVerdict(
            name="entity_resolution",
            score=0.0,
            passed=False,
            reasoning="Enrich stage errored — no entity to evaluate.",
            method="deterministic",
            confidence="low",
            degraded=True,
            caveats=["Enrich stage errored; entity resolution not possible."],
        )

    enrich_result = get_enrich_result(run)
    if enrich_result is None:
        return EvalVerdict(
            name="entity_resolution",
            score=0.0,
            passed=False,
            reasoning="Could not parse enrich output.",
            method="deterministic",
            confidence="low",
            degraded=True,
            caveats=["Enrich output is None after coercion."],
        )

    person = enrich_result.person

    # ── Apollo-degraded path ──────────────────────────────────────────────────
    if person and person.raw.get("_source") == "form-input":
        skipped = person.raw.get("_apollo_skipped", "unknown reason")
        return EvalVerdict(
            name="entity_resolution",
            score=0.5,
            passed=False,
            reasoning=(
                "Apollo enrichment was skipped; person built from form inputs only. "
                "Identity not independently verified."
            ),
            method="deterministic",
            confidence="low",
            degraded=True,
            caveats=[
                f"Apollo unavailable ({str(skipped)[:120]}); "
                "identity not independently verified."
            ],
            details={"apollo_skipped": str(skipped), "source": "form-input"},
        )

    # ── Exa web-search fallback path ─────────────────────────────────────────
    if person and person.raw.get("_source") == "exa-web":
        skipped = person.raw.get("_apollo_skipped", "unknown reason")
        linkedin_found = bool(person.raw.get("_exa_linkedin_found"))
        if linkedin_found:
            return EvalVerdict(
                name="entity_resolution",
                score=0.75,
                passed=True,
                reasoning=(
                    "Apollo unavailable; Exa web search found a LinkedIn profile URL — "
                    "identity independently verified via web."
                ),
                method="deterministic",
                confidence="medium",
                degraded=False,
                caveats=[
                    f"Apollo unavailable ({str(skipped)[:120]}); "
                    "identity verified via Exa web search (LinkedIn URL found)."
                ],
                details={"exa_linkedin_found": True, "source": "exa-web"},
            )
        return EvalVerdict(
            name="entity_resolution",
            score=0.45,
            passed=False,
            reasoning=(
                "Apollo unavailable; Exa web search ran but found no LinkedIn URL. "
                "Identity not independently verified."
            ),
            method="deterministic",
            confidence="low",
            degraded=True,
            caveats=[
                f"Apollo unavailable ({str(skipped)[:120]}); "
                "Exa web search returned no LinkedIn URL."
            ],
            details={"exa_linkedin_found": False, "source": "exa-web"},
        )

    # ── Ambiguous path ────────────────────────────────────────────────────────
    if enrich_result.status == "ambiguous":
        return EvalVerdict(
            name="entity_resolution",
            score=0.3,
            passed=False,
            reasoning="Apollo returned multiple candidates; no single entity resolved.",
            method="deterministic",
            confidence="medium",
            degraded=True,
            caveats=["Apollo returned multiple candidates; disambiguation required."],
            details={"candidate_count": len(enrich_result.candidates)},
        )

    # ── Real-match path ───────────────────────────────────────────────────────
    if enrich_result.status != "matched" or person is None:
        return EvalVerdict(
            name="entity_resolution",
            score=0.0,
            passed=False,
            reasoning="Enrich status is not 'matched' and no PersonFacts present.",
            method="deterministic",
            confidence="high",
        )

    brief = get_ingest_brief(run)
    target_name = (run.input.name or "") or (brief.display_name if brief else "")

    signals: dict[str, float | None] = {}
    signals["name_match"] = _token_overlap(person.name or "", target_name)

    if run.input.linkedin_url and person.linkedin_url:
        signals["linkedin_match"] = (
            1.0
            if run.input.linkedin_url.rstrip("/") == person.linkedin_url.rstrip("/")
            else 0.0
        )
    else:
        signals["linkedin_match"] = None  # signal not available

    if run.input.company and person.organization:
        signals["org_match"] = _token_overlap(
            person.organization or "", run.input.company or ""
        )
    else:
        signals["org_match"] = None

    available = {k: v for k, v in signals.items() if v is not None}
    score = sum(available.values()) / len(available) if available else 0.5
    passed = score >= _PASS_THRESHOLD
    confidence: str = "high" if len(available) >= 2 else "medium" if available else "low"

    return EvalVerdict(
        name="entity_resolution",
        score=round(score, 4),
        passed=passed,
        reasoning=(
            f"Entity match scored {score:.2f} across {len(available)} signal(s): "
            + ", ".join(f"{k}={v:.2f}" for k, v in available.items())
        ),
        method="deterministic",
        confidence=confidence,  # type: ignore[arg-type]
        details=signals,
    )
