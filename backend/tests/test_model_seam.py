"""The model seam: one interface, a request key, a fixture client that fails loudly,
and the conversion of a raw API response, including the three ways a response is unusable."""

import ast
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from app.errors import (
    FixtureMiss,
    ModelMismatch,
    ModelOutputInvalid,
    ModelRefused,
    ModelTruncated,
)
from app.main import create_app
from app.model.convert import response_from_api
from app.model.fixture import (
    RECORDINGS_DIR,
    FixtureModelClient,
    load_recording,
    save_recording,
)
from app.model.payload import api_request, request_key
from app.model.pricing import cost_usd
from app.model.types import DocumentPart, ModelRequest, TextPart
from app.settings import Settings

FIXTURES = Path(__file__).parent / "fixtures"
APP = Path(__file__).parents[1] / "app"


def a_request(**changes: Any) -> ModelRequest:
    base: dict[str, Any] = {
        "model": "claude-sonnet-5-5",
        "system": "Write a brief.",
        "content": [
            DocumentPart(title="A title", blocks=["Ann: One.", "Bob: Two."]),
            TextPart(text="Write it."),
        ],
        "max_tokens": 16000,
        "effort": "medium",
    }
    return ModelRequest(**(base | changes))


def raw_draft() -> dict[str, Any]:
    saved = json.loads((FIXTURES / "draft" / "t1-sentence-sonnet-medium-a.json").read_text())
    response: dict[str, Any] = saved["response"]
    return response


def a_response() -> Any:
    return response_from_api(raw_draft(), a_request(), latency_ms=6770, attempts=1)


# ------------------------------------------------------------------ the request key


def test_the_same_request_always_has_the_same_key() -> None:
    assert request_key(a_request()) == request_key(a_request())
    assert len(request_key(a_request())) == 64


@pytest.mark.parametrize(
    "changes",
    [
        {"system": "Write a brief!"},
        {"model": "claude-opus-5-5"},
        {"effort": "low"},
        {"max_tokens": 8000},
        {"output_schema": {"type": "object"}},
        {"content": [DocumentPart(title="A title", blocks=["Ann: One.", "Bob: Too."])]},
        {"content": [DocumentPart(title="Another title", blocks=["Ann: One.", "Bob: Two."])]},
    ],
)
def test_any_change_to_the_request_changes_the_key(changes: dict[str, Any]) -> None:
    assert request_key(a_request(**changes)) != request_key(a_request())


# ------------------------------------------------------------------ the fixture client


async def test_the_fixture_client_replays_a_recording_of_the_exact_request(tmp_path: Path) -> None:
    save_recording(tmp_path, a_request(), a_response(), raw_draft())

    replayed = await FixtureModelClient(tmp_path).complete(a_request())

    assert replayed == a_response()
    assert replayed.blocks[1].citations[0].start_segment == 15


async def test_a_request_with_one_word_changed_is_a_loud_miss(tmp_path: Path) -> None:
    save_recording(tmp_path, a_request(), a_response(), raw_draft())

    with pytest.raises(FixtureMiss) as miss:
        await FixtureModelClient(tmp_path).complete(a_request(system="Write a short brief."))

    assert miss.value.code == "fixture_miss"
    assert request_key(a_request(system="Write a short brief."))[:12] in miss.value.detail


def test_a_recording_file_is_named_by_its_request_key_and_holds_the_raw_response(
    tmp_path: Path,
) -> None:
    path = save_recording(tmp_path, a_request(), a_response(), raw_draft())

    assert path.name == f"{request_key(a_request())}.json"
    recording = load_recording(path)
    assert recording.request == a_request()
    assert recording.raw_response["usage"]["input_tokens"] == 4886


def test_a_recording_whose_request_does_not_match_its_file_name_is_refused(tmp_path: Path) -> None:
    path = save_recording(tmp_path, a_request(), a_response(), raw_draft())
    tampered = json.loads(path.read_text())
    tampered["request"]["system"] = "Something else."
    path.write_text(json.dumps(tampered))

    with pytest.raises(FixtureMiss):
        load_recording(path)


# ------------------------------------------------------------------ converting a raw response


