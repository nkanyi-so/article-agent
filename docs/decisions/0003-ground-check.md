# 0003: remove and record, never patch

**Status:** proposed, 2026-11-18

**Context.** In the old project, a claim whose source id was invalid had the id stripped and was then given the angle's sources instead. Every claim therefore always had a citation on paper, and the structural eval could never fail. The API's citation guarantee (`0002`) covers pointers only: not that every sentence has one, and not that the span supports the sentence.

**Decision.** A code stage, `ground`, sits between the draft and anything shown or stored as the article. A unit of the draft is kept only if:

1. it carries at least one citation;
2. every number, date and proper name in it appears in its cited text, or is the speaker of a cited segment;
3. anything in quotation marks is a verbatim substring of its cited text;
4. it does not rest only on a segment that a later statement corrected, as named by extract.

A unit that fails is removed and stored with its text and the reason. It is not re-cited, reworded or kept with a warning. If fewer than three units survive, the run fails with `too_few_grounded_claims`. The same rules apply to the headline; a failed headline is replaced by the transcript's own title and recorded.

**Why strict.** The claim is "the model added nothing". A connective sentence with no citation may be harmless, but a rule that needs judgement to apply is a rule a model can argue past. Removing too much costs prose quality; keeping too much costs the claim.

**Consequence.**

- The check can fail, and tests show it failing on hand-altered responses.
- Rule 2 is a heuristic: number formats ("12 percent", "12%", "twelve") and capitalised words that are not names need normalising, and it will sometimes remove a true sentence. That direction of error is accepted. The removal rate is an eval metric (E9) so the cost is visible.
- What counts as a unit (one cited text block, or a sentence within it) is settled by Phase 1.
- Rule 4 depends on extract naming corrections correctly. If it misses one, the judge and the correction case (E6) are the backstop.
- Revisit if the first live run shows a removal rate that leaves articles unreadable: the fix is then a better draft prompt, not a looser rule.
