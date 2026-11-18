from __future__ import annotations

from app.evals.base import EvalContext
from app.evals.schemas import ClaimGroundedness, EvalVerdict

_PASS_THRESHOLD = 0.80
_THIN_SNIPPET_CHARS = 80  # snippets shorter than this are considered thin


async def evaluate(ctx: EvalContext) -> EvalVerdict:
    """LLM-judge eval: does every claim trace to a real, cited source?

    Deterministic guardrails wrap the judge:
    - A claim citing an id not in run.sources hard-fails without asking the LLM.
    - Judge supporting_source_ids are clamped to the claim's cited set.
    LLM variance can only lower a deterministically-gated score, never inflate it.
    """
    run = ctx.run

    if run.article is None or not run.article.claims:
        return EvalVerdict(
            name="groundedness",
            score=0.0,
            passed=False,
            reasoning="No article or claims to evaluate.",
            method="llm_judge",
            confidence="low",
            degraded=True,
            caveats=["No article to evaluate — run did not complete."],
        )

    if ctx.judge is None:
        raise ValueError("groundedness eval requires a JudgeClient")

    claims = run.article.claims
    source_map = {s.id: s for s in run.sources}
    claim_source_map = run.claim_source_map or {}

    # ── Deterministic pre-check: non-existent source ids ──────────────────
    hard_fails: set[int] = set()
    for i, claim in enumerate(claims):
        cited = claim_source_map.get(str(i), claim.source_ids)
        if any(sid not in source_map for sid in cited):
            hard_fails.add(i)

    judge_claims = [
        {
            "index": i,
            "text": claim.text,
            "cited_source_ids": claim_source_map.get(str(i), claim.source_ids),
        }
        for i, claim in enumerate(claims)
        if i not in hard_fails
    ]

    cited_ids = {sid for c in judge_claims for sid in c["cited_source_ids"]}
    sources_for_judge = {sid: source_map[sid] for sid in cited_ids if sid in source_map}

    thin_snippets = any(
        not s.snippet or len(s.snippet) < _THIN_SNIPPET_CHARS
        for s in sources_for_judge.values()
    )

    claim_results: list[ClaimGroundedness] = []

    # Hard-failed claims (deterministic — no judge call)
    for i in hard_fails:
        claim = claims[i]
        cited = claim_source_map.get(str(i), claim.source_ids)
        claim_results.append(
            ClaimGroundedness(
                claim_index=i,
                claim_text=claim.text,
                supported=False,
                cited_source_ids=cited,
                supporting_source_ids=[],
                reasoning="Cited source ID does not exist in run.sources (deterministic fail).",
            )
        )

    # Judge remaining claims in one batched call
    if judge_claims and sources_for_judge:
        judge_out = await ctx.judge.judge_groundedness(judge_claims, sources_for_judge)
        judgements = {j.claim_index: j for j in judge_out.claims}

        for c in judge_claims:
            i = c["index"]
            j = judgements.get(i)
            if j is None:
                claim_results.append(
                    ClaimGroundedness(
                        claim_index=i,
                        claim_text=claims[i].text,
                        supported=False,
                        cited_source_ids=c["cited_source_ids"],
                        supporting_source_ids=[],
                        reasoning="Judge did not return a verdict for this claim.",
                    )
                )
                continue
            # Clamp: judge cannot cite ids outside the claim's cited set
            valid_supporting = [
                sid for sid in j.supporting_source_ids if sid in set(c["cited_source_ids"])
            ]
            claim_results.append(
                ClaimGroundedness(
                    claim_index=i,
                    claim_text=claims[i].text,
                    supported=j.supported,
                    cited_source_ids=c["cited_source_ids"],
                    supporting_source_ids=valid_supporting,
                    reasoning=j.reasoning,
                )
            )

    claim_results.sort(key=lambda c: c.claim_index)

    supported_count = sum(1 for c in claim_results if c.supported)
    total_count = len(claims)
    score = supported_count / total_count if total_count else 0.0

    caveats: list[str] = []
    confidence: str = "high"
    if hard_fails:
        caveats.append(
            f"{len(hard_fails)} claim(s) hard-failed: cited non-existent source id."
        )
        confidence = "medium"
    if thin_snippets:
        caveats.append("Some source snippets are short; judge may be under-informed.")
        confidence = "low"

    return EvalVerdict(
        name="groundedness",
        score=round(score, 4),
        passed=score >= _PASS_THRESHOLD,
        reasoning=(
            f"{supported_count}/{total_count} claims supported by retrieved sources."
            + (f" {len(hard_fails)} hard-failed (bad source id)." if hard_fails else "")
        ),
        method="llm_judge",
        confidence=confidence,  # type: ignore[arg-type]
        degraded=bool(hard_fails or thin_snippets),
        caveats=caveats,
        details={
            "claims": [c.model_dump() for c in claim_results],
            "supported_count": supported_count,
            "total_count": total_count,
        },
    )
