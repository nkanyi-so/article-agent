"""The ground check: a sentence of the draft is kept only if the transcript backs it.

Each rule is shown twice: passing a real recorded response, and removing a copy of that
response altered by hand in one place. A check that cannot fail proves nothing.
"""

import ast
from pathlib import Path

import pytest

from app.errors import TooFewGroundedClaims
from app.pipeline.ground import ground
from app.schemas import Citation, Correction, DraftBlock, GroundResult, RemovedUnit
from tests.support import DRAFTS, Recorded, recorded

T1 = "t1-sentence-sonnet-medium-a"
T2 = "t2-sentence-sonnet-medium"


def run(rec: Recorded, corrections: list[Correction] | None = None) -> GroundResult:
    chosen = rec.corrections if corrections is None else corrections
    return ground(rec.blocks(), rec.segments, chosen, rec.title)


def kept(result: GroundResult) -> list[str]:
    return [claim.text for claim in result.claims]


def removed(result: GroundResult, containing: str) -> RemovedUnit:
    (unit,) = [unit for unit in result.removed if containing in unit.text]
    return unit


# ------------------------------------------------------------------ the unit is the sentence


def test_a_sentence_is_assembled_from_its_uncited_lead_in_and_its_cited_clause() -> None:
    result = run(recorded(T1))

    sentence = (
        "Operations director Teodor Vance said tomato water use went from 22 litres "
        "per kilo of fruit to 15 litres."
    )
    (claim,) = [c for c in result.claims if c.text == sentence]
    assert claim.segment_indexes == [37]
    assert claim.paragraph == 1


def test_a_sentence_citing_two_places_carries_both() -> None:
    result = run(recorded(T1))

    (claim,) = [c for c in result.claims if c.text.startswith("Lindqvist advised other growers")]
    assert claim.segment_indexes == [92, 94, 95]
    assert len(claim.citations) == 2


def test_every_sentence_of_the_draft_is_either_kept_or_removed_and_never_both() -> None:
    result = run(recorded(T1))

    assert len(result.claims) + len(result.removed) == 22
    assert not set(kept(result)) & {unit.text for unit in result.removed}


def test_a_removed_sentence_is_stored_as_written_and_never_given_a_citation() -> None:
    result = run(recorded(T1))

    unit = removed(result, "The two differ on yield.")
    assert unit.text == "The two differ on yield."
    assert unit.segment_indexes == []


def test_a_thinking_block_is_not_part_of_the_draft() -> None:
    rec = recorded("t1-sentence-opus-medium")
    assert any(block["type"] == "thinking" for block in rec.content)

    result = run(rec)

    assert result.claims


@pytest.mark.parametrize("name", DRAFTS)
def test_every_recorded_draft_goes_through_the_check(name: str) -> None:
    result = run(recorded(name))

    assert len(result.claims) >= 3
    assert all(claim.segment_indexes for claim in result.claims)


# ------------------------------------------------------------------ rule 1: a citation


def test_rule_1_real_a_cited_sentence_is_kept() -> None:
    assert "Fertiliser spend is down 11 percent." in kept(run(recorded(T1)))


def test_rule_1_altered_the_same_sentence_without_its_citation_is_removed() -> None:
    rec = recorded(T1)
    rec.find("Fertiliser spend is down 11 percent.")["citations"] = None

    unit = removed(run(rec), "Fertiliser spend is down 11 percent.")

    assert unit.reason == "no_citation"


def test_rule_1_real_a_bridge_sentence_the_model_did_not_cite_is_removed() -> None:
    assert removed(run(recorded(T1)), "The two differ on yield.").reason == "no_citation"


def test_a_citation_pointing_outside_the_transcript_removes_the_sentence() -> None:
    rec = recorded(T1)
    rec.find("Fertiliser spend is down 11 percent.")["citations"][0]["end_block_index"] = 999

    unit = removed(run(rec), "Fertiliser spend is down 11 percent.")

    assert unit.reason == "invalid_citation"


# ------------------------------------------------------------------ rule 2: numbers, dates, names


def test_rule_2_real_a_sentence_whose_numbers_are_in_its_cited_text_is_kept() -> None:
    assert any("22 litres" in text for text in kept(run(recorded(T1))))


