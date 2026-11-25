"""The runner: stage order, records, and the guarantee that every run ends in a terminal state."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Literal

import pytest

from app.errors import ModelRefused
from app.events import TERMINAL, AnyRunEvent, RunCompleted, RunFailed
from app.model.convert import response_from_api
from app.model.types import ModelRequest, ModelResponse
from app.pipeline.config import JUDGE_MODEL
from app.pipeline.runner import RunState, run_pipeline
from tests.evalkit import judge_response

FIXTURES = Path(__file__).parent / "fixtures"
TRANSCRIPT = (FIXTURES / "transcripts" / "01-korvath-greenhouses.txt").read_text()
TITLE = "Korvath Greenhouses: interview on the irrigation project"


def saved(kind: str, name: str) -> dict[str, Any]:
    response: dict[str, Any] = json.loads((FIXTURES / kind / f"{name}.json").read_text())[
        "response"
    ]
    return response


class FakeClient:
    """Answers an extract request and a draft request with real recorded responses, and a
    judge request with "supported" for every sentence."""

    source: Literal["fixture"] = "fixture"

    def __init__(self, **overrides: Any) -> None:
        self.calls: list[ModelRequest] = []
        self.overrides = overrides

    async def complete(self, request: ModelRequest) -> ModelResponse:
        self.calls.append(request)
        if request.model == JUDGE_MODEL:
            behaviour = self.overrides.get("judge")
            if isinstance(behaviour, BaseException):
                raise behaviour
            if behaviour == "hang":
                await asyncio.sleep(60)
            return judge_response(request)
        kind = "extract" if request.output_schema else "draft"
        behaviour = self.overrides.get(kind)
        if isinstance(behaviour, BaseException):
            raise behaviour
        if behaviour == "hang":
            await asyncio.sleep(60)
        raw = (
            saved("extract", "t1-sonnet-low")
            if kind == "extract"
            else saved("draft", "t1-sentence-sonnet-medium-a")
        )
        if isinstance(behaviour, dict):
            raw = raw | behaviour
        return response_from_api(raw, request, latency_ms=5, attempts=1)


async def collect(
    client: FakeClient, text: str = TRANSCRIPT, **kwargs: Any
) -> tuple[list[AnyRunEvent], RunState]:
    state = RunState(run_id="run-1")
    events = [event async for event in run_pipeline(text, TITLE, client, state, **kwargs)]
    return events, state


def types(events: list[AnyRunEvent]) -> list[str]:
    return [event.type for event in events]


# ------------------------------------------------------------------ the happy path


async def test_a_run_goes_through_the_five_stages_in_order_and_completes() -> None:
    events, state = await collect(FakeClient())

    assert types(events) == [
        "run_started",
        "stage_started", "stage_completed",
        "stage_started", "stage_completed",
        "stage_started", "stage_completed",
        "stage_started", "stage_completed",
        "stage_started", "stage_completed",
        "run_completed",
    ]  # fmt: skip
    stages = [e.stage for e in events if e.type == "stage_started"]
    assert stages == ["ingest", "extract", "draft", "ground", "evaluate"]
    assert [event.seq for event in events] == list(range(12))
    assert state.status == "completed"
    assert state.result is not None and len(state.result.claims) >= 3


async def test_every_stage_stores_its_input_and_its_output() -> None:
    _, state = await collect(FakeClient())

    assert [(r.name, r.status) for r in state.stages] == [
        ("ingest", "completed"), ("extract", "completed"), ("draft", "completed"), ("ground", "completed"), ("evaluate", "completed"),  # noqa: E501
    ]  # fmt: skip
    ingest_record, extract_record, draft_record, ground_record, evaluate_record = state.stages
    assert evaluate_record.input == {"claims": len(ground_record.output["claims"])}  # type: ignore[index]
    assert evaluate_record.output["judge"]["outcome"] == "judged"  # type: ignore[index]
    assert ingest_record.input == {"title": TITLE, "transcript": TRANSCRIPT}
    assert len(ingest_record.output["segments"]) == 100  # type: ignore[index]
    assert extract_record.output["angle"]  # type: ignore[index]
    first_block = draft_record.output["blocks"][0]["text"]  # type: ignore[index]
    assert first_block.startswith("Korvath Greenhouses cuts")
    assert ground_record.output["removed"]  # type: ignore[index]
    assert all(r.duration_ms is not None and r.error is None for r in state.stages)


async def test_every_model_call_is_recorded_with_its_request_response_and_cost() -> None:
    client = FakeClient()

    _, state = await collect(client)

    assert [call.stage for call in state.model_calls] == ["extract", "draft", "evaluate"]
    assert state.model_calls[2].model_requested == "claude-opus-5-5"
    draft_call = state.model_calls[1]
    assert draft_call.request == client.calls[1]
    assert draft_call.source == "fixture"
    assert draft_call.model_requested == draft_call.model_served == "claude-sonnet-5-5"
    assert (draft_call.input_tokens, draft_call.output_tokens) == (4886, 1089)
    assert state.cost_usd() == pytest.approx(0.017312 + 0.020662 + 0.001)


async def test_the_draft_request_is_built_from_the_extract_output() -> None:
    client = FakeClient()

    await collect(client)

    draft_text = client.calls[1].content[-1].text  # type: ignore[union-attr]
    assert "Lead: " in draft_text


# ------------------------------------------------------------------ every way it can fail


async def test_a_refused_transcript_fails_the_run_before_any_model_call() -> None:
    client = FakeClient()

    events, state = await collect(client, text="Ann: Too short.")

    assert types(events) == ["run_started", "stage_started", "run_failed"]
    failed = events[-1]
    assert isinstance(failed, RunFailed)
    assert (failed.error, failed.stage) == ("transcript_too_short", "ingest")
    assert client.calls == []
    assert (state.status, state.error) == ("failed", "transcript_too_short")
    assert state.stages[0].status == "failed"


async def test_a_model_refusal_fails_the_run_at_that_stage_and_later_stages_never_start() -> None:
    events, state = await collect(FakeClient(extract=ModelRefused("cyber")))

    assert types(events)[-1] == "run_failed"
    assert events[-1].error == "model_refused"  # type: ignore[union-attr]
    assert [r.name for r in state.stages] == ["ingest", "extract"]
    assert state.stages[-1].error == "model_refused"


async def test_a_response_from_another_model_fails_the_run() -> None:
    events, _ = await collect(FakeClient(draft={"model": "claude-sonnet-5"}))

    assert events[-1].error == "model_mismatch"  # type: ignore[union-attr]


async def test_a_truncated_response_fails_the_run() -> None:
    events, _ = await collect(FakeClient(draft={"stop_reason": "max_tokens"}))

    assert events[-1].error == "model_truncated"  # type: ignore[union-attr]


async def test_nothing_checkable_is_refused_after_exactly_one_model_call() -> None:
    nothing = {"content": [{"type": "text", "text": json.dumps(
        {"points": [], "corrections": [], "disagreements": [], "angle": "Nothing to report."}
    )}]}  # fmt: skip
    client = FakeClient(extract=nothing)

    events, _ = await collect(client)

    assert events[-1].error == "no_checkable_facts"  # type: ignore[union-attr]
    assert len(client.calls) == 1


async def test_an_unexpected_exception_ends_in_run_failed_without_its_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.ERROR):
        events, state = await collect(FakeClient(draft=RuntimeError("secret upstream detail")))

    failed = events[-1]
    assert isinstance(failed, RunFailed)
    assert failed.error == "internal_error"
    assert "secret upstream detail" not in failed.model_dump_json()
    assert "secret upstream detail" not in state.model_dump_json()
    assert "secret upstream detail" in caplog.text


async def test_too_few_grounded_claims_fails_the_run_and_keeps_what_was_removed() -> None:
    uncited = {"content": [{"type": "text", "text": "A headline\n\nOne. Two. Three. Four."}]}

    events, state = await collect(FakeClient(draft=uncited))

    assert events[-1].error == "too_few_grounded_claims"  # type: ignore[union-attr]
    ground_record = state.stages[-1]
    assert (ground_record.name, ground_record.status) == ("ground", "failed")
    assert len(ground_record.output["removed"]) == 4  # type: ignore[index]


async def test_a_run_that_passes_its_ceiling_fails_with_a_timeout() -> None:
    events, state = await collect(FakeClient(extract="hang"), ceiling_s=0.05)

    assert events[-1].error == "run_timeout"  # type: ignore[union-attr]
    assert state.stages[-1].status == "failed"


@pytest.mark.parametrize(
    "client",
    [
        FakeClient(),
        FakeClient(extract=ModelRefused("bio")),
        FakeClient(draft=RuntimeError("boom")),
        FakeClient(draft={"stop_reason": "max_tokens"}),
        FakeClient(extract={"content": [{"type": "text", "text": "not json"}]}),
    ],
)
async def test_every_stream_ends_with_exactly_one_terminal_event(client: FakeClient) -> None:
    events, state = await collect(client)

    assert isinstance(events[-1], TERMINAL)
    assert sum(isinstance(event, TERMINAL) for event in events) == 1
    assert state.status == ("completed" if isinstance(events[-1], RunCompleted) else "failed")
    assert not [r for r in state.stages if r.status == "running"]


async def test_a_consumer_that_goes_away_leaves_the_run_closed_as_failed_not_running() -> None:
    state = RunState(run_id="run-2")
    stream = run_pipeline(TRANSCRIPT, TITLE, FakeClient(extract="hang"), state)

    async for event in stream:
        if event.type == "stage_started" and event.stage == "extract":
            break
    await stream.aclose()  # type: ignore[attr-defined]

    assert (state.status, state.error) == ("failed", "cancelled")
    assert state.stages[-1].status == "failed"


# ------------------------------------------------------------------ found in review


class SlowClient(FakeClient):
    """Each call takes 0.04 seconds, so two calls pass a 0.06 second ceiling between them."""

    async def complete(self, request: ModelRequest) -> ModelResponse:
        await asyncio.sleep(0.04)
        return await super().complete(request)


async def test_the_ceiling_is_on_the_whole_run_not_on_each_stage() -> None:
    events, state = await collect(SlowClient(), ceiling_s=0.06)

    failed = events[-1]
    assert isinstance(failed, RunFailed)
    assert (failed.error, failed.stage) == ("run_timeout", "draft")
    assert [r.name for r in state.stages][:2] == ["ingest", "extract"]


async def test_a_run_whose_time_is_already_up_does_not_start_a_stage() -> None:
    # Nothing in fixture mode awaits, so a deadline that only fires at an await never would.
    events, state = await collect(FakeClient(), ceiling_s=0)

    assert types(events) == ["run_started", "run_failed"]
    assert events[-1].error == "run_timeout"  # type: ignore[union-attr]
    assert state.stages == []


async def test_a_billed_call_whose_response_is_unusable_is_still_counted_in_the_runs_cost() -> None:
    _, state = await collect(FakeClient(draft={"stop_reason": "max_tokens"}))

    assert [call.stage for call in state.model_calls] == ["extract"]
    (failed,) = state.failed_calls
    assert (failed.stage, failed.error) == ("draft", "model_truncated")
    assert failed.cost_usd == pytest.approx(0.020662)
    assert state.cost_usd() == pytest.approx(0.017312 + 0.020662)


# ------------------------------------------------------------------ re-running from a stage


async def replay(
    from_stage: str, client: FakeClient, parent: RunState
) -> tuple[list[AnyRunEvent], RunState]:
    from app.pipeline.runner import Resume

    state = RunState(run_id="run-replay")
    resume = Resume(from_stage=from_stage, parent_run_id=parent.run_id, parent_stages=parent.stages)  # type: ignore[arg-type]
    events = [e async for e in run_pipeline(TRANSCRIPT, TITLE, client, state, resume=resume)]
    return events, state


async def test_a_replay_from_draft_copies_the_earlier_stages_and_runs_the_rest_again() -> None:
    _, parent = await collect(FakeClient())
    client = FakeClient()

    events, state = await replay("draft", client, parent)

    assert types(events) == [
        "run_started",
        "stage_completed", "stage_completed",
        "stage_started", "stage_completed",
        "stage_started", "stage_completed",
        "stage_started", "stage_completed",
        "run_completed",
    ]  # fmt: skip
    copied = [e for e in events if e.type == "stage_completed" and e.copied_from_run_id]
    assert [e.stage for e in copied] == ["ingest", "extract"]
    assert [(r.name, r.copied_from_run_id) for r in state.stages] == [
        ("ingest", "run-1"), ("extract", "run-1"), ("draft", None), ("ground", None), ("evaluate", None),  # noqa: E501
    ]  # fmt: skip
    assert state.stages[1].output == parent.stages[1].output
    # The draft was asked of the writer again, and the new article of the judge. Not the extract.
    assert [r.model for r in client.calls] == ["claude-sonnet-5-5", "claude-opus-5-5"]
    assert client.calls[0].output_schema is None
    assert state.status == "completed" and state.result is not None


async def test_a_replay_from_ground_calls_only_the_judge() -> None:
    _, parent = await collect(FakeClient())
    client = FakeClient()

    _, state = await replay("ground", client, parent)

    assert [r.model for r in client.calls] == ["claude-opus-5-5"]
    assert state.result == parent.result
    assert [r.copied_from_run_id for r in state.stages] == ["run-1", "run-1", "run-1", None, None]


async def test_a_replay_from_evaluate_copies_the_article_and_judges_it_again() -> None:
    _, parent = await collect(FakeClient())
    client = FakeClient()

    _, state = await replay("evaluate", client, parent)

    assert [r.model for r in client.calls] == ["claude-opus-5-5"]
    assert state.status == "completed" and state.result == parent.result
    assert [r.copied_from_run_id for r in state.stages] == ["run-1"] * 4 + [None]
    assert state.stages[4].output == parent.stages[4].output


async def test_a_judge_that_cannot_be_used_does_not_fail_the_run() -> None:
    # The article was written and checked. A judge that refuses or times out is recorded on
    # the evaluation, with what it cost, and the run completes.
    refusal = ModelRefused("unspecified")
    refusal.cost_usd = 0.03

    events, state = await collect(FakeClient(judge=refusal))

    assert types(events)[-1] == "run_completed"
    assert state.stages[4].output["judge"] == {  # type: ignore[index]
        "outcome": "failed", "error": "model_refused", "model": "claude-opus-5-5",
        "verdicts": [], "score": None, "score_alone": None,
    }  # fmt: skip
    assert [(c.stage, c.error, c.cost_usd) for c in state.failed_calls] == [
        ("evaluate", "model_refused", 0.03)
    ]


async def test_a_replay_re_executes_from_the_stored_input_not_from_memory() -> None:
    # The parent's stored extract output is edited; the replayed draft must be built from it.
    _, parent = await collect(FakeClient())
    assert parent.stages[1].output is not None
    parent.stages[1].output["angle"] = "An angle edited in the stored record."
    client = FakeClient()

    await replay("draft", client, parent)

    assert "An angle edited in the stored record." in client.calls[0].content[-1].text  # type: ignore[union-attr]


async def test_a_replay_of_a_run_that_never_reached_the_stage_fails_cleanly() -> None:
    _, parent = await collect(FakeClient(extract=ModelRefused("bio")))

    events, state = await replay("draft", FakeClient(), parent)

    assert types(events) == ["run_started", "stage_completed", "run_failed"]
    assert events[-1].error == "replay_not_possible"  # type: ignore[union-attr]
    assert state.status == "failed"
