"""Tests for REST route endpoints and async cleanup.

B6: GET /api/runs, POST /api/runs/{id}/evals, ?evaluate=true stream flag.
B7: CancelledError / generator.aclose() triggers clients.aclose().
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.evals.schemas import EvalReport, EvalVerdict
from app.main import app
from app.runs import _store
from app.schemas import FormRequest


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_store():
    _store.clear()
    yield
    _store.clear()


def _make_fake_clients(apollo, exa, claude):
    class _FakeClients:
        def __init__(self):
            self.apollo = apollo
            self.exa = exa
            self.claude = claude

        async def aclose(self):
            pass

    return _FakeClients()


def _parse_sse(raw: bytes) -> list[dict]:
    events = []
    for block in raw.decode().split("\n\n"):
        block = block.strip()
        if not block:
            continue
        event_name = ""
        data_str = ""
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                data_str = line.removeprefix("data:").strip()
        if event_name:
            events.append({"event": event_name, "data": json.loads(data_str) if data_str else {}})
    return events


def _minimal_report() -> EvalReport:
    return EvalReport(
        overall_score=1.0,
        passed=True,
        complete=True,
        verdicts=[
            EvalVerdict(
                name="stage_validity",
                score=1.0,
                passed=True,
                reasoning="All stages valid.",
                method="deterministic",
                confidence="high",
            )
        ],
        degraded=False,
        caveats=[],
        evaluated_at=datetime(2026, 6, 15, tzinfo=timezone.utc),
        judge_model=None,
    )


# ---------------------------------------------------------------------------
# B6 — route tests
# ---------------------------------------------------------------------------


def test_list_runs_includes_stored_run(fake_apollo_client, fake_exa_client, fake_claude_client):
    """GET /api/runs returns a run produced by the stream endpoint."""
    fc = _make_fake_clients(fake_apollo_client, fake_exa_client, fake_claude_client)

    with patch("app.runs.Clients", return_value=fc), TestClient(app) as client:
        stream_resp = client.post(
            "/api/runs/stream",
            json={"name": "Sam Altman", "company": "OpenAI"},
        )
        assert stream_resp.status_code == 200
        events = _parse_sse(stream_resp.content)
        run_id = events[0]["data"]["run_id"]

        runs_resp = client.get("/api/runs")

    assert runs_resp.status_code == 200
    run_ids = [r["id"] for r in runs_resp.json()["runs"]]
    assert run_id in run_ids


def test_run_evals_endpoint_delegates_to_run_all_evals(
    fake_apollo_client, fake_exa_client, fake_claude_client
):
    """POST /api/runs/{id}/evals calls run_all_evals and returns the updated run."""
    fc = _make_fake_clients(fake_apollo_client, fake_exa_client, fake_claude_client)
    report = _minimal_report()

    with patch("app.runs.Clients", return_value=fc), TestClient(app) as client:
        stream_resp = client.post(
            "/api/runs/stream",
            json={"name": "Sam Altman", "company": "OpenAI"},
        )
        events = _parse_sse(stream_resp.content)
        run_id = events[0]["data"]["run_id"]

        with (
            patch("app.clients.ClaudeClient"),
            patch("app.evals.base.run_all_evals", new=AsyncMock(return_value=report)) as mock_eval,
        ):
            resp = client.post(f"/api/runs/{run_id}/evals")

    assert resp.status_code == 200
    body = resp.json()
    assert body["run"]["id"] == run_id
    assert body["run"]["evals"] is not None
    mock_eval.assert_called_once()


def test_run_evals_endpoint_returns_404_for_unknown_run():
    """POST /api/runs/{id}/evals → 404 when run_id is not in the store."""
    with TestClient(app) as client:
        resp = client.post("/api/runs/nonexistent-run-id/evals")
    assert resp.status_code == 404


def test_stream_evaluate_flag_emits_evaluating_event(
    fake_apollo_client, fake_exa_client, fake_claude_client
):
    """?evaluate=true stream includes an evaluating event before run_completed."""
    fc = _make_fake_clients(fake_apollo_client, fake_exa_client, fake_claude_client)
    report = _minimal_report()

    with (
        patch("app.runs.Clients", return_value=fc),
        patch("app.evals.base.run_all_evals", new=AsyncMock(return_value=report)),
        TestClient(app) as client,
    ):
        resp = client.post(
            "/api/runs/stream?evaluate=true",
            json={"name": "Sam Altman", "company": "OpenAI"},
        )

    assert resp.status_code == 200
    events = _parse_sse(resp.content)
    event_names = [e["event"] for e in events]
    assert "evaluating" in event_names
    assert event_names[-1] == "run_completed"


# ---------------------------------------------------------------------------
# B7 — CancelledError cleanup
# ---------------------------------------------------------------------------


async def test_stream_cancelled_calls_aclose(
    fake_apollo_client, fake_exa_client, fake_claude_client
):
    """Closing the generator mid-stream ensures clients.aclose() is called via finally."""
    from app.runs import stream_form_pipeline

    mock_clients = MagicMock()
    mock_clients.aclose = AsyncMock()
    mock_clients.apollo = fake_apollo_client
    mock_clients.exa = fake_exa_client
    mock_clients.claude = fake_claude_client

    with patch("app.runs.Clients", return_value=mock_clients):
        gen = stream_form_pipeline(FormRequest(name="Sam Altman"))
        # First yield: run_started (before clients = Clients())
        await gen.__anext__()
        # Second yield: stage_started:ingest (after clients = Clients() is called)
        await gen.__anext__()
        # Simulate client disconnect by closing the generator
        await gen.aclose()

    mock_clients.aclose.assert_called_once()