def test_rule_2_altered_a_wrong_number_is_removed() -> None:
    rec = recorded(T1)
    block = rec.find("went from 22 litres")
    block["text"] = block["text"].replace("22 litres", "25 litres")

    unit = removed(run(rec), "25 litres")

    assert unit.reason == "unsupported_number"
    assert unit.detail == ["25"]


def test_rule_2_real_a_number_written_with_a_comma_matches_the_transcript() -> None:
    assert any("310,000 euros" in text for text in kept(run(recorded(T1))))


def test_rule_2_a_number_in_words_matches_the_same_number_in_digits() -> None:
    rec = recorded(T1)
    block = rec.find("knocked out 60 sensors for two days")
    block["text"] = block["text"].replace("60 sensors for two days", "sixty sensors for 2 days")

    assert any("sixty sensors for 2 days" in text for text in kept(run(rec)))


def test_rule_2_altered_a_number_in_words_that_nobody_said_is_removed() -> None:
    rec = recorded(T1)
    block = rec.find("knocked out 60 sensors for two days")
    block["text"] = block["text"].replace("two days", "five days")

    unit = removed(run(rec), "five days")

    assert (unit.reason, unit.detail) == ("unsupported_number", ["five"])


def test_rule_2_real_a_speaker_named_in_an_uncited_lead_in_is_the_cited_speaker() -> None:
    assert any(
        text.startswith("Operations director Teodor Vance said") for text in kept(run(recorded(T1)))
    )


def test_rule_2_altered_a_wrong_name_is_removed() -> None:
    rec = recorded(T1)
    block = rec.find("Operations director Teodor Vance said")
    block["text"] = block["text"].replace("Teodor Vance", "Teodor Vantz")

    unit = removed(run(rec), "Teodor Vantz")

    assert (unit.reason, unit.detail) == ("unsupported_name", ["Vantz"])


def test_rule_2_altered_a_statement_put_in_the_wrong_speakers_mouth_is_removed() -> None:
    rec = recorded(T1)
    block = rec.find("Operations director Teodor Vance said")
    block["text"] = block["text"].replace("Operations director Teodor Vance", "Priya Lindqvist")

    unit = removed(run(rec), "Priya Lindqvist said tomato water use")

    assert unit.reason == "unsupported_name"


def test_rule_2_real_a_true_sentence_whose_subject_is_named_in_another_block_is_removed() -> None:
    # The cost of the strict rule, on a real response: the company is named in the title and
    # in a neighbouring sentence the model did not cite. Kept strict by the owner's decision.
    unit = removed(run(recorded(T1)), "Korvath Greenhouses began an irrigation pilot")

    assert (unit.reason, unit.detail) == ("unsupported_name", ["Korvath", "Greenhouses"])


def test_rule_2_real_a_date_outside_the_cited_text_is_removed() -> None:
    unit = removed(run(recorded(T1)), "rollout finished in October 2025")

    assert unit.reason == "unsupported_number"
    assert unit.detail == ["2025"]


def test_rule_2_altered_a_wrong_month_is_removed() -> None:
    rec = recorded(T1)
    block = rec.find("In June a firmware update")
    block["text"] = block["text"].replace("In June", "In July")

    unit = removed(run(rec), "In July")

    assert (unit.reason, unit.detail) == ("unsupported_name", ["July"])


def test_rule_2_an_ordinary_word_that_starts_a_sentence_is_not_taken_for_a_name() -> None:
    result = run(recorded(T1))

    assert "Fertiliser spend is down 11 percent." in kept(result)
    assert "Those rows went back on the old timers." in kept(result)


# ------------------------------------------------------------------ rule 3: quotations


def test_rule_3_real_a_verbatim_quotation_is_kept() -> None:
    assert any("thirsty at eleven" in text for text in kept(run(recorded(T1))))


def test_rule_3_altered_a_quotation_with_one_word_changed_is_removed() -> None:
    rec = recorded(T1)
    block = rec.find("thirsty at eleven")
    block["text"] = block["text"].replace("thirsty at eleven", "thirsty by eleven")

    unit = removed(run(rec), "thirsty by eleven")

    assert unit.reason == "misquote"
    assert "thirsty by eleven" in unit.detail[0]


def test_rule_3_real_a_short_quotation_inside_a_sentence_is_checked_too() -> None:
    assert any('"keep the timers"' in text for text in kept(run(recorded(T1))))


