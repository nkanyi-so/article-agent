"""Ingest: transcript text in, numbered sentence segments out, or a refusal."""

import json
from pathlib import Path

import pytest

from app.errors import (
    TranscriptEmpty,
    TranscriptTooLong,
    TranscriptTooShort,
    TranscriptUnparseable,
)
from app.pipeline.ingest import (
    MAX_WORDS,
    citable_text,
    ingest,
    parse_turns,
    split_sentences,
)

FIXTURES = Path(__file__).parent / "fixtures"


def sentences(text: str) -> list[str]:
    return [text[start:end] for start, end in split_sentences(text)]


def long_enough(turns: int = 6, words_per_turn: int = 25) -> str:
    filler = " ".join(["word"] * (words_per_turn - 1)) + " end."
    return "\n".join(f"Speaker {'AB'[i % 2]}: {filler}" for i in range(turns))


# ------------------------------------------------------------------ the turn parser


def test_a_plain_turn_gives_speaker_and_text() -> None:
    turns = parse_turns("Priya Lindqvist: Fixed timers. Every block got 9 cycles.")

    assert [(t.speaker, t.text, t.line) for t in turns] == [
        ("Priya Lindqvist", "Fixed timers. Every block got 9 cycles.", 1)
    ]


@pytest.mark.parametrize(
    "line",
    [
        "[00:12] Samir Vale: Sure.",
        "[01:02:03] Samir Vale: Sure.",
        "00:12 Samir Vale: Sure.",
        "(00:12) Samir Vale: Sure.",
    ],
)
def test_a_timestamp_before_the_speaker_is_dropped(line: str) -> None:
    (turn,) = parse_turns(line)

    assert (turn.speaker, turn.text) == ("Samir Vale", "Sure.")


def test_blank_lines_are_skipped_and_line_numbers_are_those_of_the_source() -> None:
    turns = parse_turns("Dana Whitlock: One.\n\n\nJoss Tennant: Two.\n")

    assert [(t.speaker, t.line) for t in turns] == [("Dana Whitlock", 1), ("Joss Tennant", 4)]


def test_a_line_without_a_speaker_continues_the_turn_before_it() -> None:
    turns = parse_turns(
        "Dana Whitlock: We had one goal\nand we met it: ship on time.\nJoss Tennant: Good."
    )

    assert [(t.speaker, t.text) for t in turns] == [
        ("Dana Whitlock", "We had one goal and we met it: ship on time."),
        ("Joss Tennant", "Good."),
    ]


def test_a_sentence_with_a_colon_is_not_mistaken_for_a_speaker() -> None:
    turns = parse_turns("Dana Whitlock: Here is the plan.\nThe short version is this: we wait.")

    assert len(turns) == 1


def test_time_of_day_inside_speech_is_not_a_speaker() -> None:
    (turn,) = parse_turns("Dana Whitlock: We meet at 10:30 tomorrow.")

    assert turn.text == "We meet at 10:30 tomorrow."


# ------------------------------------------------------------------ the sentence splitter


def test_sentences_split_on_full_stops_question_marks_and_exclamations() -> None:
    assert sentences("Loud and clear. Can you hear me? Yes! Good.") == [
        "Loud and clear.",
        "Can you hear me?",
        "Yes!",
        "Good.",
    ]


def test_numbers_with_points_and_commas_are_not_split() -> None:
    assert sentences("It cost 310,000 euros. Yield rose 3.5 percent.") == [
        "It cost 310,000 euros.",
        "Yield rose 3.5 percent.",
    ]


@pytest.mark.parametrize(
    "text",
    [
        "We spoke to Dr. Okonta about it.",
        "Mr. Vale and Mrs. Whitlock agreed.",
        "We sell tools, e.g. spanners, to trade.",
        "It is unit No. 5 on the estate.",
        "J. Tennant signed it.",
        "Hartwell Lane Ltd. owns the depot.",
    ],
)
def test_an_abbreviation_does_not_end_a_sentence(text: str) -> None:
    assert sentences(text) == [text]


def test_the_word_no_ends_a_sentence_unless_a_number_follows() -> None:
    # "No." is an answer far more often than it is "number" in a transcript.
    assert sentences("No. Nobody was laid off.") == ["No.", "Nobody was laid off."]


def test_a_closing_quotation_mark_stays_with_its_sentence() -> None:
    assert sentences('She said "we wait." Then she left.') == [
        'She said "we wait."',
        "Then she left.",
    ]


def test_a_sentence_may_start_with_a_lower_case_word() -> None:
    assert sentences("Yes. sorry, go on.") == ["Yes.", "sorry, go on."]


def test_text_with_no_terminator_is_one_sentence() -> None:
    assert sentences("Thanks both") == ["Thanks both"]


def test_in_prose_a_full_stop_inside_double_quotes_does_not_split() -> None:
    text = 'Vale said: "We shipped 4,300, not 4,800. The 4,800 was the forecast." Whitlock agreed.'

    spans = split_sentences(text, prose=True)

    assert [text[a:b] for a, b in spans] == [
        'Vale said: "We shipped 4,300, not 4,800. The 4,800 was the forecast."',
        "Whitlock agreed.",
    ]


# ------------------------------------------------------------------ segments


def test_segments_are_numbered_across_turns_and_keep_turn_speaker_and_line() -> None:
    result = ingest(long_enough() + "\nSpeaker A: First. Second?", title="A title")

    last_two = result.segments[-2:]
    assert [(s.turn, s.speaker, s.line, s.text) for s in last_two] == [
        (6, "Speaker A", 7, "First."),
        (6, "Speaker A", 7, "Second?"),
    ]
    assert [s.index for s in result.segments] == list(range(len(result.segments)))


