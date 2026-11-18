"""Ground: keep a sentence of the draft only if the transcript backs it.

Pure code. No model, no network. The rules are in `docs/decisions/0003-ground-check.md`.
A sentence that fails is removed and recorded with its reason. It is never given another
citation, reworded, or kept with a warning.

Where a choice had to be made, the doubt goes against the sentence: a true sentence
wrongly removed costs prose, a false one wrongly kept costs the claim.
"""

import re
from dataclasses import dataclass

from app.errors import TooFewGroundedClaims
from app.pipeline.ingest import citable_text, split_sentences
from app.schemas import (
    Citation,
    Claim,
    Correction,
    DraftBlock,
    GroundResult,
    Headline,
    HeadlineFailure,
    NameResolution,
    RemovalReason,
    RemovedUnit,
    Segment,
)

MIN_CLAIMS = 3
# A cited block lends its citation to a sentence it only partly overlaps if the overlap is at
# least this many words. Less than that is the block spilling a word into the next sentence.
MIN_OVERLAP_WORDS = 3

_LETTER = r"[^\W\d_]"
_APOSTROPHES = "'’"  # noqa: RUF001 (curly quotes are what this matches)
_OPEN_MARKS = '"“«'
_CLOSE_MARKS = '"”»'
_QUOTE_MARKS = _OPEN_MARKS + _CLOSE_MARKS
_SENTENCE_ENDS = (".", "?", "!")
# Digits, with commas only where they group thousands, so "6,0" is two numbers and not sixty.
_DIGITS = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")
_WORD = re.compile(rf"{_LETTER}+(?:[{_APOSTROPHES}]{_LETTER}+)?")
_QUOTED = re.compile(rf"[{_OPEN_MARKS}]([^{_QUOTE_MARKS}]+)[{_CLOSE_MARKS}]")
_LINE = re.compile(r"[^\n]+")

_UNITS = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
}  # fmt: skip
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
}  # fmt: skip
_OTHER = {
    "zero": 0, "couple": 2, "dozen": 12, "hundred": 100, "thousand": 1000,
    "million": 1_000_000, "billion": 1_000_000_000,
}  # fmt: skip
# "one" is left out on purpose: it is a pronoun or an article far more often than a figure.
_NUMBER_WORDS: dict[str, int] = _UNITS | _TENS | _OTHER
_LAST_DIGIT = {"one": 1} | {word: value for word, value in _UNITS.items() if value < 10}
_COMPOUND = re.compile(rf"\b({'|'.join(_TENS)})[- ]({'|'.join(_LAST_DIGIT)})\b", re.I)

# Capitalised words that are never names, wherever they stand.
_NEVER_NAMES = {
    "a", "about", "according", "after", "all", "also", "although", "an", "and", "another", "any",
    "as", "asked", "at", "because", "before", "both", "but", "by", "each", "every", "first",
    "for", "from", "he", "her", "his", "however", "i", "if", "in", "it", "its", "last",
    "looking", "meanwhile", "most", "next", "no", "nobody", "none", "not", "now", "of", "on",
    "one", "other", "our", "previously", "second", "she", "since", "so", "some", "still",
    "that", "the", "their", "then", "there", "these", "they", "third", "this", "those", "to",
    "under", "until", "we", "what", "when", "where", "which", "while", "who", "with", "yes",
    "you",
}  # fmt: skip


_TITLES = {"dr", "mr", "mrs", "ms", "prof"}


_CALENDAR = {
    "january", "february", "march", "april", "may", "june", "july", "august", "september",
    "october", "november", "december", "monday", "tuesday", "wednesday", "thursday", "friday",
    "saturday", "sunday",
}  # fmt: skip

FirstNames = dict[str, tuple[str, set[str]]]


def _label_words(label: str) -> list[str]:
    return [word for word in label.split() if word.rstrip(".").lower() not in _TITLES]


def _first_names(segments: list[Segment], ordinary: set[str]) -> FirstNames:
    """For each first name that can only mean one speaker: that speaker's label and the
    rest of its words.

    Left out, so that they support nothing: a first name two speakers share; one that is
    also any other word of another speaker's label; one the transcript also uses as an
    ordinary word ("will", "mark"); a month or a weekday ("June", "May"); and a one-word
    label, which has no surname to support.
    """
    labels = {segment.speaker for segment in segments}
    resolved: FirstNames = {}
    for label in labels:
        words = _label_words(label)
        if len(words) < 2:
            continue
        first = words[0]
        elsewhere = [w.lower() for other in labels - {label} for w in _label_words(other)]
        if first.lower() in elsewhere:
            continue
        if first.lower() in ordinary or first.lower() in _CALENDAR or first.lower() in _NEVER_NAMES:
            continue
        resolved[first] = (label, {word.lower() for word in words[1:]})
    return resolved


