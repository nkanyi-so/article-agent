"""The eval set: what is run, and what a person wrote down that each case must show."""

import json
from pathlib import Path

from pydantic import BaseModel

from app.evals.checks import Side
from app.pipeline.ground import questions_answered
from app.pipeline.ingest import ingest
from app.schemas import Segment

EVALS_DIR = Path(__file__).resolve().parents[2] / "evals"


def recordings_dir(repeat: int) -> Path:
    """Where the recordings of the nth pass over the eval set live. The first pass is the
    one demo mode and the tests replay; the others exist only for the evals."""
    from app.model.fixture import RECORDINGS_DIR

    return RECORDINGS_DIR if repeat == 1 else EVALS_DIR / "recordings" / f"run-{repeat}"


class SideSpec(BaseModel):
    label: str
    segments: list[int]
    mentions: str

    def side(self) -> Side:
        return Side(self.label, tuple(self.segments), self.mentions)


class Case(BaseModel):
    id: str
    title: str
    file: str
    repeat: int = 1
    tags: list[str]
    seen_by_prompt: bool
    expect_error: str | None = None
    expect_model_calls: int | None = None
    key_facts: list[list[int]] = []
    canary: str | None = None
    stale: list[str] = []
    unless: list[str] = []
    sides: list[SideSpec] = []

    def text(self) -> str:
        return (EVALS_DIR / self.file).read_text() * self.repeat


class Pair(BaseModel):
    """A sentence, the lines it cites, and the answer a person gave."""

    id: str
    kind: str
    case: str
    segments: list[int]
    sentence: str
    supported: bool
    supported_alone: bool


def load_cases() -> list[Case]:
    raw = json.loads((EVALS_DIR / "cases.json").read_text())
    return [Case.model_validate(case) for case in raw["cases"]]


def load_pairs() -> list[Pair]:
    raw = json.loads((EVALS_DIR / "calibration.json").read_text())
    return [Pair.model_validate(pair) for pair in raw["pairs"]]


def lines_of(pair: Pair, cases: list[Case]) -> tuple[tuple[Segment, ...], tuple[Segment, ...]]:
    """A pair's cited lines, and the questions they answer, found as the ground stage finds them."""
    case = next(case for case in cases if case.id == pair.case)
    segments = ingest(case.text(), case.title).segments
    asked = questions_answered(pair.segments, segments)
    return tuple(segments[i] for i in pair.segments), tuple(segments[i] for i in asked)
