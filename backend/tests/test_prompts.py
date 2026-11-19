"""The prompts must not be written around the transcripts they are tested on."""

import re

from app.evals import judge
from app.evals.cases import load_cases
from app.pipeline import draft, extract
from app.pipeline.ground import _lower_case_words, _names
from app.pipeline.ingest import ingest
from app.seeds import SEEDS
from tests.support import FIXTURES, TRANSCRIPTS

# Capitalised only because they open a sentence in one of the transcripts. Checked by hand.
NOT_NAMES = {
    "Anything", "Can", "Choosing", "Does", "Did", "Do", "Fine", "Forty", "Good", "Has", "Have",
    "How", "Is", "Less", "Loud", "Morning", "Mostly", "Nine", "Probably", "Right", "Same",
    "Sorry", "Sure", "Tell", "Thank", "Thanks", "Understood", "Welcome", "Whatever", "Why",
    "Will", "Flat", "Go", "Let", "Cost", "Text", "Patients", "Postage", "Customers", "Gift",
}  # fmt: skip

PROMPTS = {
    "draft system": draft.DRAFT_SYSTEM,
    "draft notes introduction": draft._NOTES_INTRO,
    "extract system": extract.EXTRACT_SYSTEM,
    "judge system": judge.JUDGE_SYSTEM,
}


def names_in_the_test_transcripts() -> set[str]:
    """Every speaker, organisation, place and month named in a seed, a fixture transcript or
    an eval case."""
    sources = [(seed.text(), seed.title) for seed in SEEDS]
    sources += [
        ((FIXTURES / "transcripts" / filename).read_text(), title)
        for filename, title in TRANSCRIPTS.values()
    ]
    sources += [(case.text(), case.title) for case in load_cases() if case.expect_error is None]
    names: set[str] = set()
    for text, title in sources:
        segments = ingest(text, title).segments
        ordinary = _lower_case_words(segments)
        names |= set(re.findall(r"[A-Z][A-Za-z]+", title.split(":")[0]))
        for segment in segments:
            names |= set(segment.speaker.split())
            # `_names` already leaves out a sentence's first word when the transcript uses
            # that word in lower case. Other openers ("How", "Thanks") are dropped through
            # NOT_NAMES below, so a name that only ever opens a sentence is still caught.
            names |= set(_names(segment.text, ordinary))
    return names - NOT_NAMES


def test_the_seed_names_were_found() -> None:
    names = names_in_the_test_transcripts()

    assert {"Korvath", "Vance", "Ellsmoor", "Sallowfield", "Olund", "Hana", "Quillmoor"} <= names
    assert {"Farrow", "Abbey", "Hartwell", "Pellowmere", "Dunmore", "Stanek"} <= names
    # A person who is named but never speaks, at the start of a sentence.
    assert "Odette" in names


def test_no_prompt_contains_a_name_from_a_seeded_or_fixture_transcript() -> None:
    # A prompt whose worked examples come from the test transcripts is tuned on the test:
    # it measured 2.1% removed, against 6.6% with the same prompt and neutral examples.
    names = names_in_the_test_transcripts()

    for label, prompt in PROMPTS.items():
        found = sorted(name for name in names if re.search(rf"\b{re.escape(name)}\b", prompt))
        assert not found, f"{label} names {found}"


def test_the_readme_states_the_claim_word_for_word_as_decided() -> None:
    root = FIXTURES.parents[2]
    decided = [
        line[2:]
        for line in (root / "docs/decisions/0015-the-claim.md").read_text().splitlines()
        if line.startswith("> ")
    ]
    assert len(decided) == 1
    assert decided[0] in (root / "README.md").read_text()