def test_rule_3_altered_words_quoted_from_a_sentence_the_claim_does_not_cite_are_removed() -> None:
    rec = recorded(T1)
    block = rec.find('"keep the timers"')
    # Words really said in the transcript (segment 75), but not in anything this sentence cites.
    block["text"] = block["text"].replace('"keep the timers"', '"Nobody was laid off"')

    unit = removed(run(rec), '"Nobody was laid off"')

    assert unit.reason == "misquote"


# ------------------------------------------------------------------ rule 4: corrections


CORRECTED_ONLY = "Samir Vale said the company shipped 4,800 pallets in the quarter."


def altered_to_rest_on_the_corrected_segment() -> Recorded:
    """Transcript 2's first claim, rewritten to state the old figure and cite only segment 4."""
    rec = recorded(T2)
    block = rec.find("shipped 4,300 pallets in the third quarter")
    block["text"] = CORRECTED_ONLY
    block["citations"] = [
        {
            "type": "content_block_location",
            "cited_text": "Samir Vale: We shipped 4,800 pallets in the quarter, "
            "which is our best quarter so far.",
            "document_index": 0,
            "document_title": rec.title,
            "start_block_index": 4,
            "end_block_index": 5,
        }
    ]
    return rec


def test_rule_4_the_recorded_extract_names_the_correction() -> None:
    assert recorded(T2).corrections == [Correction(superseded=4, replaced_by=16)]


def test_rule_4_altered_a_sentence_resting_only_on_the_corrected_segment_is_removed() -> None:
    unit = removed(run(altered_to_rest_on_the_corrected_segment()), "4,800 pallets in the quarter")

    assert unit.reason == "rests_on_corrected_segment"
    assert unit.segment_indexes == [4]


def test_rule_4_is_what_removes_it_the_same_sentence_passes_every_other_rule() -> None:
    result = run(altered_to_rest_on_the_corrected_segment(), corrections=[])

    assert CORRECTED_ONLY in kept(result)


def test_rule_4_real_mentioning_the_old_figure_while_citing_the_correction_is_kept() -> None:
    result = run(recorded(T2))

    assert any(text.startswith("He had first given a figure of 4,800") for text in kept(result))


# ------------------------------------------------------------------ fewer than three


def sentence(text: str, segment: int, source: str) -> DraftBlock:
    citation = Citation(start_segment=segment, end_segment=segment + 1, cited_text=source)
    return DraftBlock(text=text, citations=[citation])


def test_fewer_than_three_surviving_sentences_fails_the_run_and_keeps_the_record() -> None:
    rec = recorded(T1)
    blocks = [
        DraftBlock(text="A headline\n\n"),
        sentence("Fertiliser spend is down 11 percent.", 46, ""),
        DraftBlock(text=" Nobody said this sentence at all."),
        sentence(" Ellsmoor has 420 sensors.", 27, ""),
    ]

    with pytest.raises(TooFewGroundedClaims) as failure:
        ground(blocks, rec.segments, [], rec.title)

    assert failure.value.code == "too_few_grounded_claims"
    assert len(failure.value.result.claims) == 2
    assert [unit.reason for unit in failure.value.result.removed] == ["no_citation"]


def test_three_surviving_sentences_is_enough() -> None:
    rec = recorded(T1)
    blocks = [
        DraftBlock(text="A headline\n\n"),
        sentence("Fertiliser spend is down 11 percent.", 46, ""),
        sentence(" Ellsmoor has 420 sensors.", 27, ""),
        sentence(" Nobody was laid off.", 75, ""),
    ]

    assert len(ground(blocks, rec.segments, [], rec.title).claims) == 3


# ------------------------------------------------------------------ the headline


def with_headline(rec: Recorded, headline: str) -> Recorded:
    first = rec.content[[b["type"] for b in rec.content].index("text")]
    first["text"] = headline + "\n\n" + first["text"].split("\n\n", 1)[1]
    return rec


def test_a_headline_whose_numbers_and_names_are_in_kept_sentences_is_used() -> None:
    result = run(with_headline(recorded(T1), "Ellsmoor cuts fertiliser spend by 11 percent"))

    assert result.headline.source == "model"
    assert result.headline.text == "Ellsmoor cuts fertiliser spend by 11 percent"
    assert result.headline.failure is None
    supporting = [result.claims[i].text for i in result.headline.supporting_claims]
    assert "Fertiliser spend is down 11 percent." in supporting