def test_the_citable_text_of_a_segment_starts_with_its_speaker() -> None:
    result = ingest(long_enough(), title="A title")

    assert citable_text(result.segments[0]).startswith("Speaker A: word word")


def test_the_title_is_kept_and_trimmed() -> None:
    assert ingest(long_enough(), title="  Quarterly review \n").title == "Quarterly review"


@pytest.mark.parametrize(
    ("transcript", "draft"),
    [
        ("01-korvath-greenhouses.txt", "t1-sentence-sonnet-medium-a.json"),
        ("02-hartwell-lane-correction.txt", "t2-sentence-sonnet-medium.json"),
    ],
)
def test_segments_match_the_blocks_the_recorded_requests_were_built_from(
    transcript: str, draft: str
) -> None:
    # The recorded citations point at block indexes. If ingest ever numbers these
    # transcripts differently, every recorded citation points at the wrong sentence.
    saved = json.loads((FIXTURES / "draft" / draft).read_text())
    blocks = saved["request"]["messages"][0]["content"][0]["source"]["content"]

    result = ingest((FIXTURES / "transcripts" / transcript).read_text(), title="t")

    assert [citable_text(s) for s in result.segments] == [b["text"] for b in blocks]


# ------------------------------------------------------------------ the four refusals


@pytest.mark.parametrize("text", ["", "   \n\t\n  "])
def test_empty_or_whitespace_is_refused(text: str) -> None:
    with pytest.raises(TranscriptEmpty) as refusal:
        ingest(text, title="t")

    assert refusal.value.code == "transcript_empty"
    assert refusal.value.http_status == 422


def test_text_with_no_speaker_turns_is_refused() -> None:
    with pytest.raises(TranscriptUnparseable) as refusal:
        ingest("this is just a paragraph of prose with no one speaking. " * 30, title="t")

    assert refusal.value.code == "transcript_unparseable"


def test_fewer_than_six_turns_is_refused() -> None:
    with pytest.raises(TranscriptTooShort) as refusal:
        ingest(long_enough(turns=5, words_per_turn=40), title="t")

    assert refusal.value.code == "transcript_too_short"


def test_fewer_than_120_spoken_words_is_refused_and_speaker_names_do_not_count() -> None:
    # 6 turns of 19 spoken words is 114; with the two-word speaker labels it would be 126.
    with pytest.raises(TranscriptTooShort):
        ingest(long_enough(turns=6, words_per_turn=19), title="t")


def test_six_turns_and_120_words_is_accepted() -> None:
    result = ingest(long_enough(turns=6, words_per_turn=20), title="t")

    assert len({s.turn for s in result.segments}) == 6


def test_more_than_12000_words_is_refused() -> None:
    turns = MAX_WORDS // 100 + 1

    with pytest.raises(TranscriptTooLong) as refusal:
        ingest(long_enough(turns=turns, words_per_turn=100), title="t")

    assert refusal.value.code == "transcript_too_long"
    assert refusal.value.http_status == 413


def test_a_refusal_message_never_repeats_the_transcript() -> None:
    with pytest.raises(TranscriptUnparseable) as refusal:
        ingest("secret-looking-content with no turns at all " * 40, title="t")

    assert "secret-looking-content" not in str(refusal.value)


# ------------------------------------------------------------------ found by the reviewer


@pytest.mark.parametrize(
    ("line", "speaker"),
    [
        ("Dana Whitlock (CFO): We wait.", "Dana Whitlock"),
        ("Dana Whitlock [CFO]: We wait.", "Dana Whitlock"),
        ("Samir Vale [00:12]: We wait.", "Samir Vale"),
        ("12:30 PM Samir Vale: We wait.", "Samir Vale"),
        ("[1:02 PM] Samir Vale: We wait.", "Samir Vale"),
        ("[1:02:03 pm] Samir Vale: We wait.", "Samir Vale"),
        ("Émile Brandt: We wait.", "Émile Brandt"),
    ],
)
def test_a_role_a_late_timestamp_or_an_accented_name_does_not_hide_a_speaker(
    line: str, speaker: str
) -> None:
    turns = parse_turns(f"Joss Tennant: Go on.\n{line}")

    assert [(t.speaker, t.text) for t in turns] == [
        ("Joss Tennant", "Go on."),
        (speaker, "We wait."),
    ]


def test_in_prose_a_full_stop_after_an_abbreviation_ends_the_sentence_if_a_capital_follows() -> (
    None
):
    text = "It cost a lot for sensors, controllers, etc. The sensors were sold. Plan A. Then B."

    spans = split_sentences(text, prose=True)

    assert [text[a:b] for a, b in spans] == [
        "It cost a lot for sensors, controllers, etc.",
        "The sensors were sold.",
        "Plan A.",
        "Then B.",
    ]


def test_in_prose_a_title_before_a_name_still_does_not_end_a_sentence() -> None:
    text = "We spoke to Dr. Okonta and Mr. Vale. They agreed."

    assert [text[a:b] for a, b in split_sentences(text, prose=True)] == [
        "We spoke to Dr. Okonta and Mr. Vale.",
        "They agreed.",
    ]


def test_in_prose_unbalanced_quotation_marks_are_ignored() -> None:
    text = 'They called it "a mistake. It cost a lot. Nobody left.'

    assert len(split_sentences(text, prose=True)) == 3


def test_splitting_a_very_long_run_of_initials_does_not_take_seconds() -> None:
    import time

    started = time.perf_counter()
    split_sentences("A. " * 20_000)

    assert time.perf_counter() - started < 1.0