def _names_someone(text: str, first: str) -> bool:
    """Whether `first` appears in `text` written as a name: inside the sentence, or opening
    it as a form of address ("Hana, run the calls"). A capitalised word that merely opens
    a sentence ("Will do.") is not taken for a name."""
    pattern = rf"(?<!{_LETTER}){re.escape(first)}(?!{_LETTER})"
    for match in re.finditer(pattern, text):
        if text[: match.start()].strip() or text[match.end() :].startswith(","):
            return True
    return False


def _resolve_by_first_name(
    name: str, cited: list[Segment], first_names: FirstNames
) -> NameResolution | None:
    """`name` is not in the cited text. It still stands if it is the surname of a speaker
    whose first name, written as a name, is in a cited sentence and can only mean them."""
    for first, (label, surnames) in first_names.items():
        if name.lower() in surnames and any(_names_someone(s.text, first) for s in cited):
            return NameResolution(name=name, first_name=first, speaker=label)
    return None


@dataclass(frozen=True)
class _Sentence:
    text: str
    paragraph: int
    citations: tuple[Citation, ...]


@dataclass(frozen=True)
class _Number:
    """A figure as written and as a value, so "4,300" and "sixty" compare with "4300" and "60"."""

    written: str
    value: str


def _compound_marker(match: re.Match[str]) -> str:
    value = _TENS[match.group(1).lower()] + _LAST_DIGIT[match.group(2).lower()]
    return f"\x00{value}:{match.group()}\x00"


def _numbers(text: str) -> list[_Number]:
    found = [_Number(m.group(), m.group().replace(",", "")) for m in _DIGITS.finditer(text)]
    # "twenty-five" is one number, not twenty and five.
    marked = _COMPOUND.sub(_compound_marker, text)
    for match in re.finditer(r"\x00(\d+):([^\x00]+)\x00|[A-Za-z]+", marked):
        if match.group(1):
            found.append(_Number(match.group(2), match.group(1)))
        elif match.group().lower() in _NUMBER_WORDS:
            found.append(_Number(match.group(), str(_NUMBER_WORDS[match.group().lower()])))
    return found


def _values(text: str) -> set[str]:
    return {number.value for number in _numbers(text)}


def _lower_case_words(segments: list[Segment]) -> set[str]:
    """Words the transcript itself writes in lower case: evidence that a word is ordinary."""
    return {word for segment in segments for word in _WORD.findall(segment.text) if word.islower()}


def _names(text: str, ordinary: set[str]) -> list[str]:
    """Capitalised words taken as proper names (months and weekdays included, which is how a
    date is checked beyond its digits).

    A word that opens the text is a name unless the transcript uses it in lower case.
    """
    names: list[str] = []
    for position, match in enumerate(_WORD.finditer(text)):
        word = re.sub(rf"[{_APOSTROPHES}]s$", "", match.group())
        if not word[0].isupper():
            continue
        lowered = word.lower()
        if lowered in _NEVER_NAMES or lowered in _NUMBER_WORDS:
            continue
        if position == 0 and lowered in ordinary:
            continue
        if word not in names:
            names.append(word)
    return names


def _contains_word(haystack: str, word: str) -> bool:
    pattern = rf"(?<!{_LETTER}){re.escape(word)}(?!{_LETTER})"
    return re.search(pattern, haystack, re.I) is not None


def _normalise(text: str) -> str:
    text = text.replace("’", "'").replace("‘", "'")  # noqa: RUF001 (curly quotes are what this matches)
    return " ".join(text.split()).casefold()


def _quotations(text: str) -> list[str]:
    return [quote.strip() for quote in _QUOTED.findall(text) if quote.strip()]


def _quotes_are_closed(text: str) -> bool:
    straight = text.count('"') % 2 == 0
    paired = all(text.count(a) == text.count(b) for a, b in ("“”", "«»"))
    return straight and paired


