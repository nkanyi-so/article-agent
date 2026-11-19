"""The three seeded transcripts run end to end from recordings: no key, no network."""

from pathlib import Path
from typing import Literal

import pytest

from app.evals import thresholds
from app.evals.cases import EVALS_DIR, recordings_dir
from app.evals.harness import run_set
from app.model.fixture import RECORDINGS_DIR, FixtureModelClient
from app.model.payload import request_key
from app.model.types import ModelRequest, ModelResponse
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
    assert [(call.stage, call.source) for call in state.model_calls] == [
        ("extract", "fixture"),
        ("draft", "fixture"),
        ("evaluate", "fixture"),
    ]
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
    "korvath-greenhouses": (19, 0),
    "sallowfield-dental": (17, 1),
    "quillmoor-books": (16, 0),
}


@pytest.mark.parametrize("seed", SEEDS, ids=SEED_IDS)
async def test_a_seeds_recording_keeps_and_removes_what_it_did_when_recorded(seed: Seed) -> None:
    state = await run_seed(seed)
    assert state.result is not None

    assert (len(state.result.claims), len(state.result.removed)) == RECORDED[seed.id]


class Noting:
    """The fixture client, noting the key of every request it is asked for."""

    source: Literal["fixture"] = "fixture"

    def __init__(self, folder: Path) -> None:
        self.asked: set[str] = set()
        self.inner = FixtureModelClient(folder)

    async def complete(self, request: ModelRequest) -> ModelResponse:
        self.asked.add(request_key(request))
        return await self.inner.complete(request)


async def test_every_recording_is_one_the_eval_set_asks_for() -> None:
    # A recording nothing asks for is dead weight, and usually a prompt that was edited
    # without re-recording. The eval set includes the three seeds, and its first pass
    # replays the folder that demo mode and the tests replay.
    clients: dict[int, Noting] = {}

    def client_for(repeat: int) -> Noting:
        return clients.setdefault(repeat, Noting(recordings_dir(repeat)))

    await run_set(client_for, repeats=thresholds.REPEATS)

    assert sorted(clients) == [1, 2, 3]
    assert recordings_dir(1) == RECORDINGS_DIR
    for repeat, client in clients.items():
        assert {path.stem for path in recordings_dir(repeat).glob("*.json")} == client.asked


def test_no_recording_contains_a_key_or_an_authorisation_header() -> None:
    folders = [RECORDINGS_DIR, EVALS_DIR / "recordings"]
    for path in (p for folder in folders for p in folder.rglob("*.json")):
        text = path.read_text().lower()
        assert "sk-ant" not in text
        assert "x-api-key" not in text
        assert "authorization" not in text
