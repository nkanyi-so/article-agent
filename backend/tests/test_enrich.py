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


async def test_confident_match(fake_apollo_client, fake_exa_client, brief):
    result, sources = await enrich(brief, fake_apollo_client, fake_exa_client)

    assert result.status == "matched"
    assert result.person is not None
    assert result.person.name == "Sam Altman"
    assert result.person.organization == "OpenAI"
    assert result.person.apollo_id == "apollo_fake_001"
    # The Apollo source should be included; Exa not called
    assert len(sources) == 1
    assert sources[0].kind == "apollo"
    fake_exa_client.search_web.assert_not_called()


async def test_apollo_upstream_error_falls_back_to_exa(
    fake_apollo_client_degraded, fake_exa_client, brief
):
    """Apollo 403 triggers Exa web-search fallback. Default fake returns no hits."""
    result, sources = await enrich(brief, fake_apollo_client_degraded, fake_exa_client)

    assert result.status == "matched"
    assert result.person is not None
    assert result.person.raw.get("_source") == "exa-web"
    assert "_apollo_skipped" in result.person.raw
    assert result.person.raw["_exa_linkedin_found"] is False
    fake_exa_client.search_web.assert_called_once()


async def test_apollo_upstream_error_exa_finds_linkedin(
    fake_apollo_client_degraded, fake_exa_hits, brief
):
    """When Exa finds a LinkedIn URL, it is stored in PersonFacts."""
    from unittest.mock import AsyncMock, MagicMock

    from app.clients import ExaClient, ExaHit
    from types import SimpleNamespace

    raw = SimpleNamespace(
        url="https://www.linkedin.com/in/samaltman",
        title="Sam Altman - CEO at OpenAI",
        published_date=None,
        text="Sam Altman is the CEO of OpenAI.",
        highlights=["Sam Altman is the CEO of OpenAI."],
    )
    exa = MagicMock(spec=ExaClient)
    exa.search_web = AsyncMock(return_value=[ExaHit(raw, 0)])

    result, sources = await enrich(brief, fake_apollo_client_degraded, exa)

    assert result.person.raw.get("_source") == "exa-web"
    assert result.person.raw["_exa_linkedin_found"] is True
    assert result.person.linkedin_url == "https://www.linkedin.com/in/samaltman"
    assert len(sources) == 1
    assert sources[0].kind == "exa"


async def test_apollo_upstream_error_exa_also_fails(
    fake_apollo_client_degraded, brief
):
    """When both Apollo and Exa fail, falls back to form inputs."""
    from unittest.mock import AsyncMock, MagicMock

    from app.clients import ExaClient
    from app.errors import UpstreamError

    exa = MagicMock(spec=ExaClient)
    exa.search_web = AsyncMock(side_effect=Exception("Exa connection timeout"))

    result, sources = await enrich(brief, fake_apollo_client_degraded, exa)

    assert result.person.raw.get("_source") == "form-input"
    assert sources == []


async def test_ambiguous_match_returns_candidates(fake_exa_client, brief):
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

    result, sources = await enrich(brief, apollo, fake_exa_client)

    assert result.status == "ambiguous"
    assert len(result.candidates) == 2
    assert result.candidates[0].confidence == 1.0
    assert result.candidates[1].confidence == 0.5
    assert len(sources) == 1  # top search result attached
    fake_exa_client.search_web.assert_not_called()  # Exa not used when Apollo returns candidates


async def test_no_apollo_results_raises(fake_exa_client, brief):
    from unittest.mock import AsyncMock, MagicMock

    from app.clients import ApolloClient

    apollo = MagicMock(spec=ApolloClient)
    apollo.match = AsyncMock(return_value={"person": {}})
    apollo.search = AsyncMock(return_value={"people": []})

    with pytest.raises(EnrichNotFoundError):
        await enrich(brief, apollo, fake_exa_client)