def _is_verbatim(quote: str, sources: list[str]) -> bool:
    wanted = _normalise(quote).rstrip(",.;:!?")
    return any(wanted in _normalise(source) for source in sources)


def _runs(cited: list[Segment]) -> list[str]:
    """The cited text as stretches one person said without interruption: consecutive segments
    of the same turn, joined. A quotation has to sit inside one of them, so words from two
    speakers, or from two separate moments, cannot be stitched into one quotation."""
    runs: list[list[Segment]] = []
    for segment in cited:
        last = runs[-1][-1] if runs else None
        if last and segment.index == last.index + 1 and segment.turn == last.turn:
            runs[-1].append(segment)
        else:
            runs.append([segment])
    return [" ".join(segment.text for segment in run) for run in runs]


def _lends_citation(overlap: str, block_text: str) -> bool:
    """Whether a cited block's overlap with a sentence is enough to count as citing it."""
    overlap = overlap.strip()
    return bool(overlap) and (
        overlap == block_text.strip() or len(overlap.split()) >= MIN_OVERLAP_WORDS
    )


def _sentences(blocks: list[DraftBlock]) -> tuple[str | None, list[_Sentence]]:
    """Joins the blocks, takes the first line as the headline, and splits the rest into
    sentences. Each sentence gets the citations of every cited block it overlaps."""
    text = "".join(block.text for block in blocks)
    spans: list[tuple[int, int, DraftBlock]] = []
    position = 0
    for block in blocks:
        spans.append((position, position + len(block.text), block))
        position += len(block.text)

    lines = [line for line in _LINE.finditer(text) if line.group().strip()]
    headline: str | None = None
    # A headline is a first line with body after it that does not end like a sentence (the
    # draft prompt asks for no trailing full stop). A first line that does end like one is a
    # paragraph of the body: the draft then has no headline, and nothing is lost from the body.
    first_line = lines[0].group().rstrip().rstrip(_QUOTE_MARKS) if lines else ""
    if len(lines) > 1 and not first_line.endswith(_SENTENCE_ENDS):
        headline = lines[0].group().strip()
        lines = lines[1:]

    sentences: list[_Sentence] = []
    for paragraph, line in enumerate(lines):
        for start, end in split_sentences(line.group(), prose=True):
            first, last = line.start() + start, line.start() + end
            sentence = text[first:last].strip()
            if not any(char.isalnum() for char in sentence):
                continue  # punctuation alone says nothing and is not a claim
            citations: list[Citation] = []
            for block_start, block_end, block in spans:
                overlap = text[max(first, block_start) : min(last, block_end)]
                if block.citations and _lends_citation(overlap, block.text):
                    citations += [c for c in block.citations if c not in citations]
            sentences.append(_Sentence(sentence, paragraph, tuple(citations)))
    return headline, sentences


def _cited_segments(sentence: _Sentence, segments: list[Segment]) -> list[Segment] | None:
    """The segments the sentence cites, or None if any citation points outside the transcript.

    The range is checked before it is walked: a citation is model output, and a range of a
    billion segments must be refused, not expanded.
    """
    indexes: set[int] = set()
    for citation in sentence.citations:
        if not 0 <= citation.start_segment < citation.end_segment <= len(segments):
            return None
        indexes.update(range(citation.start_segment, citation.end_segment))
    return [segments[i] for i in sorted(indexes)]


def _check(
    sentence: _Sentence,
    cited: list[Segment] | None,
    superseded: set[int],
    ordinary: set[str],
    first_names: FirstNames,
    resolutions: list[NameResolution],
) -> tuple[RemovalReason, list[str]] | None:
    """The first rule the sentence fails, with what was missing, or None if it passes all four.
    Names that stand only through the first-name rule are appended to `resolutions`."""
    if not sentence.citations:
        return "no_citation", []
    if cited is None:
        return "invalid_citation", []

    # Checked against the transcript's own text for those segments, not the response's copy of it.
    with_speakers = " ".join(citable_text(segment) for segment in cited)
    spoken = " ".join(segment.text for segment in cited)
    numbers = _numbers(sentence.text)

    source_values = _values(spoken)
    missing_numbers = [n.written for n in numbers if n.value not in source_values]
    if missing_numbers:
        return "unsupported_number", missing_numbers
    names = _names(sentence.text, ordinary)
    missing_names: list[str] = []
    for name in names:
        if _contains_word(with_speakers, name):
            continue
        resolution = _resolve_by_first_name(name, cited, first_names)
        if resolution:
            resolutions.append(resolution)
        else:
            missing_names.append(name)
    if missing_names:
        return "unsupported_name", missing_names
    if not _quotes_are_closed(sentence.text):
        return "misquote", ["a quotation mark is never closed"]
    misquotes = [q for q in _quotations(sentence.text) if not _is_verbatim(q, _runs(cited))]
    if misquotes:
        return "misquote", misquotes

    current = [segment for segment in cited if segment.index not in superseded]
    if not current:
        return "rests_on_corrected_segment", []
    if len(current) < len(cited):
        # It cites a superseded segment beside others. Its figures must stand on the others:
        # citing a neighbour does not make the old figure current.
        current_values = _values(" ".join(segment.text for segment in current))
        stale = [n.written for n in numbers if n.value not in current_values]
        if stale:
            return "rests_on_corrected_segment", stale
    return None


