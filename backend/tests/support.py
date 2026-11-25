"""Loads the recorded responses in `tests/fixtures/` into the shapes the stages take."""

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.pipeline.ingest import ingest
from app.schemas import Citation, Correction, DraftBlock, Segment

FIXTURES = Path(__file__).parent / "fixtures"

TRANSCRIPTS = {
    "t1": (
        "01-korvath-greenhouses.txt",
        "Korvath Greenhouses: interview on the irrigation project",
    ),
    "t2": (
        "02-hartwell-lane-correction.txt",
        "Hartwell Lane Bakery Supply: third-quarter operations review",
    ),
}

DRAFTS = sorted(path.stem for path in (FIXTURES / "draft").glob("*.json"))


@dataclass
class Recorded:
    """One recorded draft, with everything the ground stage needs to check it."""

    name: str
    title: str
    segments: list[Segment]
    corrections: list[Correction]
    content: list[dict[str, Any]]  # the raw response blocks, free to alter in a test

    def blocks(self) -> list[DraftBlock]:
        return blocks_from_content(self.content)

    def find(self, text: str) -> dict[str, Any]:
        """The one raw text block containing `text`."""
        (block,) = [b for b in self.content if b["type"] == "text" and text in b["text"]]
        return block


def blocks_from_content(content: list[dict[str, Any]]) -> list[DraftBlock]:
    """Text blocks only: a thinking block is not part of the draft."""
    return [
        DraftBlock(
            text=block["text"],
            citations=[
                Citation(
                    start_segment=c["start_block_index"],
                    end_segment=c["end_block_index"],
                    cited_text=c["cited_text"],
                )
                for c in block.get("citations") or []
            ],
        )
        for block in content
        if block["type"] == "text"
    ]


def recorded(name: str) -> Recorded:
    saved = json.loads((FIXTURES / "draft" / f"{name}.json").read_text())
    key = name[:2]
    filename, title = TRANSCRIPTS[key]
    segments = ingest((FIXTURES / "transcripts" / filename).read_text(), title).segments
    extract = json.loads((FIXTURES / "extract" / f"{key}-sonnet-low.json").read_text())
    (text_block,) = [b for b in extract["response"]["content"] if b["type"] == "text"]
    corrections = [Correction(**c) for c in json.loads(text_block["text"])["corrections"]]
    return Recorded(name, title, segments, corrections, copy.deepcopy(saved["response"]["content"]))


def recorded_sallowfield() -> Recorded:
    """One saved run of the draft prompt trial on the Sallowfield seed, with the prompt
    whose examples come from no transcript. It has a sentence that uses two surnames where
    the cited text has only first names."""
    from app.seeds import seed

    chosen = seed("sallowfield-dental")
    saved = json.loads((FIXTURES / "sallowfield" / "draft-sallowfield-neutral-1.json").read_text())
    extract = json.loads((FIXTURES / "sallowfield" / "extract-sallowfield.json").read_text())
    segments = ingest(chosen.text(), chosen.title).segments
    corrections = [Correction(**c) for c in extract["response"]["parsed"]["corrections"]]
    return Recorded(
        "sallowfield-neutral-1",
        chosen.title,
        segments,
        corrections,
        copy.deepcopy(saved["raw"]["content"]),
    )
