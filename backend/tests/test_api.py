"""The HTTP surface: stored runs, replay, the event stream, uniform errors and the guards."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import httpx
import pytest
from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute

from app import __version__
from app.errors import ModelRefused
from app.main import Prepared, create_app
from app.pipeline.runner import ModelCallRecord, RunState
from app.settings import Settings
from app.store import RunRow, Store
from tests.test_runner import FakeClient

KORVATH = "seed-korvath-greenhouses"
ORIGIN = "https://frontend.example.com"


def client_for(app: FastAPI, **headers: str) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver", headers=headers)


def events_of(body: str) -> list[dict[str, Any]]:
    return [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]


def types(events: list[dict[str, Any]]) -> list[str]:
    return [event["type"] for event in events]


@pytest.fixture
def app() -> FastAPI:
    return create_app(Settings())


@pytest.fixture
async def client(app: FastAPI) -> httpx.AsyncClient:
    return client_for(app)


def error_of(response: httpx.Response) -> dict[str, Any]:
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "retryable", "request_id"}
    error: dict[str, Any] = body["error"]
    return error


# ------------------------------------------------------------------ reading


async def test_health_reports_mode_version_and_that_the_store_answers(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "mode": "demo",
        "version": __version__,
        "store": True,
    }


async def test_config_says_what_the_page_needs_to_know(client: httpx.AsyncClient) -> None:
    config = (await client.get("/api/config")).json()

    assert (config["mode"], config["paste_enabled"]) == ("demo", False)
    assert [s["id"] for s in config["seeds"]] == [
        "korvath-greenhouses", "sallowfield-dental", "quillmoor-books",
    ]  # fmt: skip
    assert config["limits"] == {
        "min_turns": 6, "min_words": 120, "max_words": 12000,
        "runs_per_minute": 10, "daily_budget_usd": 2.0, "run_ceiling_seconds": 240.0,
    }  # fmt: skip


async def test_a_seeds_text_can_be_read(client: httpx.AsyncClient) -> None:
    seed = (await client.get("/api/seeds/quillmoor-books")).json()

    assert seed["title"] == "Quillmoor Books: interview with the founder"
    assert seed["text"].startswith("Ines Wetherby: Welcome back to the programme.")


async def test_the_three_seeded_runs_exist_from_the_start_under_stable_ids(
    client: httpx.AsyncClient,
) -> None:
    runs = (await client.get("/api/runs")).json()["runs"]

    assert [(r["id"], r["status"], r["pinned"], r["source"]) for r in runs] == [
        ("seed-korvath-greenhouses", "completed", True, "seed"),
        ("seed-sallowfield-dental", "completed", True, "seed"),
        ("seed-quillmoor-books", "completed", True, "seed"),
    ]


async def test_a_stored_run_shows_its_article_its_removals_and_its_trace(
    client: httpx.AsyncClient,
) -> None:
    detail = (await client.get(f"/api/runs/{KORVATH}")).json()

    assert detail["run"]["title"].startswith("Korvath Greenhouses")
    assert detail["article"]["headline"]["source"] == "model"
    assert len(detail["article"]["claims"]) == 19
    assert detail["article"]["removed"] == []
    assert len(detail["segments"]) == 100
    first = detail["article"]["claims"][0]
    assert detail["segments"][first["segment_indexes"][0]]["text"].startswith("For readers who")
    assert [(s["name"], s["status"]) for s in detail["stages"]] == [
        ("ingest", "completed"),
        ("extract", "completed"),
        ("draft", "completed"),
        ("ground", "completed"),
        ("evaluate", "completed"),
    ]
    assert all(
        s["input"] and s["output"] and s["duration_ms"] is not None for s in detail["stages"]
    )
    calls = detail["model_calls"]
    assert [(c["stage"], c["source"]) for c in calls] == [
        ("extract", "fixture"),
        ("draft", "fixture"),
        ("evaluate", "fixture"),
    ]
    assert calls[1]["request"]["system"].startswith("You write short news briefs")
    assert calls[1]["response"]["blocks"]
    assert calls[2]["model_requested"] == "claude-opus-5-5"
    assert detail["cost_usd"] == pytest.approx(sum(c["cost_usd"] for c in calls))


async def test_a_stored_run_shows_its_evaluation(client: httpx.AsyncClient) -> None:
    detail = (await client.get(f"/api/runs/{KORVATH}")).json()

    evaluation = detail["evaluation"]
    assert [(c["id"], c["passed"]) for c in evaluation["checks"]] == [
        ("E1", True),
        ("E2", True),
        ("E3", True),
    ]
    judged = evaluation["judge"]
    assert (judged["outcome"], judged["model"]) == ("judged", "claude-opus-5-5")
    # One verdict for each kept sentence and one for the model's headline. The score is the
    # share the judge found supported with each answer's question shown; the second score
    # is the share with the cited lines alone, which is lower on this recording.
    verdicts = judged["verdicts"]
    assert len(verdicts) == len(detail["article"]["claims"]) + 1
    assert judged["score"] == pytest.approx(sum(v["supported"] for v in verdicts) / len(verdicts))
    alone = sum(v["supported_alone"] for v in verdicts) / len(verdicts)
    assert judged["score_alone"] == pytest.approx(alone)
    assert judged["score_alone"] < judged["score"]
    assert all(v["supported"] or not v["supported_alone"] for v in verdicts)
    for verdict in judged["verdicts"]:
        if verdict["claim"] is not None:
            cited = detail["article"]["claims"][verdict["claim"]]["segment_indexes"]
            assert set(verdict["supporting_segments"]) <= set(cited)
    assert (evaluation["drafted"], evaluation["removed"], evaluation["removal_rate"]) == (19, 0, 0)


async def test_a_stored_claim_shows_the_question_its_cited_answer_replied_to(
    client: httpx.AsyncClient,
) -> None:
    # What the reader is shown is what the judge was shown: the same line, found by code.
    detail = (await client.get(f"/api/runs/{KORVATH}")).json()
    segments = detail["segments"]
    with_question = [c for c in detail["article"]["claims"] if c["question_segments"]]

    assert with_question
    for claim in with_question:
        for index in claim["question_segments"]:
            assert segments[index]["text"].endswith("?")
            assert index not in claim["segment_indexes"]
            assert index + 1 in claim["segment_indexes"]
    judge_call = detail["model_calls"][2]["request"]["content"][0]["text"]
    first = with_question[0]
    question = segments[first["question_segments"][0]]
    shown = f"[{question['index']}] {question['speaker']}: {question['text']}"
    assert f"<context>\n{shown}" in judge_call


async def test_a_run_that_failed_before_the_evaluation_has_none() -> None:
    refused = create_app(Settings(), model_client=FakeClient(extract=ModelRefused("unspecified")))
    async with client_for(refused) as client:
        started = await client.post("/api/runs/stream", json={"seed_id": "korvath-greenhouses"})
        run_id = events_of(started.text)[0]["run_id"]
        detail = (await client.get(f"/api/runs/{run_id}")).json()

    assert detail["run"]["status"] == "failed"
    assert detail["evaluation"] is None


# ------------------------------------------------------------------ starting a run


async def test_a_seeded_run_streams_to_run_completed_and_is_stored(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/api/runs/stream", json={"seed_id": "korvath-greenhouses"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event:" not in response.text
    events = events_of(response.text)
    assert types(events) == [
        "run_started",
        "stage_started", "stage_completed",
        "stage_started", "stage_completed",
        "stage_started", "stage_completed",
        "stage_started", "stage_completed",
        "stage_started", "stage_completed",
        "run_completed",
    ]  # fmt: skip
    run_id = events[0]["run_id"]
    assert run_id != KORVATH and all(e["run_id"] == run_id for e in events)

    stored = (await client.get(f"/api/runs/{run_id}")).json()
    assert (stored["run"]["status"], stored["run"]["seed_id"]) == (
        "completed",
        "korvath-greenhouses",
    )
    assert stored["run"]["pinned"] is False
    assert len(stored["article"]["claims"]) == 19
    listed = [r["id"] for r in (await client.get("/api/runs")).json()["runs"]]
    assert run_id in listed and len(listed) == 4


async def test_the_run_exists_before_its_first_event_so_a_reload_mid_run_finds_it(
    app: FastAPI,
) -> None:
    store: Store = app.state.store
    run = RunRow(
        id="mid-run",
        created_at=datetime.now(UTC),
        mode="demo",
        source="seed",
        title="t",
        status="running",
    )
    from app.seeds import seed

    chosen = seed("korvath-greenhouses")
    stream = app.state.stream_run(Prepared(run=run, text=chosen.text(), title=chosen.title))

    first = await anext(stream)
    assert first.root.type == "run_started"
    found = store.get_run("mid-run")
    assert found is not None and found.run.status == "running"

    async for event in stream:
        if event.root.type == "stage_completed" and event.root.stage == "extract":
            part_way = store.get_run("mid-run")
            assert part_way is not None
            assert [(s.name, s.status) for s in part_way.stages] == [
                ("ingest", "completed"), ("extract", "completed"),
            ]  # fmt: skip
    done = store.get_run("mid-run")
    assert done is not None and done.run.status == "completed"


async def test_a_stream_abandoned_mid_run_leaves_the_stored_run_failed_not_running(
    app: FastAPI,
) -> None:
    store: Store = app.state.store
    run = RunRow(
        id="gone",
        created_at=datetime.now(UTC),
        mode="demo",
        source="seed",
        title="t",
        status="running",
    )
    from app.seeds import seed

    chosen = seed("korvath-greenhouses")
    stream = app.state.stream_run(Prepared(run=run, text=chosen.text(), title=chosen.title))
    async for event in stream:
        if event.root.type == "stage_started" and event.root.stage == "extract":
            break
    await stream.aclose()

    stored = store.get_run("gone")
    assert stored is not None
    assert (stored.run.status, stored.run.error) == ("failed", "cancelled")
    assert not [s for s in stored.stages if s.status == "running"]


async def test_an_induced_stage_failure_still_ends_in_run_failed_and_is_stored() -> None:
    app = create_app(Settings(), model_client=FakeClient(draft=ModelRefused("cyber")))

    async with client_for(app) as client:
        response = await client.post("/api/runs/stream", json={"seed_id": "korvath-greenhouses"})
        events = events_of(response.text)
        stored = (await client.get(f"/api/runs/{events[0]['run_id']}")).json()

    assert response.status_code == 200
    assert types(events)[-1] == "run_failed"
    assert (events[-1]["error"], events[-1]["stage"]) == ("model_refused", "draft")
    assert sum(e["type"] in ("run_completed", "run_failed") for e in events) == 1
    assert (stored["run"]["status"], stored["run"]["error"]) == ("failed", "model_refused")
    assert stored["article"] is None
    assert [(s["name"], s["status"]) for s in stored["stages"]][-1] == ("draft", "failed")


async def test_a_billed_call_that_failed_is_stored_with_its_cost_and_no_response() -> None:
    app = create_app(Settings(), model_client=FakeClient(draft={"stop_reason": "max_tokens"}))

    async with client_for(app) as client:
        events = events_of(
            (await client.post("/api/runs/stream", json={"seed_id": "korvath-greenhouses"})).text
        )
        stored = (await client.get(f"/api/runs/{events[0]['run_id']}")).json()

    failed = stored["model_calls"][-1]
    assert (failed["stage"], failed["error"], failed["response"]) == (
        "draft",
        "model_truncated",
        None,
    )
    assert failed["cost_usd"] == pytest.approx(0.020662)


# ------------------------------------------------------------------ refusals before the stream


async def test_pasted_text_is_refused_in_demo_mode_and_nothing_is_started(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        "/api/runs/stream", json={"transcript": "Ann: Hello.", "title": "t"}
    )

    assert response.status_code == 403
    error = error_of(response)
    assert error["code"] == "paste_disabled_in_demo"
    assert "locally with your own key" in error["message"]
    assert len((await client.get("/api/runs")).json()["runs"]) == 3


async def test_pasted_text_runs_in_live_mode() -> None:
    app = create_app(Settings(mode="live"), model_client=FakeClient())
    transcript = (
        Path(__file__).parent / "fixtures/transcripts/01-korvath-greenhouses.txt"
    ).read_text()

    async with client_for(app) as client:
        response = await client.post(
            "/api/runs/stream", json={"transcript": transcript, "title": "A  pasted\ntitle"}
        )
        events = events_of(response.text)
        stored = (await client.get(f"/api/runs/{events[0]['run_id']}")).json()

    assert types(events)[-1] == "run_completed"
    assert (stored["run"]["source"], stored["run"]["title"]) == ("paste", "A pasted title")


async def test_a_pasted_transcript_that_is_too_short_is_refused_by_code_inside_the_stream() -> None:
    client_fake = FakeClient()
    app = create_app(Settings(mode="live"), model_client=client_fake)

    async with client_for(app) as client:
        response = await client.post("/api/runs/stream", json={"transcript": "Ann: Too short."})

    events = events_of(response.text)
    assert types(events) == ["run_started", "stage_started", "run_failed"]
    assert events[-1]["error"] == "transcript_too_short"
    assert client_fake.calls == []


@pytest.mark.parametrize(
    "body",
    [{}, {"seed_id": "korvath-greenhouses", "transcript": "Ann: Hello."}, {"seed_id": 7}, []],
)
async def test_a_malformed_start_request_is_refused_without_echoing_it(
    client: httpx.AsyncClient, body: Any
) -> None:
    response = await client.post("/api/runs/stream", json=body)

    assert response.status_code == 422
    assert error_of(response)["code"] == "invalid_request"
    assert "korvath" not in response.text and "Hello" not in response.text


async def test_an_unknown_seed_is_a_typed_404(client: httpx.AsyncClient) -> None:
    for response in (
        await client.post("/api/runs/stream", json={"seed_id": "no-such-seed"}),
        await client.get("/api/seeds/no-such-seed"),
    ):
        assert response.status_code == 404
        assert error_of(response)["code"] == "seed_not_found"


# ------------------------------------------------------------------ re-running from a stage


async def test_a_replay_from_draft_is_a_new_run_linked_to_its_parent(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(f"/api/runs/{KORVATH}/replay/stream", json={"from_stage": "draft"})

    events = events_of(response.text)
    assert types(events) == [
        "run_started",
        "stage_completed", "stage_completed",
        "stage_started", "stage_completed",
        "stage_started", "stage_completed",
        "stage_started", "stage_completed",
        "run_completed",
    ]  # fmt: skip
    assert [e.get("copied_from_run_id") for e in events[1:3]] == [KORVATH, KORVATH]
    run_id = events[0]["run_id"]
    stored = (await client.get(f"/api/runs/{run_id}")).json()
    run = stored["run"]
    assert (run["source"], run["parent_run_id"], run["replay_from_stage"]) == (
        "replay",
        KORVATH,
        "draft",
    )
    assert run["status"] == "completed"
    assert [(s["name"], s["copied_from_run_id"]) for s in stored["stages"]] == [
        ("ingest", KORVATH), ("extract", KORVATH), ("draft", None), ("ground", None),
        ("evaluate", None),
    ]  # fmt: skip
    assert [c["stage"] for c in stored["model_calls"]] == ["draft", "evaluate"]
    parent = (await client.get(f"/api/runs/{KORVATH}")).json()
    assert stored["article"] == parent["article"]
    assert parent["run"]["status"] == "completed"


async def test_a_replay_of_a_replay_can_be_replayed_again(client: httpx.AsyncClient) -> None:
    first = events_of(
        (
            await client.post(f"/api/runs/{KORVATH}/replay/stream", json={"from_stage": "ground"})
        ).text
    )
    second = events_of(
        (
            await client.post(
                f"/api/runs/{first[0]['run_id']}/replay/stream", json={"from_stage": "extract"}
            )
        ).text
    )

    assert types(first)[-1] == types(second)[-1] == "run_completed"
    stored = (await client.get(f"/api/runs/{second[0]['run_id']}")).json()
    assert stored["run"]["parent_run_id"] == first[0]["run_id"]


async def test_replaying_a_run_that_does_not_exist_is_a_typed_404(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/api/runs/nope/replay/stream", json={"from_stage": "draft"})

    assert response.status_code == 404
    assert error_of(response)["code"] == "run_not_found"


async def test_replaying_from_a_stage_that_does_not_exist_is_refused(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        f"/api/runs/{KORVATH}/replay/stream", json={"from_stage": "publish"}
    )

    assert response.status_code == 422
    assert error_of(response)["code"] == "invalid_request"
    assert "publish" not in response.text


async def test_replaying_a_failed_run_from_past_its_failure_ends_in_run_failed() -> None:
    app = create_app(Settings(), model_client=FakeClient(extract=ModelRefused("bio")))

    async with client_for(app) as client:
        failed = events_of(
            (await client.post("/api/runs/stream", json={"seed_id": "korvath-greenhouses"})).text
        )
        replay = events_of(
            (
                await client.post(
                    f"/api/runs/{failed[0]['run_id']}/replay/stream", json={"from_stage": "ground"}
                )
            ).text
        )

    assert replay[-1]["type"] == "run_failed"
    assert replay[-1]["error"] == "replay_not_possible"


# ------------------------------------------------------------------ the guards


def unguarded_post_routes(app: FastAPI) -> list[str]:
    """POST routes that do not depend on the run guard. Every POST route here starts a run."""
    guard = app.state.run_guard

    def depends_on_guard(dependant: Any) -> bool:
        return any(d.call is guard or depends_on_guard(d) for d in dependant.dependencies)

    return [
        route.path
        for route in app.routes
        if isinstance(route, APIRoute)
        and "POST" in (route.methods or set())
        and not depends_on_guard(route.dependant)
    ]


def test_every_route_that_can_start_a_run_depends_on_the_guard(app: FastAPI) -> None:
    posts = [
        r.path for r in app.routes if isinstance(r, APIRoute) and "POST" in (r.methods or set())
    ]

    assert posts == ["/api/runs/stream", "/api/runs/{run_id}/replay/stream"]
    assert unguarded_post_routes(app) == []


def test_the_check_above_fails_when_a_run_starting_route_lacks_the_guard(app: FastAPI) -> None:
    @app.post("/api/runs/unguarded")
    async def unguarded() -> dict[str, str]:
        return {}

    guard = app.state.run_guard

    def through_another_dependency(_guard: Annotated[None, Depends(guard)]) -> None:
        return None

    @app.post("/api/runs/guarded-indirectly")
    async def guarded(_: Annotated[None, Depends(through_another_dependency)]) -> dict[str, str]:
        return {}

    assert unguarded_post_routes(app) == ["/api/runs/unguarded"]


async def test_the_rate_limit_refuses_the_run_after_the_allowed_number_in_a_minute() -> None:
    app = create_app(Settings(runs_per_minute=2))

    async with client_for(app) as client:
        statuses = [
            (await client.post("/api/runs/stream", json={"seed_id": "quillmoor-books"})).status_code
            for _ in range(2)
        ]
        refused = await client.post("/api/runs/stream", json={"seed_id": "quillmoor-books"})
        replay = await client.post(
            f"/api/runs/{KORVATH}/replay/stream", json={"from_stage": "ground"}
        )
        reading = await client.get("/api/runs")

    assert statuses == [200, 200]
    assert refused.status_code == 429
    error = error_of(refused)
    assert (error["code"], error["retryable"]) == ("rate_limited", True)
    assert refused.headers["retry-after"] == "60"
    assert replay.status_code == 429
    assert reading.status_code == 200
    assert len(reading.json()["runs"]) == 5


async def test_the_rate_limit_is_per_address() -> None:
    app = create_app(Settings(runs_per_minute=1, trust_proxy=True))
    body = {"seed_id": "quillmoor-books"}

    async with client_for(app) as client:
        one = await client.post(
            "/api/runs/stream", json=body, headers={"x-real-ip": "198.51.100.7"}
        )
        again = await client.post(
            "/api/runs/stream", json=body, headers={"x-real-ip": "198.51.100.7"}
        )
        other = await client.post(
            "/api/runs/stream", json=body, headers={"x-real-ip": "198.51.100.8"}
        )

    assert (one.status_code, again.status_code, other.status_code) == (200, 429, 200)


async def test_a_forwarded_address_is_ignored_unless_the_proxy_is_trusted() -> None:
    app = create_app(Settings(runs_per_minute=1))
    body = {"seed_id": "quillmoor-books"}

    async with client_for(app) as client:
        await client.post("/api/runs/stream", json=body, headers={"x-real-ip": "198.51.100.7"})
        spoofed = await client.post(
            "/api/runs/stream", json=body, headers={"x-real-ip": "198.51.100.8"}
        )

    assert spoofed.status_code == 429


def record_live_cost(store: Store, cost: float) -> None:
    """Stores a finished run whose one model call was live and cost `cost`."""
    from tests.test_model_seam import a_request, a_response

    store.create_run(
        RunRow(
            id=f"live-{cost}",
            created_at=datetime.now(UTC),
            mode="live",
            source="paste",
            title="t",
            status="completed",
        )
    )
    response = a_response()
    call = ModelCallRecord(
        stage="draft", request_key="k", source="live", model_requested=response.model,
        model_served=response.model, stop_reason="end_turn", input_tokens=1, output_tokens=1,
        cost_usd=cost, latency_ms=1, attempts=1, request=a_request(), response=response,
    )  # fmt: skip
    state = RunState(run_id=f"live-{cost}", status="completed", model_calls=[call])
    store.save_state(state, datetime.now(UTC))


async def test_the_daily_budget_refuses_a_run_when_todays_recorded_cost_is_at_the_cap() -> None:
    app = create_app(Settings(daily_budget_usd=2.0))
    body = {"seed_id": "quillmoor-books"}

    async with client_for(app) as client:
        record_live_cost(app.state.store, 1.99)
        under = await client.post("/api/runs/stream", json=body)
        record_live_cost(app.state.store, 0.01)
        at_cap = await client.post("/api/runs/stream", json=body)
        replay = await client.post(
            f"/api/runs/{KORVATH}/replay/stream", json={"from_stage": "draft"}
        )

    assert under.status_code == 200
    assert at_cap.status_code == 429
    error = error_of(at_cap)
    assert (error["code"], error["retryable"]) == ("daily_budget_exhausted", False)
    assert replay.status_code == 429


async def test_replayed_recordings_cost_nothing_against_the_budget() -> None:
    app = create_app(Settings(daily_budget_usd=0.01))

    async with client_for(app) as client:
        statuses = [
            (
                await client.post("/api/runs/stream", json={"seed_id": "korvath-greenhouses"})
            ).status_code
            for _ in range(3)
        ]

    assert statuses == [200, 200, 200]


# ------------------------------------------------------------------ one shape for every error


async def test_an_unknown_path_and_a_wrong_method_get_the_same_error_shape(
    client: httpx.AsyncClient,
) -> None:
    missing = await client.get("/api/nothing-here")
    wrong = await client.delete("/api/runs")
    no_run = await client.get("/api/runs/nope")

    assert (missing.status_code, error_of(missing)["code"]) == (404, "not_found")
    assert (wrong.status_code, error_of(wrong)["code"]) == (405, "method_not_allowed")
    assert (no_run.status_code, error_of(no_run)["code"]) == (404, "run_not_found")


async def test_every_response_carries_a_request_id_and_an_error_repeats_it(
    client: httpx.AsyncClient,
) -> None:
    ok = await client.get("/health")
    bad = await client.get("/api/runs/nope")

    assert len(ok.headers["x-request-id"]) == 12
    assert error_of(bad)["request_id"] == bad.headers["x-request-id"]
    assert ok.headers["x-request-id"] != bad.headers["x-request-id"]


async def test_an_unexpected_failure_is_a_500_with_no_exception_text(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode() -> None:
        raise RuntimeError("secret detail about the database at /private/path")

    monkeypatch.setattr(app.state.store, "list_runs", explode)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/runs")

    assert response.status_code == 500
    assert error_of(response)["code"] == "internal_error"
    assert "secret detail" not in response.text and "/private/path" not in response.text


async def test_a_request_body_over_the_limit_is_refused_before_it_is_read() -> None:
    app = create_app(Settings(mode="live", max_body_bytes=2048), model_client=FakeClient())

    async with client_for(app) as client:
        response = await client.post(
            "/api/runs/stream", json={"transcript": "Ann: " + "word " * 2000}
        )

    assert response.status_code == 413
    assert error_of(response)["code"] == "request_too_large"


# ------------------------------------------------------------------ the schema and the origin


def test_the_event_union_is_one_named_schema_and_the_skeleton_is_gone(app: FastAPI) -> None:
    schema = app.openapi()

    assert schema["components"]["schemas"]["RunEvent"]["discriminator"]["propertyName"] == "type"
    assert not [path for path in schema["paths"] if path.startswith("/skeleton")]
    assert sorted(schema["paths"]) == [
        "/api/config", "/api/runs", "/api/runs/stream", "/api/runs/{run_id}",
        "/api/runs/{run_id}/replay/stream", "/api/seeds/{seed_id}", "/health",
    ]  # fmt: skip


@pytest.mark.parametrize(
    ("origin", "allowed"), [(ORIGIN, True), ("https://elsewhere.example.com", False)]
)
async def test_cors_allows_only_the_configured_origin(origin: str, allowed: bool) -> None:
    app = create_app(Settings(cors_origins=ORIGIN))

    async with client_for(app) as client:
        response = await client.get("/health", headers={"Origin": origin})

    assert response.status_code == 200
    assert (response.headers.get("access-control-allow-origin") == origin) is allowed


@pytest.mark.parametrize(
    "value",
    ["*", f"{ORIGIN},*", "https://*.example.com", f"{ORIGIN}/path", "frontend.example.com"],
)
def test_a_wildcard_or_malformed_cors_origin_is_refused(value: str) -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(cors_origins=value)


def test_the_committed_openapi_file_is_what_the_code_writes() -> None:
    # The frontend's types are generated from this file. If it is stale, so are they.
    from tools.write_openapi import OPENAPI_PATH, render

    assert OPENAPI_PATH.read_text() == render(), (
        "run: uv run --locked python -m tools.write_openapi"
    )


# ------------------------------------------------------------------ found by the reviewer


async def test_replaying_from_a_stage_that_does_not_exist_is_refused_before_the_stream(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    response = await client.post(
        f"/api/runs/{KORVATH}/replay/stream", json={"from_stage": "publish"}
    )

    assert response.status_code == 422
    assert error_of(response)["code"] == "invalid_request"
    # What a caller may ask for is exactly what the runner runs.
    from app.pipeline.runner import STAGE_NAMES

    stages = app.openapi()["components"]["schemas"]["ReplayRequest"]["properties"]["from_stage"]
    assert stages["enum"] == list(STAGE_NAMES)


async def test_a_replay_from_evaluate_copies_the_article_and_judges_it_again(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        f"/api/runs/{KORVATH}/replay/stream", json={"from_stage": "evaluate"}
    )

    events = events_of(response.text)
    assert types(events)[-1] == "run_completed"
    stored = (await client.get(f"/api/runs/{events[0]['run_id']}")).json()
    assert [s["copied_from_run_id"] for s in stored["stages"]] == [KORVATH] * 4 + [None]
    assert [c["stage"] for c in stored["model_calls"]] == ["evaluate"]
    parent = (await client.get(f"/api/runs/{KORVATH}")).json()
    assert stored["evaluation"] == parent["evaluation"]


@pytest.mark.parametrize("failing_call", [1, 2, 3, 6, 10])
async def test_a_store_failure_mid_stream_still_ends_the_stream_with_run_failed(
    failing_call: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_app(Settings())
    async with client_for(app) as client:
        await client.get("/api/runs")  # seed first, with the store working
        store: Store = app.state.store
        real, calls = store.save_state, 0

        def flaky(*args: Any, **kwargs: Any) -> None:
            nonlocal calls
            calls += 1
            if calls == failing_call:
                raise OSError("disk full at /private/path")
            real(*args, **kwargs)

        monkeypatch.setattr(store, "save_state", flaky)
        response = await client.post("/api/runs/stream", json={"seed_id": "quillmoor-books"})

    events = events_of(response.text)
    assert events[-1]["type"] == "run_failed"
    assert events[-1]["error"] == "internal_error"
    assert sum(e["type"] in ("run_completed", "run_failed") for e in events) == 1
    assert "disk full" not in response.text and "/private/path" not in response.text


async def test_requests_sent_at_once_cannot_get_past_the_rate_limit() -> None:
    import asyncio

    app = create_app(Settings(runs_per_minute=2))
    async with client_for(app) as client:
        await client.get("/api/runs")
        responses = await asyncio.gather(
            *[
                client.post("/api/runs/stream", json={"seed_id": "quillmoor-books"})
                for _ in range(10)
            ]
        )

    assert sorted(r.status_code for r in responses) == [200, 200] + [429] * 8


async def test_live_runs_in_flight_are_counted_against_the_budget_before_they_have_a_cost() -> None:
    # Two live runs started together would both read the same recorded cost. Each run that
    # is still going reserves a worst-case amount, so the second is refused.
    from app.store import WORST_RUN_USD

    budget = WORST_RUN_USD + 0.05  # room for one live run, not for two
    app = create_app(Settings(mode="live", daily_budget_usd=budget), model_client=FakeClient())
    store: Store = app.state.store
    store.create_run(
        RunRow(
            id="in-flight",
            created_at=datetime.now(UTC),
            mode="live",
            source="paste",
            title="t",
            status="running",
        )
    )

    async with client_for(app) as client:
        refused = await client.post("/api/runs/stream", json={"seed_id": "quillmoor-books"})

    assert refused.status_code == 429
    assert error_of(refused)["code"] == "daily_budget_exhausted"


async def test_a_chunked_body_with_no_declared_length_is_still_capped() -> None:
    app = create_app(Settings(mode="live", max_body_bytes=2048), model_client=FakeClient())

    async def chunks() -> Any:
        yield b'{"transcript": "'
        for _ in range(200):
            yield b"Ann: " + b"word " * 100
        yield b'"}'

    async with client_for(app) as client:
        response = await client.post(
            "/api/runs/stream", content=chunks(), headers={"content-type": "application/json"}
        )
        runs = (await client.get("/api/runs")).json()["runs"]

    assert response.status_code == 413
    assert error_of(response)["code"] == "request_too_large"
    assert len(runs) == 3


async def test_a_500_carries_the_request_id_header_too(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode() -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(app.state.store, "list_runs", explode)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/runs")

    assert response.status_code == 500
    assert response.headers["x-request-id"] == error_of(response)["request_id"]


async def test_in_demo_mode_a_run_made_from_pasted_text_cannot_be_replayed(tmp_path: Path) -> None:
    # Locally the demo and live modes can share one database file.
    path = tmp_path / "shared.sqlite3"
    transcript = (
        Path(__file__).parent / "fixtures/transcripts/01-korvath-greenhouses.txt"
    ).read_text()
    live = create_app(Settings(mode="live", database_path=path), model_client=FakeClient())
    async with client_for(live) as client:
        pasted = events_of(
            (await client.post("/api/runs/stream", json={"transcript": transcript})).text
        )

    demo = create_app(Settings(mode="demo", database_path=path))
    async with client_for(demo) as client:
        response = await client.post(
            f"/api/runs/{pasted[0]['run_id']}/replay/stream", json={"from_stage": "ground"}
        )

    assert response.status_code == 403
    assert error_of(response)["code"] == "paste_disabled_in_demo"


def test_the_routes_are_exactly_these_and_every_stream_is_guarded(app: FastAPI) -> None:
    # Any new route, or new method on an old one, changes this set and forces a decision
    # about the guard. Every route that opens an event stream starts a run.
    from fastapi.sse import EventSourceResponse

    routes = [r for r in app.routes if isinstance(r, APIRoute)]
    assert {(r.path, method) for r in routes for method in (r.methods or set())} == {
        ("/health", "GET"),
        ("/api/config", "GET"),
        ("/api/seeds/{seed_id}", "GET"),
        ("/api/runs", "GET"),
        ("/api/runs/{run_id}", "GET"),
        ("/api/runs/stream", "POST"),
        ("/api/runs/{run_id}/replay/stream", "POST"),
    }
    streams = [r.path for r in routes if r.response_class is EventSourceResponse]
    assert streams == ["/api/runs/stream", "/api/runs/{run_id}/replay/stream"]
    assert unguarded_post_routes(app) == []


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ({"x-real-ip": "198.51.100.7"}, "198.51.100.7"),
        # The left-most forwarded entry is whatever the caller sent. Only the right-most,
        # added by the proxy in front of the app, is trusted.
        ({"x-forwarded-for": "203.0.113.99, 198.51.100.7"}, "198.51.100.7"),
        ({"x-real-ip": "2001:db8:1:2:aaaa:bbbb:cccc:dddd"}, "2001:db8:1:2::/64"),
        ({"x-real-ip": "not an address"}, "testclient-fallback"),
    ],
)
def test_the_address_a_run_is_counted_against(headers: dict[str, str], expected: str) -> None:
    from app.main import client_address

    assert client_address(headers, "testclient-fallback", trust_proxy=True) == expected
    assert (
        client_address(headers, "testclient-fallback", trust_proxy=False) == "testclient-fallback"
    )


async def test_old_runs_are_pruned_but_seeded_runs_never_are() -> None:
    app = create_app(Settings(max_stored_runs=3, runs_per_minute=50))
    async with client_for(app) as client:
        ids = []
        for _ in range(5):
            events = events_of(
                (await client.post("/api/runs/stream", json={"seed_id": "quillmoor-books"})).text
            )
            ids.append(events[0]["run_id"])
        runs = (await client.get("/api/runs")).json()["runs"]
        oldest = await client.get(f"/api/runs/{ids[0]}")

    assert [r["id"] for r in runs if r["pinned"]] == [
        "seed-korvath-greenhouses", "seed-sallowfield-dental", "seed-quillmoor-books",
    ]  # fmt: skip
    assert sorted(r["id"] for r in runs if not r["pinned"]) == sorted(ids[-3:])
    assert oldest.status_code == 404
