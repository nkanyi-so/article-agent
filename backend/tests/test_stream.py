"""Tests for the SSE streaming pipeline endpoint.

Uses the same fake client fixtures as test_pipeline_e2e.py — zero API calls.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.clients import ApolloClient, ExaClient
from app.errors import UpstreamError
from app.main import app
from app.schemas import FormRequest


# ---------------------------------------------------------------------------
# SSE parsing helper
# ---------------------------------------------------------------------------


def _parse_sse(raw: bytes) -> list[dict]:
    """Parse an SSE stream into a list of {event, data} dicts."""
    events = []
    for block in raw.decode().split("\n\n"):
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        event_name = ""
        data_str = ""
        for line in lines:
            if line.startswith("event:"):
                event_name = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                data_str = line.removeprefix("data:").strip()
        if event_name:
            payload = json.loads(data_str) if data_str else {}
            events.append({"event": event_name, "data": payload})
    return events


def _make_fake_clients(apollo, exa, claude):
    class _FakeClients:
        def __init__(self):
            self.apollo = apollo
            self.exa = exa
            self.claude = claude

        async def aclose(self):
            pass

    return _FakeClients()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_stream_completed_run(fake_apollo_client, fake_exa_client, fake_claude_client):
    """Happy path: completed run emits all four stages + run_completed terminal."""
    fc = _make_fake_clients(fake_apollo_client, fake_exa_client, fake_claude_client)

    with patch("app.runs.Clients", return_value=fc), TestClient(app) as client:
        resp = client.post(
            "/api/runs/stream",
            json={"name": "Sam Altman", "company": "OpenAI"},
        )

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = _parse_sse(resp.content)
    event_names = [e["event"] for e in events]

    # Must start with run_started
    assert event_names[0] == "run_started"
    assert events[0]["data"]["run_id"]

    # stage_started / stage_completed pairs for each of the four stages
    for stage in ("ingest", "enrich", "research", "draft"):
        assert f"stage_started" in event_names
        assert f"stage_completed" in event_names

    # Terminal event must be run_completed
    assert event_names[-1] == "run_completed"
    run = events[-1]["data"]["run"]
    assert run["status"] == "completed"
    assert run["article"] is not None

    # stage_started and stage_completed must alternate for each stage
    stage_started = [e["data"]["name"] for e in events if e["event"] == "stage_started"]
    stage_completed = [e["data"]["stage"]["name"] for e in events if e["event"] == "stage_completed"]
    assert stage_started == ["ingest", "enrich", "research", "draft"]
    assert stage_completed == ["ingest", "enrich", "research", "draft"]


def test_stream_needs_disambiguation(fake_exa_client, fake_claude_client):
    """Ambiguous Apollo match → needs_disambiguation terminal, no article."""
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

    with patch("app.runs.Clients", return_value=fc), TestClient(app) as client:
        resp = client.post("/api/runs/stream", json={"name": "Sam A"})

    events = _parse_sse(resp.content)
    terminal = events[-1]
    assert terminal["event"] == "needs_disambiguation"
    assert len(terminal["data"]["candidates"]) == 2
    assert terminal["data"]["run_id"]


def test_stream_failed_run(fake_apollo_client, fake_claude_client):
    """Empty Exa results → run_failed terminal with error info."""
    empty_exa = MagicMock(spec=ExaClient)
    empty_exa.search_news = AsyncMock(return_value=[])

    fc = _make_fake_clients(fake_apollo_client, empty_exa, fake_claude_client)

    with patch("app.runs.Clients", return_value=fc), TestClient(app) as client:
        resp = client.post("/api/runs/stream", json={"name": "NoNews Person"})

    events = _parse_sse(resp.content)
    terminal = events[-1]
    assert terminal["event"] == "run_failed"
    run = terminal["data"]["run"]
    assert run["status"] == "failed"
    assert run["error"]["code"] == "exa_empty"


def test_stream_apollo_degraded_still_completes(
    fake_apollo_client_degraded, fake_exa_client, fake_claude_client
):
    """Apollo 403 (free plan) degrades gracefully — pipeline still completes."""
    fc = _make_fake_clients(fake_apollo_client_degraded, fake_exa_client, fake_claude_client)

    with patch("app.runs.Clients", return_value=fc), TestClient(app) as client:
        resp = client.post(
            "/api/runs/stream",
            json={"name": "Sam Altman", "company": "OpenAI"},
        )

    events = _parse_sse(resp.content)
    terminal = events[-1]
    assert terminal["event"] == "run_completed"
    assert terminal["data"]["run"]["status"] == "completed"


def test_stream_run_started_event_shape(fake_apollo_client, fake_exa_client, fake_claude_client):
    """run_started event includes run_id, created_at, and the original input."""
    fc = _make_fake_clients(fake_apollo_client, fake_exa_client, fake_claude_client)

    with patch("app.runs.Clients", return_value=fc), TestClient(app) as client:
        resp = client.post(
            "/api/runs/stream",
            json={"name": "Sam Altman", "company": "OpenAI"},
        )

    events = _parse_sse(resp.content)
    started = events[0]
    assert started["event"] == "run_started"
    data = started["data"]
    assert data["run_id"]
    assert data["created_at"]
    assert data["input"]["name"] == "Sam Altman"
    assert data["input"]["company"] == "OpenAI"


def test_stream_stage_completed_shape(fake_apollo_client, fake_exa_client, fake_claude_client):
    """stage_completed events contain the full StageOutput envelope."""
    fc = _make_fake_clients(fake_apollo_client, fake_exa_client, fake_claude_client)

    with patch("app.runs.Clients", return_value=fc), TestClient(app) as client:
        resp = client.post(
            "/api/runs/stream",
            json={"name": "Sam Altman", "company": "OpenAI"},
        )

    events = _parse_sse(resp.content)
    completed = [e for e in events if e["event"] == "stage_completed"]
    assert len(completed) == 4

    for ev in completed:
        stage = ev["data"]["stage"]
        assert "name" in stage
        assert "status" in stage
        assert "duration_ms" in stage
        assert stage["status"] in ("ok", "error")


def test_stream_invalid_body_returns_422():
    """Missing name + linkedin_url should return 422 (FastAPI validation), not 500."""
    with TestClient(app) as client:
        resp = client.post("/api/runs/stream", json={"company": "OpenAI"})
    assert resp.status_code == 422
