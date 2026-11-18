"""The seeded transcripts: fictional people at fictional companies, shipped with the app."""

from dataclasses import dataclass
from pathlib import Path

SEEDS_DIR = Path(__file__).resolve().parents[1] / "seeds"


@dataclass(frozen=True)
class Seed:
    id: str
    title: str

    def text(self) -> str:
        return (SEEDS_DIR / f"{self.id}.txt").read_text()


SEEDS: tuple[Seed, ...] = (
    Seed("korvath-greenhouses", "Korvath Greenhouses: interview on the irrigation project"),
    Seed("sallowfield-dental", "Sallowfield Dental Group: monthly operations meeting"),
    Seed("quillmoor-books", "Quillmoor Books: interview with the founder"),
)


def seed(seed_id: str) -> Seed:
    for candidate in SEEDS:
        if candidate.id == seed_id:
            return candidate
    raise KeyError(seed_id)