def test_real_the_models_headline_names_the_company_which_no_kept_sentence_does() -> None:
    # On the recorded response the strict name rule removed the only sentences that name
    # the company, so the headline has nothing to stand on and the title is used.
    result = run(recorded(T1))

    assert result.headline.source == "title"
    assert result.headline.text == "Korvath Greenhouses: interview on the irrigation project"
    assert result.headline.failure == "headline_unsupported_name"
    assert result.headline.rejected_text == (
        "Korvath Greenhouses cuts tomato water use by a third with soil sensors"
    )
    assert result.headline.failure_detail == ["Korvath", "Greenhouses"]


def test_a_headline_with_a_number_no_kept_sentence_has_falls_back_to_the_title() -> None:
    result = run(with_headline(recorded(T1), "Ellsmoor cuts fertiliser spend by 40 percent"))

    assert (result.headline.source, result.headline.failure) == (
        "title",
        "headline_unsupported_number",
    )
    assert result.headline.failure_detail == ["40"]


def test_a_headline_number_from_a_removed_sentence_does_not_count() -> None:
    # "2025" appears in the draft only in sentences the check removed.
    result = run(with_headline(recorded(T1), "Ellsmoor on sensors since 2025"))

    assert result.headline.failure == "headline_unsupported_number"


def test_a_headline_quotation_must_be_verbatim_in_a_kept_sentence() -> None:
    good = run(with_headline(recorded(T1), 'Vance: "keep the timers"'))
    bad = run(with_headline(recorded(T1), 'Vance: "throw away the timers"'))

    assert good.headline.source == "model"
    assert (bad.headline.source, bad.headline.failure) == ("title", "headline_misquote")


def test_a_headline_stating_the_superseded_figure_falls_back_to_the_title() -> None:
    # A kept sentence says "He had first given a figure of 4,800", so "appears in a kept
    # sentence" alone would let this through. The superseded segment's own numbers do not count.
    result = run(with_headline(recorded(T2), "Record quarter: 4,800 pallets"))

    assert (result.headline.source, result.headline.failure) == (
        "title",
        "headline_superseded_number",
    )
    assert result.headline.failure_detail == ["4,800"]


def test_a_headline_stating_the_corrected_figure_is_used() -> None:
    result = run(with_headline(recorded(T2), "Vale reports 4,300 pallets, a record"))

    assert result.headline.source == "model"


def test_a_headline_with_nothing_to_check_is_supported_by_the_whole_kept_body() -> None:
    result = run(with_headline(recorded(T1), "Sensors cut water use"))

    assert result.headline.source == "model"
    assert result.headline.supporting_claims == list(range(len(result.claims)))


def test_a_draft_with_no_headline_line_takes_the_title() -> None:
    rec = recorded(T1)
    rec.content[0]["text"] = ""  # the first line is now the first paragraph of the body

    result = run(rec)

    assert (result.headline.source, result.headline.failure) == ("title", "headline_missing")
    assert len(result.claims) + len(result.removed) == 22


# ------------------------------------------------------------------ no model in this phase


def test_no_module_of_the_app_imports_a_model_client() -> None:
    imported: set[str] = set()
    for path in (Path(__file__).parents[1] / "app").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                imported |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])

    assert "anthropic" not in imported
    assert "httpx" not in imported


# ------------------------------------------------------------------ found by the reviewer
#
# Each of these got a made-up sentence through the first version of the check.


def insert_after(rec: Recorded, anchor: str, text: str) -> None:
    """Adds an uncited block straight after the block containing `anchor`."""
    position = rec.content.index(rec.find(anchor))
    rec.content.insert(position + 1, {"type": "text", "text": text, "citations": None})


def test_a_citation_range_of_a_billion_segments_is_refused_not_expanded() -> None:
    rec = recorded(T1)
    rec.find("Fertiliser spend is down 11 percent.")["citations"][0]["end_block_index"] = 10**9

    unit = removed(run(rec), "Fertiliser spend is down 11 percent.")

    assert unit.reason == "invalid_citation"
    assert unit.segment_indexes == []


