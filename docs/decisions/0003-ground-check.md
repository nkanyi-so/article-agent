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
- the headline must not state as current a figure that a correction superseded: a number that the kept body carries only inside a sentence about the correction does not count.

A headline that passes is stored with the kept sentences that supplied its numbers and names, so the reader can click from the headline to them and on to the transcript. A headline that fails is replaced by the transcript's own title, and the failure is recorded in the trace with its reason. Like a removed sentence, a failed headline is never reworded or patched.

**What the headline check does not show.** It is weaker than a sentence's check, and the README says so. A body sentence carries a pointer the API guarantees is a real span of the transcript. The headline has no pointer of its own: its support is derived by code from the body. The check stops a headline from introducing a number, a date or a name the grounded body does not contain. It does not stop a headline from combining grounded facts into something nobody said ("cuts fertiliser use by a third", when a third was the water). Two things cover that gap: the judge scores the headline against its supporting sentences' cited text like any other claim (J1), and the correction case (E6) checks the headline as well as the body. A headline with no number, date or name passes the code check trivially and rests on the judge alone.

**Why strict.** The claim is "the model added nothing". A connective sentence with no citation may be harmless, but a rule that needs judgement to apply is a rule a model can argue past. Removing too much costs prose quality; keeping too much costs the claim.

**Consequence.**

- The check can fail, and tests show it failing on hand-altered responses.
- Rule 2 is a heuristic: number formats ("12 percent", "12%", "twelve") and capitalised words that are not names need normalising, and it will sometimes remove a true sentence. That direction of error is accepted. The removal rate is an eval metric (E9) so the cost is visible.
- The unit was settled by Phase 1: the sentence (`0012`).
- The headline is the one line of the article whose support is derived and not cited. That is stated wherever the claim is stated.
- Rule 4 depends on extract naming corrections correctly. If it misses one, the judge and the correction case (E6) are the backstop.
- Revisit if the first live run shows a removal rate that leaves articles unreadable: the fix is then a better draft prompt, not a looser rule.
