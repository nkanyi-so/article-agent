from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from app.clients import ApolloClient, ExaClient, ExaHit
from app.errors import EnrichNotFoundError, UpstreamError
from app.schemas import (
    Brief,
    EnrichCandidate,
    EnrichResult,
    PersonFacts,
    Source,
)

_LINKEDIN_RE = re.compile(
    r'https?://([\w-]+\.)?linkedin\.com/in/[\w%-]+', re.IGNORECASE
)

logger = logging.getLogger(__name__)

# Fields we keep from the Apollo payload — enough for grounding, not everything.
_KEPT_FIELDS = {
    "id", "name", "title", "organization_name", "city", "country",
    "linkedin_url", "email", "seniority", "departments",
}


def _confident_match(person: dict) -> bool:
    """True when the Apollo payload has enough data to be a confident single match."""
    return bool(
        person.get("name")
        and (person.get("title") or person.get("organization_name"))
    )


def _to_source(person: dict) -> Source:
    org = person.get("organization_name") or ""
    title = person.get("title") or ""
    snippet = f"{title} at {org}".strip(" at") if (title or org) else None
    return Source(
        id=f"apollo:person:{person.get('id', 'unknown')}",
        kind="apollo",
        url=person.get("linkedin_url"),
        title=person.get("name"),
        snippet=snippet,
        retrieved_at=datetime.now(timezone.utc),
    )


def _to_person_facts(person: dict) -> PersonFacts:
    org: dict[str, Any] = person.get("organization") or {}
    return PersonFacts(
        apollo_id=person.get("id"),
        name=person.get("name"),
        title=person.get("title"),
        organization=person.get("organization_name") or org.get("name"),
        organization_domain=org.get("primary_domain"),
        linkedin_url=person.get("linkedin_url"),
        location=person.get("city") or person.get("country"),
        raw={k: v for k, v in person.items() if k in _KEPT_FIELDS},
    )


def _stub_from_brief(brief: Brief, reason: str) -> PersonFacts:
    """Last-resort fallback when both Apollo and Exa are unavailable."""
    return PersonFacts(
        name=brief.name or brief.display_name,
        organization=brief.company,
        raw={"_source": "form-input", "_apollo_skipped": reason},
    )


def _extract_linkedin_url(hits: list[ExaHit]) -> str | None:
    """Scan Exa results for a LinkedIn profile URL."""
    for hit in hits:
        for text in [hit.url or "", hit.text or "", *hit.highlights]:
            m = _LINKEDIN_RE.search(text)
            if m:
                return m.group(0)
    return None


async def _exa_fallback(
    brief: Brief,
    exa: ExaClient,
    *,
    apollo_error: str,
) -> tuple[EnrichResult, list[Source]]:
    """Enrich via Exa general web search when Apollo is unavailable."""
    parts = [p for p in [brief.name or brief.display_name, brief.company] if p]
    query = " ".join(f'"{p}"' for p in parts)

    try:
        hits = await exa.search_web(query, num_results=5)
    except Exception as exc:
        logger.warning("Exa web search also failed (%s) — falling back to form inputs.", exc)
        return (
            EnrichResult(status="matched", person=_stub_from_brief(brief, apollo_error)),
            [],
        )

    linkedin_url = _extract_linkedin_url(hits)
    person = PersonFacts(
        name=brief.name or brief.display_name,
        organization=brief.company,
        linkedin_url=linkedin_url,
        raw={
            "_source": "exa-web",
            "_apollo_skipped": apollo_error,
            "_exa_linkedin_found": linkedin_url is not None,
            "_exa_result_count": len(hits),
        },
    )

    sources: list[Source] = []
    if hits:
        top = hits[0]
        sources = [
            Source(
                id="exa:enrich:0",
                kind="exa",
                url=top.url,
                title=top.title,
                snippet=(
                    top.highlights[0]
                    if top.highlights
                    else (top.text[:200] if top.text else None)
                ),
                retrieved_at=datetime.now(timezone.utc),
            )
        ]

    return EnrichResult(status="matched", person=person), sources


async def enrich(
    brief: Brief,
    apollo: ApolloClient,
    exa: ExaClient,
) -> tuple[EnrichResult, list[Source]]:
    """Stage 2: Resolve the person via Apollo.

    Strategy:
    1. Call people/match — accept if a single person with name + (title or org) is returned.
    2. Otherwise call mixed_people/api_search — return the top candidates (ambiguous).
    3. If search returns nothing, raise EnrichNotFoundError.
    4. If Apollo is unavailable for any reason (plan restriction, network error), fall back
       to a stub PersonFacts built from form inputs so the pipeline can still run.

    Returns (EnrichResult, sources_list).
    """
    try:
        match_resp = await apollo.match(
            name=brief.name,
            organization_name=brief.company,
            linkedin_url=brief.linkedin_url,
        )
    except UpstreamError as exc:
        logger.warning("Apollo match unavailable (%s) — falling back to Exa web search.", exc)
        return await _exa_fallback(brief, exa, apollo_error=str(exc))

    person = match_resp.get("person") or {}

    if person and _confident_match(person):
        source = _to_source(person)
        return (
            EnrichResult(status="matched", person=_to_person_facts(person)),
            [source],
        )

    # No confident single match — search for candidates.
    keywords = " ".join(filter(None, [brief.name, brief.company, brief.display_name]))
    try:
        search_resp = await apollo.search(q_keywords=keywords, per_page=5)
    except UpstreamError as exc:
        logger.warning("Apollo search unavailable (%s) — falling back to Exa web search.", exc)
        return await _exa_fallback(brief, exa, apollo_error=str(exc))

    people: list[dict] = search_resp.get("people") or []

    if not people:
        raise EnrichNotFoundError(
            f"No Apollo match found for '{brief.display_name}'. "
            "Try providing a LinkedIn URL or company name."
        )

    candidates = [
        EnrichCandidate(
            apollo_id=p.get("id"),
            name=p.get("name"),
            title=p.get("title"),
            organization=p.get("organization_name"),
            linkedin_url=p.get("linkedin_url"),
            confidence=round(1.0 / (i + 1), 2),  # rank-based heuristic
        )
        for i, p in enumerate(people)
    ]
    # Attach the top search result as a representative source.
    sources = [_to_source(people[0])]
    return EnrichResult(status="ambiguous", candidates=candidates), sources
