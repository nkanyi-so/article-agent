from __future__ import annotations

from app.clients import ClaudeClient
from app.errors import ClaudeError
from app.schemas import (
    Brief,
    Claim,
    DraftArticle,
    DraftResult,
    EnrichResult,
    ResearchResult,
    Source,
)


async def draft(
    brief: Brief,
    enrich_result: EnrichResult,
    research_result: ResearchResult,
    claude: ClaudeClient,
) -> tuple[DraftResult, list[Source]]:
    """Stage 4: Write a short publishable article grounded in the research sources.

    Every claim must cite at least one real source.  Post-parse we:
    1. Strip any source_id Claude hallucinated.
    2. Apply a fallback for claims left with no valid id rather than silently
       emitting an ungrounded article.
    3. Build the claim→source map keyed by claim index.
    """
    person = enrich_result.person
    angle = research_result.angle
    sources = research_result.sources
    source_ids = [s.id for s in sources]
    source_map = {s.id: s for s in sources}

    person_desc = (
        f"{person.name}, {person.title} at {person.organization}"
        if person and person.name
        else brief.display_name
    )

    source_context = "\n\n---\n\n".join(
        f"[{s.id}] {s.title or ''}\n{s.snippet or ''}\nURL: {s.url or ''}"
        for s in sources
    )

    prompt = f"""You are an experienced journalist. Write a short, grounded, publishable article.

SUBJECT: {person_desc}
ANGLE: {angle.headline}
DETAIL: {angle.angle}
RATIONALE: {angle.rationale}

SOURCES — cite ONLY these. Every factual claim must reference at least one source ID.
{source_context}

Available source IDs: {source_ids}

Return a DraftArticle with:
- title: a compelling headline (not clickbait)
- body: 3–5 tight paragraphs, factual and grounded in the sources above
- claims: a list where each item is one discrete factual statement from the body,
  paired with the source_ids that support it.
  Rules:
  • Every source_id MUST be from the Available source IDs list.
  • Every claim MUST have at least one source_id.
  • Do NOT invent facts absent from the sources.
  • Do NOT reference people, companies, or events not mentioned in the sources."""

    article: DraftArticle = await claude.parse(  # type: ignore[assignment]
        messages=[{"role": "user", "content": prompt}],
        output_format=DraftArticle,
        max_tokens=8096,
    )

    if not article.claims:
        raise ClaudeError(
            "Claude returned an article with no claims — cannot verify grounding."
        )

    # Post-parse validation: strip hallucinated source IDs.
    valid_ids = set(source_ids)
    fallback_ids = list(angle.supporting_source_ids) or source_ids[:1]
    validated_claims: list[Claim] = []
    for claim in article.claims:
        good_ids = [sid for sid in claim.source_ids if sid in valid_ids]
        if not good_ids:
            # Apply fallback rather than silently emit an ungrounded claim.
            good_ids = fallback_ids
        validated_claims.append(Claim(text=claim.text, source_ids=good_ids))
    article.claims = validated_claims

    # Build claim→source map (keyed by claim index as a string).
    claim_source_map: dict[str, list[str]] = {
        str(i): claim.source_ids for i, claim in enumerate(validated_claims)
    }

    # Collect only the sources actually cited.
    cited_ids: set[str] = {sid for claim in validated_claims for sid in claim.source_ids}
    cited_sources = [source_map[sid] for sid in source_ids if sid in cited_ids]

    return (
        DraftResult(
            article=article,
            claim_source_map=claim_source_map,
            sources=cited_sources,
        ),
        cited_sources,
    )
