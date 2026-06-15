import pytest

from app.errors import EmptyResearchError
from app.schemas import Brief, EnrichResult, PersonFacts
from app.stages.research import research


@pytest.fixture
def brief() -> Brief:
    return Brief(
        name="Sam Altman",
        company="OpenAI",
        display_name="Sam Altman",
        search_terms=["Sam Altman", "OpenAI"],
    )


@pytest.fixture
def enrich_result() -> EnrichResult:
    return EnrichResult(
        status="matched",
        person=PersonFacts(
            name="Sam Altman",
            title="CEO",
            organization="OpenAI",
            raw={"_source": "form-input", "_apollo_skipped": "free plan"},
        ),
    )


async def test_happy_path(brief, enrich_result, fake_exa_client, fake_claude_client, canned_angle):
    result, sources = await research(brief, enrich_result, fake_exa_client, fake_claude_client)

    assert result.angle.headline == canned_angle.headline
    assert result.angle.angle == canned_angle.angle
    assert len(result.sources) == 3
    assert all(s.kind == "exa" for s in result.sources)
    assert len(sources) == 3


async def test_empty_exa_raises(brief, enrich_result, fake_claude_client):
    from unittest.mock import AsyncMock, MagicMock

    from app.clients import ExaClient

    empty_exa = MagicMock(spec=ExaClient)
    empty_exa.search_news = AsyncMock(return_value=[])

    with pytest.raises(EmptyResearchError):
        await research(brief, enrich_result, empty_exa, fake_claude_client)


async def test_hallucinated_source_ids_stripped(brief, enrich_result, fake_exa_client):
    from unittest.mock import MagicMock

    from app.clients import ClaudeClient
    from app.schemas import ChosenAngle

    # Claude returns an angle citing a source id that doesn't exist
    hallucinated_angle = ChosenAngle(
        headline="Test headline",
        angle="Test angle",
        rationale="Test rationale",
        supporting_source_ids=["exa:999", "exa:FAKE"],
    )

    async def _parse(*, messages, output_format, max_tokens=4096):
        return hallucinated_angle

    claude = MagicMock(spec=ClaudeClient)
    claude.parse = _parse

    result, _ = await research(brief, enrich_result, fake_exa_client, claude)

    # Hallucinated ids must be stripped; fallback to first two real sources
    valid_ids = {s.id for s in result.sources}
    assert all(sid in valid_ids for sid in result.angle.supporting_source_ids)
    # Fallback should give us at least something
    assert len(result.angle.supporting_source_ids) >= 1


async def test_source_ids_subset_of_exa_results(brief, enrich_result, fake_exa_client, fake_claude_client):
    result, _ = await research(brief, enrich_result, fake_exa_client, fake_claude_client)

    valid_ids = {s.id for s in result.sources}
    for sid in result.angle.supporting_source_ids:
        assert sid in valid_ids
