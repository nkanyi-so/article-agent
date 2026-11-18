"""Ingest: parse a transcript into numbered sentence segments, or refuse it.

Pure code. No model, no network, no clock.
"""

import re
from dataclasses import dataclass

from app.errors import (
    TranscriptEmpty,
    TranscriptTooLong,
    TranscriptTooShort,
    TranscriptUnparseable,
)
from app.schemas import IngestResult, Segment

MIN_TURNS = 6
MIN_WORDS = 120
MAX_WORDS = 12_000
MAX_TITLE_CHARS = 200

# An optional timestamp, a speaker label of one to four words, an optional role or timestamp
# in brackets, a colon, then the speech. Each word of the label must start with a capital
# letter or a digit (checked in code, so accented capitals count); that keeps "The short
# version is this: we wait." from being read as a turn by a speaker of that name.
_TIMESTAMP = r"(?:[\[(]?\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?[\])]?\s+)?"
_LABEL_WORD = r"\w[\w.'’-]*"  # noqa: RUF001 (curly quotes are what this matches)
_BRACKETED = r"(?:\s*[\[(][^\])\n]{1,30}[\])])?"
_TURN = re.compile(
    rf"^{_TIMESTAMP}(?P<speaker>{_LABEL_WORD}(?: {_LABEL_WORD}){{0,3}}){_BRACKETED}"
    r":\s+(?P<text>\S.*)$"
)

# A title is always followed by a name, so its full stop never ends a sentence.
_TITLES = {"mr", "mrs", "ms", "dr", "prof", "st"}
# Other abbreviations. In prose their full stop does end a sentence when a capital follows.
_ABBREVIATIONS = {"vs", "etc", "inc", "ltd", "co", "approx", "e.g", "i.e"}
_TERMINATORS = ".?!"
_OPEN_QUOTE, _CLOSE_QUOTE = "“", "”"
_CLOSERS = '"”’)]'  # noqa: RUF001 (curly quotes are what this matches)
_WORD_BEFORE = re.compile(r"[A-Za-z][A-Za-z.]*$")
# How far around a full stop to look when deciding whether it ends a sentence. Bounded,
# so splitting stays linear in the length of the text.
_LOOK = 24


@dataclass(frozen=True)
class Turn:
    speaker: str
    text: str
    line: int


def _is_label(speaker: str) -> bool:
    return all(word[0].isupper() or word[0].isdigit() for word in speaker.split())


def parse_turns(text: str) -> list[Turn]:
    """Reads `Speaker: text` lines. A line with no speaker continues the turn before it."""
    turns: list[Turn] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        match = _TURN.match(line)
        if match and _is_label(match["speaker"]):
            turns.append(Turn(match["speaker"], match["text"].strip(), line_no))
        elif turns:
            last = turns[-1]
            turns[-1] = Turn(last.speaker, f"{last.text} {line}", last.line)
    return turns


def _is_abbreviation(text: str, stop: int, after: int, prose: bool) -> bool:
    """Whether the full stop at `stop` belongs to an abbreviation rather than ending a sentence.

    In prose the doubt goes to ending the sentence: a sentence wrongly cut in two has to
    earn its place twice, while two sentences wrongly joined let one ride on the other.
    """
    before = _WORD_BEFORE.search(text[max(0, stop - _LOOK) : stop])
    if not before:
        return False
    word = before.group()
    rest = text[after : after + _LOOK].lstrip()
    if not rest:
        return False
    if word.lower() in _TITLES:
        return True
    if word.lower() in _ABBREVIATIONS:
        return not (prose and rest[0].isupper())
    if word.lower() == "no":
        # "No. 5" is a number; "No. Nobody was laid off." is an answer.
        return rest[0].isdigit()
    # A single capital is an initial ("J. Tennant"), except the pronoun. Not in prose,
    # where "plan A. The sensors..." must stay two sentences.
    return not prose and len(word) == 1 and word.isupper() and word != "I"


def _quotes_balance(text: str) -> bool:
    return text.count('"') % 2 == 0 and text.count(_OPEN_QUOTE) == text.count(_CLOSE_QUOTE)


def split_sentences(text: str, *, prose: bool = False) -> list[tuple[int, int]]:
    """Character spans of the sentences in `text`.

    A sentence ends at `.`, `?` or `!` (and any closing quote or bracket) followed by
    white space. `prose` is for the draft, where the check depends on the split: nothing
    inside balanced double quotation marks ends a sentence, so a quotation of two
    sentences stays whole, and abbreviations get less benefit of the doubt. If the
    quotation marks do not balance they are ignored, or one stray mark would swallow
    the rest of the paragraph.
    """
    respect_quotes = prose and _quotes_balance(text)
    spans: list[tuple[int, int]] = []
    start: int | None = None
    in_quote = False
    i, n = 0, len(text)
    while i < n:
        char = text[i]
        if start is None and not char.isspace():
            start = i
        if char == '"':
            in_quote = not in_quote
        elif char == _OPEN_QUOTE:
            in_quote = True
        elif char == _CLOSE_QUOTE:
            in_quote = False
        if char not in _TERMINATORS:
            i += 1
            continue
        end = i + 1
        while end < n and text[end] in _TERMINATORS:
            end += 1
        while end < n and text[end] in _CLOSERS:
            if text[end] == '"':
                in_quote = not in_quote
            elif text[end] == _CLOSE_QUOTE:
                in_quote = False
            end += 1
        followed_by_space = end == n or text[end].isspace()
        single_stop = char == "." and end - i == 1
        if (
            start is not None
            and followed_by_space
            and not (respect_quotes and in_quote)
            and not (single_stop and _is_abbreviation(text, i, end, prose))
        ):
            spans.append((start, end))
            start = None
        i = end
    if start is not None:
        spans.append((start, len(text.rstrip())))
    return spans


def citable_text(segment: Segment) -> str:
    """The text of the segment's block in the citable document. The speaker comes first so the
    model can attribute, and so a cited span carries its speaker's name."""
    return f"{segment.speaker}: {segment.text}"


def ingest(text: str, title: str) -> IngestResult:
    if not text.strip():
        raise TranscriptEmpty
    turns = parse_turns(text)
    if not turns:
        raise TranscriptUnparseable
    words = sum(len(turn.text.split()) for turn in turns)
    if words > MAX_WORDS:
        raise TranscriptTooLong
    if len(turns) < MIN_TURNS or words < MIN_WORDS:
        raise TranscriptTooShort

    segments: list[Segment] = []
    for turn_no, turn in enumerate(turns):
        for start, end in split_sentences(turn.text):
            segments.append(
                Segment(
                    index=len(segments),
                    turn=turn_no,
                    speaker=turn.speaker,
                    line=turn.line,
                    text=turn.text[start:end],
                )
            )
    return IngestResult(title=title.strip()[:MAX_TITLE_CHARS], segments=segments)
