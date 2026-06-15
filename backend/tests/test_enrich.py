import pytest

from app.errors import EnrichNotFoundError
from app.schemas import Brief, FormRequest
from app.stages.enrich import enrich
from app.stages.ingest import ingest


@pytest.fixture
def brief() -> Brief:
    return Brief(
        name="Sam Altman",
        company="OpenAI",
        display_name="Sam Altman",
        search_terms=["Sam Altman", "OpenAI"],
    )


async def test_confident_match(fake_apollo_client, brief):
    result, sources = await enrich(brief, fake_apollo_client)

    assert result.status == "matched"
    assert result.person is not None
    assert result.person.name == "Sam Altman"
    assert result.person.organization == "OpenAI"
    assert result.person.apollo_id == "apollo_fake_001"
    # The Apollo source should be included
    assert len(sources) == 1
    assert sources[0].kind == "apollo"


async def test_apollo_upstream_error_falls_back_to_stub(fake_apollo_client_degraded, brief):
    result, sources = await enrich(brief, fake_apollo_client_degraded)

    assert result.status == "matched"
    assert result.person is not None
    assert result.person.raw.get("_source") == "form-input"
    assert "_apollo_skipped" in result.person.raw
    # No Apollo source attached in fallback
    assert sources == []


async def test_ambiguous_match_returns_candidates(brief):
    from unittest.mock import AsyncMock, MagicMock

    from app.clients import ApolloClient

    apollo = MagicMock(spec=ApolloClient)
    # match returns no confident person
    apollo.match = AsyncMock(return_value={"person": {}})
    apollo.search = AsyncMock(
        return_value={
            "people": [
                {
                    "id": "a1",
                    "name": "Sam Altman",
                    "title": "CEO",
                    "organization_name": "OpenAI",
                    "linkedin_url": "https://linkedin.com/in/samaltman",
                },
                {
                    "id": "a2",
                    "name": "Sam Altman",
                    "title": "Investor",
                    "organization_name": "Y Combinator",
                    "linkedin_url": None,
                },
            ]
        }
    )

    result, sources = await enrich(brief, apollo)

    assert result.status == "ambiguous"
    assert len(result.candidates) == 2
    assert result.candidates[0].confidence == 1.0
    assert result.candidates[1].confidence == 0.5
    assert len(sources) == 1  # top search result attached


async def test_no_apollo_results_raises(brief):
    from unittest.mock import AsyncMock, MagicMock

    from app.clients import ApolloClient

    apollo = MagicMock(spec=ApolloClient)
    apollo.match = AsyncMock(return_value={"person": {}})
    apollo.search = AsyncMock(return_value={"people": []})

    with pytest.raises(EnrichNotFoundError):
        await enrich(brief, apollo)
