from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.clients import ClaudeClient, ExaClient, ExaHit
from app.errors import EmptyResearchError
from app.schemas import (
    Brief,
    ChosenAngle,
    EnrichResult,
    ResearchResult,
    Source,
)

# How far back to search for news.
RESEARCH_LOOKBACK_DAYS = 180


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hit_to_source(hit: ExaHit) -> Source:
    snippet: str | None = None
    if hit.highlights:
        snippet = " | ".join(hit.highlights[:2])
    elif hit.text:
        snippet = hit.text[:300]
    return Source(
        id=hit.id,
        kind="exa",
        url=hit.url,
        title=hit.title,
        snippet=snippet,
        retrieved_at=datetime.now(timezone.utc),
    )


def _hit_to_context(hit: ExaHit) -> str:
    parts: list[str] = [f"[{hit.id}]"]
    if hit.title:
        parts.append(f"Title: {hit.title}")
    if hit.url:
        parts.append(f"URL: {hit.url}")
    if hit.published_date:
        parts.append(f"Published: {hit.published_date}")
    if hit.highlights:
        parts.append("Highlights: " + " | ".join(hit.highlights[:3]))
    elif hit.text:
        parts.append(f"Excerpt: {hit.text[:500]}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Stage
# ---------------------------------------------------------------------------


async def research(
    brief: Brief,
    enrich_result: EnrichResult,
    exa: ExaClient,
    claude: ClaudeClient,
) -> tuple[ResearchResult, list[Source]]:
    """Stage 3: Find recent news via Exa, then have Claude pick ONE grounded angle.

    Raises EmptyResearchError if Exa returns nothing — we never let Claude
    invent an angle from thin air.
    """
    person = enrich_result.person
    org = (person.organization if person else None) or brief.company or ""
    query = " ".join(filter(None, [brief.display_name, org]))

    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=RESEARCH_LOOKBACK_DAYS)
    ).strftime("%Y-%m-%dT00:00:00.000Z")

    hits = await exa.search_news(query, start_published_date=cutoff, num_results=8)

    if not hits:
        raise EmptyResearchError(
            f"Exa returned no news for '{query}' in the last {RESEARCH_LOOKBACK_DAYS} days. "
            "Try a different name or company, or provide a LinkedIn URL."
        )

    sources = [_hit_to_source(h) for h in hits]
    source_ids = [s.id for s in sources]
    context = "\n\n---\n\n".join(_hit_to_context(h) for h in hits)

    person_desc = (
        f"{person.name}, {person.title} at {person.organization}"
        if person and person.name
        else brief.display_name
    )

    prompt = f"""You are a senior editorial researcher. Select ONE newsworthy angle for an article about {person_desc}.

SOURCES (you MUST ground your angle in these — do not use any facts not found here):

{context}

Available source IDs: {source_ids}

Choose the single most compelling and timely angle grounded in the sources above.

Your supporting_source_ids MUST be a non-empty subset of the Available source IDs listed above.
Do not reference any person, company, or event not mentioned in the sources."""

    angle: ChosenAngle = await claude.parse(  # type: ignore[assignment]
        messages=[{"role": "user", "content": prompt}],
        output_format=ChosenAngle,
        max_tokens=2048,
    )

    # Validate: strip any source IDs Claude hallucinated.
    valid_ids = set(source_ids)
    angle.supporting_source_ids = [
        sid for sid in angle.supporting_source_ids if sid in valid_ids
    ]
    angle_fallback = False
    if not angle.supporting_source_ids:
        # Fallback: use the first two sources if Claude returned nothing valid.
        angle.supporting_source_ids = source_ids[:2]
        angle_fallback = True

    return ResearchResult(angle=angle, sources=sources, angle_fallback=angle_fallback), sources
