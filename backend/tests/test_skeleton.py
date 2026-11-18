"""The Phase 2 walking skeleton: a dummy event stream and a runtime report.

These routes exist to prove the host. They are replaced by the real run routes in Phase 5.
"""

import json
import logging

import httpx
import pytest
from pydantic import ValidationError

from app.main import create_app
from app.settings import Settings
from app.skeleton import RunCompleted, RunFailed, skeleton_events


async def no_sleep(_: float) -> None:
    return None


def client_for(settings: Settings) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=create_app(settings))
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


def data_lines(body: str) -> list[dict[str, object]]:
    return [
        json.loads(line[len("data: ") :]) for line in body.splitlines() if line.startswith("data: ")
    ]


async def test_the_stream_emits_five_events_then_a_terminal_one() -> None:
    events = [event async for event in skeleton_events(delay_s=0, sleep=no_sleep)]

    assert [event.type for event in events] == [
        "run_started",
        "stage_started",
        "stage_completed",
        "stage_started",
        "stage_completed",
        "run_completed",
    ]
    assert isinstance(events[-1], RunCompleted)
    assert [event.seq for event in events] == [0, 1, 2, 3, 4, 5]


async def test_a_failure_part_way_still_ends_with_a_terminal_event(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def sleep_that_breaks(_: float) -> None:
        raise RuntimeError("upstream detail that must not reach a client")

    with caplog.at_level(logging.ERROR):
        events = [event async for event in skeleton_events(delay_s=1, sleep=sleep_that_breaks)]

    assert isinstance(events[-1], RunFailed)
    assert events[-1].error == "internal_error"
    assert "upstream detail" not in events[-1].model_dump_json()
    # The reason is kept, on the server side only.
    assert "upstream detail" in caplog.text


async def test_the_route_sends_data_only_events_with_the_tag_in_the_body() -> None:
    async with client_for(Settings(skeleton_routes=True, skeleton_delay_s=0)) as client:
        response = await client.get("/skeleton/stream")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event:" not in response.text
    events = data_lines(response.text)
    assert events[0]["type"] == "run_started"
    assert events[-1]["type"] == "run_completed"
    assert len(events) == 6


async def test_the_event_union_is_one_named_schema() -> None:
    schema = create_app(Settings(skeleton_routes=True)).openapi()

    assert "SkeletonEvent" in schema["components"]["schemas"]
    assert (
        schema["components"]["schemas"]["SkeletonEvent"]["discriminator"]["propertyName"] == "type"
    )


async def test_the_runtime_report_reads_back_a_scratch_database() -> None:
    async with client_for(Settings(skeleton_routes=True)) as client:
        report = (await client.get("/skeleton/runtime")).json()

    assert report["scratch_sqlite"] == {"ok": True, "rows_read": 1}
    assert isinstance(report["anthropic_installed"], bool)
    assert "fastapi" in {d["name"].lower() for d in report["distributions"]}
    assert report["uptime_s"] >= 0


@pytest.mark.parametrize(
    ("origin", "allowed"),
    [("https://frontend.example.com", True), ("https://elsewhere.example.com", False)],
)
async def test_cors_allows_only_the_configured_origin(origin: str, allowed: bool) -> None:
    settings = Settings(cors_origins="https://frontend.example.com")
    async with client_for(settings) as client:
        response = await client.get("/health", headers={"Origin": origin})

    assert response.status_code == 200
    assert (response.headers.get("access-control-allow-origin") == origin) is allowed


async def test_the_skeleton_routes_are_off_unless_switched_on() -> None:
    app = create_app(Settings())

    assert not [path for path in app.openapi()["paths"] if path.startswith("/skeleton")]
    async with client_for(Settings()) as client:
        assert (await client.get("/skeleton/runtime")).status_code == 404


@pytest.mark.parametrize(
    "value",
    [
        "*",
        "https://ok.example.com,*",
        "https://*.example.com",
        "https://ok.example.com/path",
        "ok.example.com",
    ],
)
def test_a_wildcard_or_malformed_cors_origin_is_refused(value: str) -> None:
    with pytest.raises(ValidationError):
        Settings(cors_origins=value)


def test_several_explicit_origins_are_accepted() -> None:
    settings = Settings(cors_origins="https://a.example.com, http://localhost:3000")

    assert settings.cors_origin_list() == ["https://a.example.com", "http://localhost:3000"]
