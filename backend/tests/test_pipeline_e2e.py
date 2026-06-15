from unittest.mock import AsyncMock, patch

import pytest

from app.runs import run_form_pipeline
from app.schemas import FormRequest


def _make_fake_clients(apollo, exa, claude):
    class _FakeClients:
        def __init__(self):
            self.apollo = apollo
            self.exa = exa
            self.claude = claude

        async def aclose(self):
            pass

    return _FakeClients()


async def test_completed_run(fake_apollo_client, fake_exa_client, fake_claude_client):
    fc = _make_fake_clients(fake_apollo_client, fake_exa_client, fake_claude_client)

    with patch("app.runs.Clients", return_value=fc):
        run = await run_form_pipeline(FormRequest(name="Sam Altman", company="OpenAI"))

    assert run.status == "completed"
    assert run.article is not None
    assert len(run.article.claims) == 3
    assert run.claim_source_map is not None
    assert set(run.claim_source_map.keys()) == {"0", "1", "2"}

    # sources must be deduped
    source_ids = [s.id for s in run.sources]
    assert len(source_ids) == len(set(source_ids))

    # all four stage envelopes present
    assert run.ingest is not None and run.ingest.status == "ok"
    assert run.enrich is not None and run.enrich.status == "ok"
    assert run.research is not None and run.research.status == "ok"
    assert run.draft is not None and run.draft.status == "ok"


async def test_failed_run_empty_exa(fake_apollo_client, fake_claude_client):
    from unittest.mock import MagicMock
    from app.clients import ExaClient

    empty_exa = MagicMock(spec=ExaClient)
    empty_exa.search_news = AsyncMock(return_value=[])

    fc = _make_fake_clients(fake_apollo_client, empty_exa, fake_claude_client)

    with patch("app.runs.Clients", return_value=fc):
        run = await run_form_pipeline(FormRequest(name="NoNews Person"))

    assert run.status == "failed"
    assert run.error is not None
    assert run.error.code == "exa_empty"
    assert run.error.retryable is True
    assert run.article is None


async def test_needs_disambiguation_on_ambiguous_enrich(fake_exa_client, fake_claude_client):
    from unittest.mock import AsyncMock, MagicMock
    from app.clients import ApolloClient

    ambiguous_apollo = MagicMock(spec=ApolloClient)
    ambiguous_apollo.match = AsyncMock(return_value={"person": {}})
    ambiguous_apollo.search = AsyncMock(
        return_value={
            "people": [
                {"id": "a1", "name": "Sam A", "title": "CEO", "organization_name": "OAI",
                 "linkedin_url": None},
                {"id": "a2", "name": "Sam A", "title": "Investor", "organization_name": "YC",
                 "linkedin_url": None},
            ]
        }
    )
    ambiguous_apollo.aclose = AsyncMock()

    fc = _make_fake_clients(ambiguous_apollo, fake_exa_client, fake_claude_client)

    with patch("app.runs.Clients", return_value=fc):
        run = await run_form_pipeline(FormRequest(name="Sam A"))

    assert run.status == "needs_disambiguation"
    assert run.article is None
    assert run.enrich is not None
    assert run.enrich.status == "ok"


async def test_apollo_degraded_still_completes(
    fake_apollo_client_degraded, fake_exa_client, fake_claude_client
):
    fc = _make_fake_clients(fake_apollo_client_degraded, fake_exa_client, fake_claude_client)

    with patch("app.runs.Clients", return_value=fc):
        run = await run_form_pipeline(FormRequest(name="Sam Altman", company="OpenAI"))

    # Apollo degraded → enrich falls back to Exa web search → pipeline continues
    assert run.status == "completed"
    assert run.enrich.status == "ok"

    from app.evals.base import get_enrich_result
    enrich_out = get_enrich_result(run)
    assert enrich_out is not None
    assert enrich_out.person is not None
    assert enrich_out.person.raw.get("_source") == "exa-web"
    assert run.article is not None
