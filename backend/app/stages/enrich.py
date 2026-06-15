from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.clients import ApolloClient
from app.errors import EnrichNotFoundError, UpstreamError
from app.schemas import (
    Brief,
    EnrichCandidate,
    EnrichResult,
    PersonFacts,
    Source,
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
    """Fallback person record built entirely from form inputs.

    Used when Apollo is unavailable (plan restriction, network error, etc.).
    Downstream stages still run; the article is grounded in Exa sources only.
    """
    return PersonFacts(
        name=brief.name or brief.display_name,
        organization=brief.company,
        raw={"_source": "form-input", "_apollo_skipped": reason},
    )


async def enrich(
    brief: Brief,
    apollo: ApolloClient,
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
        logger.warning("Apollo match unavailable (%s) — falling back to form inputs.", exc)
        return (
            EnrichResult(status="matched", person=_stub_from_brief(brief, str(exc))),
            [],  # no Apollo source to attach
        )

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
        logger.warning("Apollo search unavailable (%s) — falling back to form inputs.", exc)
        return (
            EnrichResult(status="matched", person=_stub_from_brief(brief, str(exc))),
            [],
        )

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