def test_a_stray_quotation_mark_does_not_merge_the_paragraph_into_one_sentence() -> None:
    rec = recorded(T1)
    cost = rec.find("The Ellsmoor project cost 310,000 euros")
    cost["text"] = 'The board called it "a costly mistake. ' + cost["text"]

    result = run(rec)

    # The sentences after the stray mark are still separate, each on its own citation.
    assert "Nobody was laid off, and three growers were retrained to read sensor data." in kept(
        result
    )
    assert removed(result, "a costly mistake").reason == "misquote"


def test_an_uncited_sentence_after_a_stray_quotation_mark_is_still_removed() -> None:
    rec = recorded(T1)
    cost = rec.find("The Ellsmoor project cost 310,000 euros")
    cost["text"] = cost["text"].replace("including sensors", 'including "sensors')
    insert_after(rec, "The Ellsmoor project cost 310,000 euros", " The sensors were then sold off.")

    assert removed(run(rec), "The sensors were then sold off.").reason == "no_citation"


def test_a_quotation_stitched_from_two_speakers_is_a_misquote() -> None:
    rec = recorded(T1)
    block = rec.find("yield was flat and he would not claim a gain.")
    block["text"] = '"Flat. Cucumber yield was up 4 percent in the sensor blocks."'
    block["citations"][0]["start_block_index"] = 49
    block["citations"][0]["end_block_index"] = 53  # Vance's "Flat." through Lindqvist's sentence

    unit = removed(run(rec), 'Cucumber yield was up 4 percent in the sensor blocks."')

    assert unit.reason == "misquote"


def test_a_quotation_of_two_consecutive_sentences_by_one_speaker_is_verbatim() -> None:
    rec = recorded(T1)
    block = rec.find("yield was flat and he would not claim a gain.")
    block["text"] = '"Flat. I would not claim a yield gain from this."'

    assert any("I would not claim a yield gain" in text for text in kept(run(rec)))


def test_an_unclosed_quotation_cannot_be_checked_and_is_removed() -> None:
    rec = recorded(T1)
    block = rec.find("thirsty at eleven")
    block["text"] = block["text"].rstrip('"')

    assert removed(run(rec), "thirsty at eleven").reason == "misquote"


def test_rule_4_altered_citing_an_extra_segment_beside_the_corrected_one_does_not_rescue_it() -> (
    None
):
    rec = altered_to_rest_on_the_corrected_segment()
    citation = rec.find(CORRECTED_ONLY)["citations"][0]
    citation["start_block_index"], citation["end_block_index"] = 3, 5  # adds Vale's "Sure."

    unit = removed(run(rec), "4,800 pallets in the quarter")

    assert (unit.reason, unit.detail) == ("rests_on_corrected_segment", ["4,800"])


def test_rule_4_a_sentence_citing_the_old_statement_and_its_correction_is_kept() -> None:
    rec = recorded(T2)
    block = rec.find("shipped 4,300 pallets in the third quarter")
    block["text"] = "Samir Vale first said 4,800 pallets, then corrected the figure to 4,300."
    block["citations"][0]["start_block_index"] = 4
    block["citations"][0]["end_block_index"] = 5
    block["citations"].append(dict(block["citations"][0], start_block_index=16, end_block_index=17))

    assert any("then corrected the figure to 4,300" in text for text in kept(run(rec)))


def test_an_uncited_sentence_after_an_abbreviation_is_not_merged_into_the_cited_one() -> None:
    rec = recorded(T1)
    cost = rec.find("The Ellsmoor project cost 310,000 euros")
    cost["text"] = "The Ellsmoor project cost 310,000 euros for sensors, controllers, etc."
    insert_after(rec, "controllers, etc.", " The sensors were later sold off.")

    assert removed(run(rec), "The sensors were later sold off.").reason == "no_citation"


def test_an_uncited_sentence_after_a_single_capital_letter_is_not_merged() -> None:
    rec = recorded(T1)
    rows = rec.find("Those rows went back on the old timers.")
    rows["text"] = "Those rows went back on the old timers, plan A."
    insert_after(rec, "plan A.", " The sensors were later sold off.")

    assert removed(run(rec), "The sensors were later sold off.").reason == "no_citation"


def test_a_cited_block_that_spills_one_word_into_the_next_sentence_lends_it_nothing() -> None:
    rec = recorded(T1)
    block = rec.find("Fertiliser spend is down 11 percent.")
    block["text"] = "Fertiliser spend is down 11 percent. The"
    insert_after(rec, "down 11 percent. The", " growers were furious about it.")

    assert removed(run(rec), "The growers were furious about it.").reason == "no_citation"