def test_a_real_draft_response_becomes_blocks_with_citations_usage_and_cost() -> None:
    response = a_response()

    assert response.stop_reason == "end_turn"
    assert response.model == "claude-sonnet-5-5"
    assert response.blocks[1].text.startswith("Korvath Greenhouses began an irrigation pilot")
    assert response.blocks[1].citations[0].end_segment == 17
    assert (response.usage.input_tokens, response.usage.output_tokens) == (4886, 1089)
    assert response.cost_usd == pytest.approx(0.020662)
    assert response.latency_ms == 6770
    assert response.parsed is None


def test_thinking_blocks_are_counted_but_are_not_part_of_the_draft() -> None:
    saved = json.loads((FIXTURES / "draft" / "t1-sentence-opus-medium.json").read_text())
    request = a_request(model="claude-opus-5-5")

    response = response_from_api(saved["response"], request, latency_ms=1, attempts=1)

    assert response.usage.thinking_tokens == 481
    assert all(block.text for block in response.blocks)


def test_a_structured_response_is_parsed() -> None:
    saved = json.loads((FIXTURES / "extract" / "t2-sonnet-low.json").read_text())
    request = a_request(output_schema={"type": "object"})

    response = response_from_api(saved["response"], request, latency_ms=1, attempts=1)

    assert response.parsed is not None
    assert response.parsed["corrections"] == [{"superseded": 4, "replaced_by": 16}]


def test_a_refusal_is_a_typed_error_and_carries_only_the_category() -> None:
    raw = raw_draft() | {
        "stop_reason": "refusal",
        "stop_details": {"type": "refusal", "category": "cyber", "explanation": "upstream text"},
        "content": [],
    }

    with pytest.raises(ModelRefused) as refused:
        response_from_api(raw, a_request(), latency_ms=1, attempts=1)

    assert refused.value.code == "model_refused"
    assert refused.value.detail == "cyber"
    assert "upstream text" not in str(refused.value)


def test_a_response_cut_off_at_max_tokens_is_a_typed_error() -> None:
    with pytest.raises(ModelTruncated) as truncated:
        response_from_api(raw_draft() | {"stop_reason": "max_tokens"}, a_request(), 1, 1)

    assert truncated.value.code == "model_truncated"


def test_a_response_from_another_model_is_a_typed_error() -> None:
    with pytest.raises(ModelMismatch) as mismatch:
        response_from_api(raw_draft() | {"model": "claude-sonnet-5"}, a_request(), 1, 1)

    assert mismatch.value.code == "model_mismatch"
    assert mismatch.value.detail == "claude-sonnet-5"


def test_structured_output_that_is_not_json_is_a_typed_error() -> None:
    raw = raw_draft() | {"content": [{"type": "text", "text": "not json at all"}]}

    with pytest.raises(ModelOutputInvalid):
        response_from_api(raw, a_request(output_schema={"type": "object"}), 1, 1)


def test_cost_is_computed_from_usage_and_the_price_table() -> None:
    assert cost_usd("claude-sonnet-5-5", 1_000_000, 1_000_000) == pytest.approx(12.0)
    assert cost_usd("claude-opus-5-5", 1_000_000, 1_000_000) == pytest.approx(24.0)
    with pytest.raises(KeyError):
        cost_usd("a-model-with-no-price", 1, 1)


# ------------------------------------------------------------------ where the SDK may live


