# 0003: remove and record, never patch

**Status:** accepted by the owner on 2026-11-18, with the unit and the headline rule settled after the Phase 1 spike (`0012`).

**Context.** In the old project, a claim whose source id was invalid had the id stripped and was then given the angle's sources instead. Every claim therefore always had a citation on paper, and the structural eval could never fail. The API's citation guarantee (`0002`) covers pointers only: not that every sentence has one, and not that the span supports the sentence.

**Decision.** A code stage, `ground`, sits between the draft and anything shown or stored as the article.

**The unit is the sentence.** The draft response is a run of text blocks, some cited and some not, and a block is usually part of a sentence: an uncited lead-in ("Vance said") followed by a cited clause (`0012`). The ground stage joins the blocks, splits the body into sentences, and gives each sentence the citations of every block it overlaps. The sentence is checked against the union of that cited text.

A sentence is kept only if:

1. it carries at least one citation, that is, at least one of its blocks is cited;
2. every number, date and proper name in it appears in its cited text, or is the speaker of a cited segment;
3. anything in quotation marks is a verbatim substring of its cited text;
4. it does not rest only on a segment that a later statement corrected, as named by extract.

A sentence that fails is removed and stored with its text and the reason. It is not re-cited, reworded or kept with a warning. If fewer than three sentences survive, the run fails with `too_few_grounded_claims`.

**Rule 2 stays strict.** A name or a date is checked against the sentence's own cited text and cited speakers, nothing else: not the title, not the rest of the transcript. The spike showed this removes two or three true sentences per article, usually because the subject is named in a neighbouring block the model did not cite. The answer is a better draft prompt (ask the model to cite every sentence it drew on), tried and measured in Phase 4, not a looser rule.

**The headline.** The model writes a headline as the first line of the draft. The spike found it is never cited (0 of 15), so it cannot be held to rule 1. It is checked instead against the article body **after** the body has passed the rules above:

- every number, date and proper name in the headline must appear in a kept sentence;
- anything in quotation marks in the headline must appear verbatim in a kept sentence;
- no number in the headline may appear in the text of a segment that extract named as superseded. This is deliberately blunt, because code cannot tell what a sentence is "about": in the spike's drafts the old figure sits in a kept sentence that cites only the correction ("He had first given a figure of 4,800, but corrected himself"), so "appears in a kept sentence" alone would let a headline state the old figure. The blunt rule also rejects a correct headline that reuses a still-true number from a superseded segment; that direction of error is accepted, and the fallback is the title.

A headline that passes is stored with the kept sentences that supplied its numbers and names, so the reader can click from the headline to them and on to the transcript. A headline that fails is replaced by the transcript's own title, and the failure is recorded in the trace with its reason. Like a removed sentence, a failed headline is never reworded or patched.

**What the headline check does not show.** It is weaker than a sentence's check, and the README says so. A body sentence carries a pointer the API guarantees is a real span of the transcript. The headline has no pointer of its own: its support is derived by code from the body. The check stops a headline from introducing a number, a date or a name the grounded body does not contain. It does not stop a headline from combining grounded facts into something nobody said ("cuts fertiliser use by a third", when a third was the water). Two things cover that gap: the judge scores the headline against its supporting sentences' cited text like any other claim (J1), and the correction case (E6) checks the headline as well as the body. A headline with no number, date or name passes the code check trivially and rests on the judge alone; its supporting set is then the whole kept body, which is what the judge is given. A fallback title is not scored by the judge: it is input the pipeline was given, not something the model wrote.

**Why strict.** The claim is "the model added nothing". A connective sentence with no citation may be harmless, but a rule that needs judgement to apply is a rule a model can argue past. Removing too much costs prose quality; keeping too much costs the claim.

**Consequence.**

- The check can fail, and tests show it failing on hand-altered responses.
- Rule 2 is a heuristic: number formats ("12 percent", "12%", "twelve") and capitalised words that are not names need normalising, and it will sometimes remove a true sentence. That direction of error is accepted. The removal rate is an eval metric (E9) so the cost is visible.
- The unit was settled by Phase 1: the sentence (`0012`).
- The headline is the one line of the article whose support is derived and not cited. That is stated wherever the claim is stated.
- Rule 4 depends on extract naming corrections correctly. If it misses one, the judge and the correction case (E6) are the backstop.
- Revisit if the first live run shows a removal rate that leaves articles unreadable: the fix is then a better draft prompt, not a looser rule.

**As built in Phase 3.** What the rules mean in code (`backend/app/pipeline/ground.py`). Where a choice had to be made, the doubt goes against the sentence.