def test_a_short_cited_fragment_that_is_a_whole_block_still_counts() -> None:
    # Opus cites fragments as short as two words inside its own sentences ("October 2025").
    # They are whole blocks, so they still lend their citation: the count is unchanged.
    assert len(run(recorded("t1-sentence-opus-medium")).claims) == 13


@pytest.mark.parametrize(
    "changed",
    [
        "zero sensors for two days",
        "a dozen sensors for two days",
        "a couple of hundred sensors for two days",
    ],
)
def test_rule_2_altered_small_number_words_are_checked(changed: str) -> None:
    rec = recorded(T1)
    block = rec.find("knocked out 60 sensors for two days")
    block["text"] = block["text"].replace("60 sensors for two days", changed)

    assert removed(run(rec), changed).reason == "unsupported_number"


def test_rule_2_altered_a_compound_number_word_is_checked() -> None:
    rec = recorded(T1)
    block = rec.find("went from 22 litres")
    kept_text = block["text"].replace("22 litres", "twenty-two litres")
    block["text"] = kept_text
    assert any("twenty-two litres" in text for text in kept(run(rec)))

    block["text"] = kept_text.replace("twenty-two", "twenty-five")
    assert removed(run(rec), "twenty-five litres").reason == "unsupported_number"


def test_rule_2_altered_digits_split_by_a_comma_are_not_read_as_one_number() -> None:
    rec = recorded(T1)
    block = rec.find("knocked out 60 sensors for two days")
    block["text"] = block["text"].replace("60 sensors", "6,0 sensors")

    assert removed(run(rec), "6,0 sensors").reason == "unsupported_number"


@pytest.mark.parametrize("name", ["Émile", "Øresund"])
def test_rule_2_altered_a_name_starting_with_an_accented_letter_is_checked(name: str) -> None:
    rec = recorded(T1)
    block = rec.find("In June a firmware update")
    block["text"] = block["text"].replace("a firmware update", f"a firmware update from {name}")

    unit = removed(run(rec), f"from {name}")

    assert (unit.reason, unit.detail) == ("unsupported_name", [name])


def test_rule_2_altered_a_made_up_name_as_the_first_word_is_checked() -> None:
    rec = recorded(T1)
    block = rec.find("Those rows went back on the old timers.")
    block["text"] = "Zorvane rows went back on the old timers."

    unit = removed(run(rec), "Zorvane rows")

    assert (unit.reason, unit.detail) == ("unsupported_name", ["Zorvane"])


def test_rule_2_real_a_first_word_the_transcript_uses_in_lower_case_is_not_a_name() -> None:
    # "Honestly" is on no list here and is not in the cited sentence; it is an ordinary word
    # because the transcript itself says "honestly" in lower case.
    rec = recorded(T1)
    block = rec.find("cucumber yield was up 4 percent in the sensor blocks.")
    rec.content[rec.content.index(block) - 1]["text"] = " "
    block["text"] = "Honestly cucumber yield was up 4 percent in the sensor blocks."

    assert "Honestly cucumber yield was up 4 percent in the sensor blocks." in kept(run(rec))


def test_a_sentence_of_punctuation_alone_is_not_a_claim() -> None:
    rec = recorded(T1)
    blocks = [
        DraftBlock(text="A headline\n\n"),
        sentence(". . . ! ?", 46, ""),
        sentence(" Fertiliser spend is down 11 percent.", 46, ""),
    ]

    with pytest.raises(TooFewGroundedClaims) as failure:
        ground(blocks, rec.segments, [], rec.title)

    assert len(failure.value.result.claims) == 1


@pytest.mark.parametrize(
    "blocks",
    [
        [],
        [DraftBlock(text="   \n\n  ")],
        [DraftBlock(text="One line and nothing else")],
    ],
)
def test_an_empty_or_one_line_draft_fails_cleanly(blocks: list[DraftBlock]) -> None:
    rec = recorded(T1)

    with pytest.raises(TooFewGroundedClaims) as failure:
        ground(blocks, rec.segments, [Correction(superseded=9999, replaced_by=3)], "")

    assert failure.value.result.headline.source == "title"