def imports_of(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            found |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    return found


def test_only_the_live_client_module_imports_the_sdk() -> None:
    importers = [
        p.relative_to(APP).as_posix() for p in APP.rglob("*.py") if "anthropic" in imports_of(p)
    ]

    assert importers == ["model/live.py"]


def test_no_module_of_the_app_imports_the_live_client_at_module_level() -> None:
    for path in APP.rglob("*.py"):
        tree = ast.parse(path.read_text())
        top_level = [n for n in tree.body if isinstance(n, ast.Import | ast.ImportFrom)]
        names = {getattr(n, "module", None) for n in top_level} | {
            alias.name for n in top_level if isinstance(n, ast.Import) for alias in n.names
        }
        assert "app.model.live" not in names, path


def test_demo_mode_builds_the_fixture_client_and_never_loads_the_live_one() -> None:
    sys.modules.pop("app.model.live", None)

    app = create_app(Settings(mode="demo"))

    assert isinstance(app.state.model_client, FixtureModelClient)
    assert "app.model.live" not in sys.modules
    assert "anthropic" not in sys.modules


# ------------------------------------------------------------------ what is sent


def test_the_document_goes_as_citable_blocks_and_nothing_sets_sampling() -> None:
    sent = api_request(a_request())

    document, text = sent["messages"][0]["content"]
    assert document["citations"] == {"enabled": True}
    assert [b["text"] for b in document["source"]["content"]] == ["Ann: One.", "Bob: Two."]
    assert text == {"type": "text", "text": "Write it."}
    assert sent["output_config"] == {"effort": "medium"}
    assert not {"temperature", "top_p", "top_k", "fallbacks"} & set(sent)


def test_a_schema_is_sent_as_the_output_format() -> None:
    sent = api_request(a_request(output_schema={"type": "object"}, content=[TextPart(text="x")]))

    assert sent["output_config"]["format"] == {"type": "json_schema", "schema": {"type": "object"}}


def test_live_mode_without_a_key_fails_at_start_with_a_typed_error() -> None:
    pytest.importorskip("anthropic")  # only where the live group is installed
    from app.errors import MissingKey

    with pytest.raises(MissingKey):
        create_app(Settings(mode="live", anthropic_api_key=None))


# ------------------------------------------------------------------ found in review


@pytest.mark.parametrize("stop_reason", [None, "pause_turn", "tool_use", "something_new"])
def test_a_stop_reason_that_is_not_a_normal_end_is_a_typed_error(stop_reason: str | None) -> None:
    with pytest.raises(ModelOutputInvalid):
        response_from_api(raw_draft() | {"stop_reason": stop_reason}, a_request(), 1, 1)


@pytest.mark.parametrize(
    "broken",
    [
        {"usage": None},
        {"usage": {"input_tokens": None, "output_tokens": 5}},
        {"content": [{"type": "text"}]},
        {
            "content": [
                {"type": "text", "text": "x", "citations": [{"type": "content_block_location"}]}
            ]
        },
        {"content": "not a list"},
    ],
)
def test_a_malformed_response_is_a_typed_error_not_a_crash(broken: dict[str, Any]) -> None:
    with pytest.raises(ModelOutputInvalid):
        response_from_api(raw_draft() | broken, a_request(), 1, 1)


@pytest.mark.parametrize(
    "changes",
    [{"stop_reason": "max_tokens"}, {"model": "claude-sonnet-5"}, {"stop_reason": "refusal"}],
)
def test_a_typed_model_error_carries_what_the_call_cost(changes: dict[str, Any]) -> None:
    # The call was billed even though its response cannot be used.
    with pytest.raises(Exception) as failure:
        response_from_api(raw_draft() | changes, a_request(), 1, 1)

    assert failure.value.cost_usd == pytest.approx(0.020662)  # type: ignore[attr-defined]


def test_the_key_covers_what_is_actually_sent_not_only_the_request_model() -> None:
    # If the way a request is turned into API arguments changes, old recordings must miss.
    import hashlib
    import json

    sent = api_request(a_request())
    canonical = json.dumps(sent, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    assert request_key(a_request()) == hashlib.sha256(canonical.encode()).hexdigest()
    assert sent["thinking"] == {"type": "adaptive"}


def test_every_recording_stores_the_response_its_raw_response_converts_to() -> None:
    paths = sorted(RECORDINGS_DIR.glob("*.json"))
    assert paths
    for path in paths:
        recording = load_recording(path)
        again = response_from_api(
            recording.raw_response,
            recording.request,
            latency_ms=recording.response.latency_ms,
            attempts=recording.response.attempts,
            request_id=recording.response.request_id,
        )
        assert again == recording.response, path.name


NETWORK_MODULES = {
    "anthropic",
    "httpx",
    "httpx2",
    "requests",
    "urllib",
    "urllib3",
    "aiohttp",
    "socket",
}


def test_only_the_live_client_module_can_reach_the_network() -> None:
    reachers = {
        p.relative_to(APP).as_posix(): sorted(imports_of(p) & NETWORK_MODULES)
        for p in APP.rglob("*.py")
        if imports_of(p) & NETWORK_MODULES
    }

    assert reachers == {"model/live.py": ["anthropic"]}