- **Sentence:** the draft's text blocks joined and split at `.`, `?` or `!` followed by white space. Nothing inside balanced double quotation marks ends a sentence, so a two-sentence quotation stays whole; if the marks do not balance they are ignored. An abbreviation's full stop ends a sentence when a capital follows ("etc. The"), except after a title ("Dr. Okonta"). A sentence of punctuation alone is dropped.
- **Citations of a sentence:** those of every cited block it overlaps, where the overlap is the whole block or at least three words. A block that spills a word or two into the next sentence lends that sentence nothing.
- **Invalid citation:** a citation pointing outside the transcript removes its sentence with the reason `invalid_citation`, and the range is checked before it is used. The API promises this cannot happen; a recording edited by hand could do it.
- **Number:** a run of digits (commas only where they group thousands), or a number word: zero, two to ninety-nine, couple, dozen, hundred, thousand, million, billion. Digits and words match each other.
- **Name:** a capitalised word, accented letters included, that is not on a short list of ordinary words. A sentence's first word is a name unless the transcript itself uses that word in lower case. Months and weekdays are names, which is how a date is checked beyond its digits. A name must appear in the text of a cited segment or be its speaker.
- **A first name and its speaker (added in Phase 4 by the owner's decision, `0013`).** If a name is not in the cited text, it still stands when it is the surname of a speaker whose first name is written as a name in a cited sentence and can only mean that speaker. "Hana, run the calls" supports "Olund" when the only speaker called Hana is Hana Olund. It supports nothing when two speakers share the first name; when the first name is also a word of another speaker's label; when the transcript also uses it as an ordinary word ("will") or it is a month or a weekday ("June"); when it matches no label; or when it only opens a sentence without being a form of address ("Will do."). Each use is recorded on the kept sentence. **Limits, stated plainly:** it assumes the Hana who is spoken to is the Hana who speaks, so a different Hana who is mentioned but never speaks would be taken for the speaker; every word of a label after the first counts as a surname; and what the sentence says about the person is not checked.
- **Quotation:** text in double quotation marks or guillemets, compared ignoring case, spacing and trailing punctuation. It must sit inside one stretch of what one person said without interruption: consecutive cited segments of the same turn. Words from two speakers, or from two separate moments, cannot be stitched into one quotation. A quotation mark that is never closed removes the sentence, since it cannot be checked.
- **Rule 4, made stricter in the build (for the owner to confirm).** As decided, a sentence fails if it rests only on superseded segments. The reviewer showed that citing one neighbouring segment as well ("Sure.") was enough to keep a sentence stating the old figure. So, in addition: when a sentence cites a superseded segment beside others, every number in it must appear in one of the others. The real sentence "He had first given a figure of 4,800, but corrected himself" still passes, because the correcting segment says "not 4,800".
- **Source of truth:** the transcript's own segments at the cited indexes, not the copy of the cited text inside the response.

**The question a cited answer replied to (added in Phase 6, `0014`, approved by the owner on 2026-11-19).** For each kept sentence the ground stage records `question_segments`: for every cited line that opens a turn, the last line of the turn before, when that line ends with a question mark and is not itself cited. `Two days.` says nothing without `How long was it off the road?`, and the first two judged runs showed the writer citing the answer alone in 11 of 325 sentences. The question is found by code, the same way every time; it is shown to the reader beside the cited lines, marked as added by code, and to the judge in the same form. **It is not a citation and not evidence.** None of the four rules reads it: a figure or a name in a question supports nothing, because an answer need not agree with its question (an altered-copy test holds this). It does not rescue a sentence that failed: it is recorded only on sentences that already passed. Its limits: it finds only the question directly before the answer's turn, so a question two turns back, or a statement that an answer leans on, is not found; and it is added whether or not the sentence needs it.

**What the code does not check,** so that nobody reads silence as a pass. These rest on the judge:

- Meaning. "Ellsmoor has 420 sensors" passes on "Across Ellsmoor, 420." And a right number with the wrong unit passes: "two days" against "a couple of weeks".
- "One", ordinals ("the second of June"), fractions and multiples in words ("a third", "half", "twice", "double").
- A name written in lower case, and a capitalised ordinary word found in the cited text in lower case.
- Quotations in single quotation marks, which cannot be told from apostrophes.
- Who a pronoun refers to. "He said a tank is being built", after a sentence about someone else, passes if its own citation is of the right speaker; the reader may take "he" for the wrong person. The verifier found one in a recorded seed.
- A sentence with no number, name or quotation: it passes on having a citation.
- A cited block that spills three or more words into a following uncited sentence lends it its citation. The sentence's numbers and names are still checked against that cited text.
- A superseded segment's claim restated with no number in it, cited beside another segment.
- The headline: grounded facts combined into something nobody said (above).
- Speaker labels the parser misses or invents. A label of more than four words, or one in lower case, is read as a continuation of the turn before it, and a line such as "Note: ..." is read as a speaker called Note. Since a cited segment's speaker counts as support for a name, a wrong label can let a wrong attribution through.

**Measured again in Phase 4 (`0013`):** with the draft prompt rewritten to tell the model how it is checked, and the first-name rule, 14 of 252 sentences were removed across 15 runs on four transcripts (5.6%, plausibly 3% to 9%), against 17.1% before. All removed sentences are true.

**Measured on the eleven recorded drafts:** 40 of 186 sentences removed, all of them true; 28 because a subject, date or figure sits in a neighbouring block the model did not cite. Every model headline was rejected for the same reason. Both are what the Phase 4 prompt change is for. The stricter rules added after the review changed none of these numbers.
