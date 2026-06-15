from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.clients import ApolloClient, ClaudeClient, ExaClient, ExaHit
from app.evals.judge import JudgeClient
from app.evals.schemas import (
    AngleSupportJudgeOutput,
    ClaimJudgement,
    GroundednessJudgeOutput,
)
from app.errors import UpstreamError
from app.evals.schemas import EvalReport  # noqa: F401 — triggers Run.model_rebuild
from app.schemas import (
    Brief,
    ChosenAngle,
    Claim,
    DraftArticle,
    FormRequest,
    Run,
)

# EvalReport is imported under TYPE_CHECKING in schemas.py; rebuild so model_validate works.
Run.model_rebuild()

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Exa raw hit builder + ExaHit fixtures
# ---------------------------------------------------------------------------


def _raw_hit(url: str, title: str, text: str) -> SimpleNamespace:
    return SimpleNamespace(
        url=url,
        title=title,
        published_date="2026-06-01T00:00:00Z",
        text=text,
        highlights=[text[:120]],
    )


@pytest.fixture
def fake_exa_hits() -> list[ExaHit]:
    raws = [
        _raw_hit(
            "https://example.com/news/0",
            "Sam Altman postpones South Korea visit",
            "OpenAI CEO Sam Altman has postponed a visit to South Korea scheduled for next week, "
            "citing personal reasons. He was due to meet Samsung Electronics executives.",
        ),
        _raw_hit(
            "https://example.com/news/1",
            "Samsung AI chip talks stall as Altman delays Seoul trip",
            "Samsung Electronics had prepared a multi-day schedule for Altman at its Suwon campus. "
            "The postponement leaves the timeline for a potential chip partnership in limbo.",
        ),
        _raw_hit(
            "https://example.com/news/2",
            "Naver and Kakao await Altman visit outcome",
            "Portal operator Naver and Kakao had confirmed executive-level meetings with Altman. "
            "Both companies are exploring AI licensing agreements with OpenAI.",
        ),
    ]
    return [ExaHit(r, i) for i, r in enumerate(raws)]


# ---------------------------------------------------------------------------
# Canned Claude outputs
# ---------------------------------------------------------------------------


@pytest.fixture
def canned_angle() -> ChosenAngle:
    return ChosenAngle(
        headline="Altman Postpones South Korea Trip, Leaving Samsung Chip Talks in Limbo",
        angle=(
            "Sam Altman's last-minute postponement disrupts AI chip partnership "
            "discussions with Samsung Electronics."
        ),
        rationale=(
            "The postponement directly stalls concrete chip cooperation talks "
            "Samsung had scheduled at its Suwon campus."
        ),
        supporting_source_ids=["exa:0", "exa:1"],
    )


@pytest.fixture
def canned_article() -> DraftArticle:
    return DraftArticle(
        title="Altman Postpones South Korea Trip, Leaving Samsung Chip Talks in Limbo",
        body=(
            "OpenAI CEO Sam Altman has postponed his visit to South Korea scheduled for next week.\n\n"
            "Samsung Electronics had prepared a multi-day schedule at its Suwon campus to discuss "
            "custom AI chip development.\n\n"
            "Naver and Kakao executives had also confirmed meetings with Altman during the planned trip."
        ),
        claims=[
            Claim(
                text="Sam Altman postponed his South Korea visit citing personal reasons.",
                source_ids=["exa:0"],
            ),
            Claim(
                text="Samsung had a multi-day schedule at Suwon to discuss AI chip development.",
                source_ids=["exa:1"],
            ),
            Claim(
                text="Naver and Kakao confirmed executive meetings with Altman.",
                source_ids=["exa:2"],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Fake clients
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_claude_client(canned_angle: ChosenAngle, canned_article: DraftArticle) -> ClaudeClient:
    async def _parse(*, messages, output_format, max_tokens=4096):
        if output_format is ChosenAngle:
            return canned_angle
        return canned_article

    client = MagicMock(spec=ClaudeClient)
    client.parse = _parse
    return client


@pytest.fixture
def fake_exa_client(fake_exa_hits: list[ExaHit]) -> ExaClient:
    client = MagicMock(spec=ExaClient)
    client.search_news = AsyncMock(return_value=fake_exa_hits)
    # search_web is used by the enrich stage when Apollo is unavailable.
    # Default: empty results (no LinkedIn found). Override in individual tests as needed.
    client.search_web = AsyncMock(return_value=[])
    return client


@pytest.fixture
def fake_apollo_client() -> ApolloClient:
    client = MagicMock(spec=ApolloClient)
    client.match = AsyncMock(
        return_value={
            "person": {
                "id": "apollo_fake_001",
                "name": "Sam Altman",
                "title": "CEO",
                "organization_name": "OpenAI",
                "linkedin_url": "https://www.linkedin.com/in/samaltman",
                "city": "San Francisco",
            }
        }
    )
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def fake_apollo_client_degraded() -> ApolloClient:
    """Apollo client that raises UpstreamError (simulates free-plan 403)."""
    client = MagicMock(spec=ApolloClient)
    client.match = AsyncMock(
        side_effect=UpstreamError(
            "Apollo people/match returned HTTP 403: API_INACCESSIBLE on free plan"
        )
    )
    client.aclose = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# Fixture-loaded Run objects
# ---------------------------------------------------------------------------


def _load_run(name: str) -> Run:
    data = json.loads((FIXTURES / name).read_text())
    return Run.model_validate(data)


@pytest.fixture
def sample_run_completed() -> Run:
    return _load_run("sample_run_completed.json")


@pytest.fixture
def sample_run_degraded() -> Run:
    return _load_run("sample_run_degraded.json")


@pytest.fixture
def sample_run_failed() -> Run:
    return _load_run("sample_run_failed.json")


# ---------------------------------------------------------------------------
# Mock judge (dynamic — returns "supported=True" for every claim it receives)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_judge() -> JudgeClient:
    """JudgeClient that marks every passed claim as supported — no API calls."""
    judge = MagicMock(spec=JudgeClient)

    async def _judge_groundedness(claims: list[dict], sources_by_id):
        return GroundednessJudgeOutput(
            claims=[
                ClaimJudgement(
                    claim_index=c["index"],
                    supported=True,
                    supporting_source_ids=c["cited_source_ids"][:1],
                    reasoning="Snippet directly supports this claim.",
                )
                for c in claims
            ],
            overall_reasoning="All provided claims are well-supported.",
        )

    judge.judge_groundedness = AsyncMock(side_effect=_judge_groundedness)
    judge.judge_angle_support = AsyncMock(
        return_value=AngleSupportJudgeOutput(
            supported=True,
            score=0.9,
            supporting_source_ids=["exa:0", "exa:1"],
            reasoning="The snippets directly support the angle.",
        )
    )
    return judge