def _check_headline(
    text: str | None,
    title: str,
    claims: list[Claim],
    segments: list[Segment],
    superseded: set[int],
    ordinary: set[str],
) -> Headline:
    """The headline has no citation of its own, so it is checked against the kept sentences."""

    def fallback(failure: HeadlineFailure, detail: list[str]) -> Headline:
        return Headline(
            text=title, source="title", rejected_text=text, failure=failure, failure_detail=detail
        )

    if not text:
        return fallback("headline_missing", [])

    numbers = _numbers(text)
    old_values = _values(" ".join(segments[i].text for i in superseded if i < len(segments)))
    stale = [n.written for n in numbers if n.value in old_values]
    if stale:
        return fallback("headline_superseded_number", stale)

    body = " ".join(claim.text for claim in claims)
    body_values = _values(body)
    missing_numbers = [n.written for n in numbers if n.value not in body_values]
    if missing_numbers:
        return fallback("headline_unsupported_number", missing_numbers)
    names = _names(text, ordinary)
    missing_names = [name for name in names if not _contains_word(body, name)]
    if missing_names:
        return fallback("headline_unsupported_name", missing_names)
    if not _quotes_are_closed(text):
        return fallback("headline_misquote", ["a quotation mark is never closed"])
    misquotes = [q for q in _quotations(text) if not _is_verbatim(q, [c.text for c in claims])]
    if misquotes:
        return fallback("headline_misquote", misquotes)

    values = {n.value for n in numbers}
    supporting = [
        i
        for i, claim in enumerate(claims)
        if values & _values(claim.text) or any(_contains_word(claim.text, name) for name in names)
    ]
    # Nothing checkable in it: its support is the whole kept body, which is what the judge gets.
    return Headline(
        text=text, source="model", supporting_claims=supporting or list(range(len(claims)))
    )


def ground(
    blocks: list[DraftBlock], segments: list[Segment], corrections: list[Correction], title: str
) -> GroundResult:
    """Checks the draft against the transcript. Raises `TooFewGroundedClaims`, carrying the
    result, if fewer than three sentences survive."""
    superseded = {correction.superseded for correction in corrections}
    ordinary = _lower_case_words(segments)
    first_names = _first_names(segments, ordinary)
    headline_text, sentences = _sentences(blocks)

    claims: list[Claim] = []
    removed: list[RemovedUnit] = []
    for sentence in sentences:
        cited = _cited_segments(sentence, segments)
        indexes = [segment.index for segment in cited or []]
        resolutions: list[NameResolution] = []
        failure = _check(sentence, cited, superseded, ordinary, first_names, resolutions)
        if failure:
            reason, detail = failure
            removed.append(
                RemovedUnit(
                    text=sentence.text,
                    paragraph=sentence.paragraph,
                    reason=reason,
                    detail=detail,
                    segment_indexes=indexes,
                )
            )
        else:
            claims.append(
                Claim(
                    text=sentence.text,
                    paragraph=sentence.paragraph,
                    citations=list(sentence.citations),
                    segment_indexes=indexes,
                    name_resolutions=resolutions,
                )
            )

    headline = _check_headline(headline_text, title, claims, segments, superseded, ordinary)
    result = GroundResult(headline=headline, claims=claims, removed=removed)
    if len(claims) < MIN_CLAIMS:
        raise TooFewGroundedClaims(result)
    return result
