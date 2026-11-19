"""The seeded transcripts: fictional people at fictional companies, shipped with the app."""

from dataclasses import dataclass
from pathlib import Path

SEEDS_DIR = Path(__file__).resolve().parents[1] / "seeds"
ALTERED_SEED = "korvath-altered"


@dataclass(frozen=True)
class Seed:
    id: str
    title: str
    # The transcript file, when it is another seed's. And a note shown beside the seed.
    transcript: str | None = None
    note: str | None = None

    def text(self) -> str:
        return (SEEDS_DIR / f"{self.transcript or self.id}.txt").read_text()


SEEDS: tuple[Seed, ...] = (
    Seed("korvath-greenhouses", "Korvath Greenhouses: interview on the irrigation project"),
    Seed("sallowfield-dental", "Sallowfield Dental Group: monthly operations meeting"),
    Seed("quillmoor-books", "Quillmoor Books: interview with the founder"),
    # Not a model's draft as it came. The Korvath draft with two changes made by hand, so
    # that a visitor can watch the ground check remove something false: see
    # `tools/make_altered_seed.py`, which made its recordings and says what it changed.
    Seed(
        ALTERED_SEED,
        "Korvath Greenhouses: the same interview, with the draft altered by hand",
        transcript="korvath-greenhouses",
        note=(
            "Altered on purpose. We changed one figure in the model's draft (11 percent "
            "became 17) and removed one sentence's citation, to show the code removing both."
        ),
    ),
)


def seed(seed_id: str) -> Seed:
    for candidate in SEEDS:
        if candidate.id == seed_id:
            return candidate
    raise KeyError(seed_id)
