"""A scripted model for the eval tests: an article written by hand, and a judge whose
answers the test chooses. Nothing here is a recording of a real model."""

from collections.abc import Callable
from typing import Any, Literal

from app.evals.cases import Case, load_cases
from app.model.types import ModelRequest, ModelResponse, Usage
from app.pipeline.config import JUDGE_MODEL
from app.pipeline.ingest import ingest
from app.schemas import Citation, DraftBlock, Segment

# A fair article on the Marrowbeck case, written by hand: each sentence with the segments
# it cites. It covers every key fact and both sides of the disagreement.
HEADLINE = "Farraday and Oxley disagree over the cancelled sailings"
PERFECT: list[tuple[str, list[int]]] = [
    ("Marrowbeck Ferries cancelled 14 sailings in October, Ione Farraday said.", [1, 10]),
    ("Farraday said weather was the main cause.", [22]),
    (
        "Bram Oxley said his log shows weather closed the harbour on two days, "
        "which accounts for 5 of the 14 sailings.",
        [15, 16],
    ),
    ("Oxley said crew was the main cause.", [24]),
    ("Farraday said the Eilean's master was off sick for part of the month.", [20]),
    ("Farraday said 312 passengers were refunded in October.", [29]),
    ("A second master for the Eilean starts on the first of December, Farraday said.", [32, 33]),
    ("Oxley said a wind gauge is going on the outer wall.", [37]),
]


def case(case_id: str = "marrowbeck-ferries") -> Case:
    return next(c for c in load_cases() if c.id == case_id)


def segments_of(case_id: str = "marrowbeck-ferries") -> list[Segment]:
    chosen = case(case_id)
    return ingest(chosen.text(), chosen.title).segments


def draft_blocks(
    sentences: list[tuple[str, list[int]]], segments: list[Segment], headline: str = HEADLINE
) -> list[DraftBlock]:
    blocks = [DraftBlock(text=f"{headline}\n\n")]
    for text, cited in sentences:
        citations = [
            Citation(start_segment=i, end_segment=i + 1, cited_text=segments[i].text) for i in cited
        ]
        blocks.append(DraftBlock(text=f"{text} ", citations=citations))
    return blocks


def agree(number: int, sentence: str, cited: list[int]) -> dict[str, Any]:
    """A judge that finds every sentence supported by the first line it cites."""
    return {
        "item": number,
        "supported": True,
        "supported_without_context": True,
        "supporting": cited[:1],
        "reason": "Stated.",
    }


Answer = Callable[[int, str, list[int]], dict[str, Any]]


def judge_items(request: ModelRequest) -> list[tuple[str, list[int]]]:
    """Reads the sentences and cited indexes back out of a judge request."""
    import re

    (part,) = request.content
    text = getattr(part, "text", "")
    found = []
    for body in re.findall(r"<item number=\"\d+\">(.*?)</item>", text, re.S):
        sentence = re.search(r"<sentence>(.*?)</sentence>", body, re.S)
        assert sentence is not None
        lines = re.search(r"<cited>(.*?)</cited>", body, re.S)
        assert lines is not None
        cited = [int(i) for i in re.findall(r"^\[(\d+)\]", lines.group(1), re.M)]
        found.append((sentence.group(1), cited))
    return found


class ScriptedClient:
    """Answers the three kinds of request the pipeline makes. `judge` chooses each verdict;
    `fail` raises instead, for one kind of request."""

    source: Literal["fixture"] = "fixture"

    def __init__(
        self,
        blocks: list[DraftBlock],
        *,
        judge: Answer = agree,
        extract: dict[str, Any] | None = None,
        fail: dict[str, BaseException] | None = None,
    ) -> None:
        self.blocks = blocks
        self.judge = judge
        self.extract = extract or {
            "points": [{"text": "Fourteen sailings were cancelled.", "segments": [10]}],
            "corrections": [],
            "disagreements": [],
            "angle": "The cancellations.",
        }
        self.fail = fail or {}
        self.judge_requests: list[ModelRequest] = []

    def _response(
        self, request: ModelRequest, blocks: list[DraftBlock], parsed: dict[str, Any] | None
    ) -> ModelResponse:
        return ModelResponse(
            blocks=blocks,
            parsed=parsed,
            stop_reason="end_turn",
            model=request.model,
            usage=Usage(input_tokens=10, output_tokens=10),
            cost_usd=0.001,
            latency_ms=1,
        )

    async def complete(self, request: ModelRequest) -> ModelResponse:
        if request.model == JUDGE_MODEL:
            kind = "judge"
        else:
            kind = "extract" if request.output_schema else "draft"
        if kind in self.fail:
            raise self.fail[kind]
        if kind == "extract":
            return self._response(request, [], self.extract)
        if kind == "draft":
            return self._response(request, self.blocks, None)
        self.judge_requests.append(request)
        return judge_response(request, self.judge)


def judge_response(request: ModelRequest, answer: Answer = agree) -> ModelResponse:
    """A judge's answer to a judge request, one verdict per item, chosen by `answer`."""
    verdicts = [
        answer(number, sentence, cited)
        for number, (sentence, cited) in enumerate(judge_items(request))
    ]
    return ModelResponse(
        blocks=[],
        parsed={"verdicts": verdicts},
        stop_reason="end_turn",
        model=request.model,
        usage=Usage(input_tokens=10, output_tokens=10),
        cost_usd=0.001,
        latency_ms=1,
    )
