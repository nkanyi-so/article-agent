import pytest

from app.errors import ClaudeError
from app.schemas import (
    Brief,
    ChosenAngle,
    DraftArticle,
    EnrichResult,
    PersonFacts,
    ResearchResult,
    Source,
)
from app.stages.draft import draft

from datetime import datetime, timezone


def _ts() -> datetime:
    return datetime.now(timezone.utc)


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
            raw={"_source": "form-input"},
        ),
    )


@pytest.fixture
def research_result() -> ResearchResult:
    sources = [
        Source(id="exa:0", kind="exa", url="https://ex.com/0", title="T0",
               snippet="Sam Altman postponed South Korea visit citing personal reasons.", retrieved_at=_ts()),
        Source(id="exa:1", kind="exa", url="https://ex.com/1", title="T1",
               snippet="Samsung had prepared a multi-day schedule at Suwon campus.", retrieved_at=_ts()),
        Source(id="exa:2", kind="exa", url="https://ex.com/2", title="T2",
               snippet="Naver and Kakao confirmed executive meetings with Altman.", retrieved_at=_ts()),
    ]
    return ResearchResult(
        angle=ChosenAngle(
            headline="Altman Postpones South Korea Trip",
            angle="Postponement disrupts Samsung chip talks.",
            rationale="Samsung had concrete meetings lined up.",
            supporting_source_ids=["exa:0", "exa:1"],
        ),
        sources=sources,
    )


async def test_happy_path(brief, enrich_result, research_result, fake_claude_client, canned_article):
    result, sources = await draft(brief, enrich_result, research_result, fake_claude_client)

    assert result.article.title == canned_article.title
    assert len(result.article.claims) == 3
    # claim_source_map keys are "0", "1", "2"
    assert set(result.claim_source_map.keys()) == {"0", "1", "2"}
    # All cited source IDs must be real
    valid_ids = {"exa:0", "exa:1", "exa:2"}
    for ids in result.claim_source_map.values():
        for sid in ids:
            assert sid in valid_ids


async def test_claim_source_map_indices_match_claims(brief, enrich_result, research_result, fake_claude_client):
    result, _ = await draft(brief, enrich_result, research_result, fake_claude_client)

    for i, claim in enumerate(result.article.claims):
        assert str(i) in result.claim_source_map
        assert result.claim_source_map[str(i)] == claim.source_ids


async def test_hallucinated_source_ids_in_claims_stripped(brief, enrich_result, research_result):
    from unittest.mock import MagicMock
    from app.clients import ClaudeClient
    from app.schemas import Claim

    bad_article = DraftArticle(
        title="Test",
        body="Body.",
        claims=[
            Claim(text="Good claim.", source_ids=["exa:0"]),
            Claim(text="Bad claim citing fake source.", source_ids=["exa:FAKE", "exa:NONEXIST"]),
        ],
    )

    async def _parse(*, messages, output_format, max_tokens=4096):
        return bad_article

    claude = MagicMock(spec=ClaudeClient)
    claude.parse = _parse

    result, _ = await draft(brief, enrich_result, research_result, claude)

    valid_ids = {"exa:0", "exa:1", "exa:2"}
    for claim in result.article.claims:
        for sid in claim.source_ids:
            assert sid in valid_ids
    # Hallucinated claim got fallback ids, not stripped to empty
    assert len(result.article.claims[1].source_ids) >= 1


async def test_no_claims_raises_claude_error(brief, enrich_result, research_result):
    from unittest.mock import MagicMock
    from app.clients import ClaudeClient

    empty_article = DraftArticle(title="T", body="B.", claims=[])

    async def _parse(*, messages, output_format, max_tokens=4096):
        return empty_article

    claude = MagicMock(spec=ClaudeClient)
    claude.parse = _parse

    with pytest.raises(ClaudeError):
        await draft(brief, enrich_result, research_result, claude)
