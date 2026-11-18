"""The three seeded transcripts run end to end from recordings: no key, no network."""

import pytest

from app.model.fixture import RECORDINGS_DIR, FixtureModelClient, load_recording
from app.model.payload import request_key
from app.pipeline.draft import build_draft_request
from app.pipeline.extract import build_extract_request, parse_extract
from app.pipeline.ingest import ingest
from app.pipeline.runner import RunState, run_pipeline
from app.seeds import SEEDS, Seed

SEED_IDS = [seed.id for seed in SEEDS]


async def run_seed(seed: Seed) -> RunState:
    state = RunState(run_id=f"test-{seed.id}")
    async for _ in run_pipeline(seed.text(), seed.title, FixtureModelClient(), state):
        pass
    return state


@pytest.mark.parametrize("seed", SEEDS, ids=SEED_IDS)
async def test_a_seed_runs_end_to_end_from_its_recordings(seed: Seed) -> None:
    state = await run_seed(seed)

    assert (state.status, state.error) == ("completed", None)
    assert [call.source for call in state.model_calls] == ["fixture", "fixture"]
    assert state.result is not None
    assert len(state.result.claims) >= 3


@pytest.mark.parametrize("seed", SEEDS, ids=SEED_IDS)
async def test_a_seeds_article_keeps_its_lead_and_its_own_headline(seed: Seed) -> None:
    # What the Phase 4 prompt change was for: on the recorded runs the first sentence of the
    # body survives the ground check and the model's headline is accepted.
    state = await run_seed(seed)
    assert state.result is not None
    result = state.result

    assert result.headline.source == "model"
    assert result.headline.supporting_claims
    lead = result.claims[0]
    assert lead.paragraph == 0
    assert not [unit for unit in result.removed if unit.paragraph == 0]
    company = seed.title.split(":")[0].split()[0]
    assert company in lead.text


# What each recording shows: sentences kept and removed. A snapshot of fixed files, not a
# threshold for the model. Each seed was recorded once and the run was not chosen; when a
# prompt change forces a new recording these numbers are replaced with what it shows.
RECORDED = {
    "korvath-greenhouses": (20, 2),
    "sallowfield-dental": (17, 2),
    "quillmoor-books": (14, 0),
}


@pytest.mark.parametrize("seed", SEEDS, ids=SEED_IDS)
async def test_a_seeds_recording_keeps_and_removes_what_it_did_when_recorded(seed: Seed) -> None:
    state = await run_seed(seed)
    assert state.result is not None

    assert (len(state.result.claims), len(state.result.removed)) == RECORDED[seed.id]


def test_every_recording_is_one_the_pipeline_asks_for() -> None:
    # A recording nothing asks for is dead weight, and usually a prompt that was edited
    # without re-recording.
    wanted: set[str] = set()
    for seed in SEEDS:
        ingested = ingest(seed.text(), seed.title)
        extract_request = build_extract_request(ingested)
        wanted.add(request_key(extract_request))
        response = load_recording(RECORDINGS_DIR / f"{request_key(extract_request)}.json").response
        extract = parse_extract(response, len(ingested.segments))
        wanted.add(request_key(build_draft_request(ingested, extract)))

    assert {path.stem for path in RECORDINGS_DIR.glob("*.json")} == wanted


def test_no_recording_contains_a_key_or_an_authorisation_header() -> None:
    for path in RECORDINGS_DIR.glob("*.json"):
        text = path.read_text().lower()
        assert "sk-ant" not in text
        assert "x-api-key" not in text
        assert "authorization" not in text
