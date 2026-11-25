# 0010: eval plan and starting thresholds

**Status:** proposed, 2026-11-18

**Context.** The old project had no real eval result: the committed run used no judge, the harness had no thresholds and exited 0 when every row failed, the default mode was paid, and the judge was the writer's own model. What was sound was the shape: code checks wrapped around a model judge, so the judge could not lift a claim that failed a code check. I decided to keep the earlier draft's thresholds as a starting point and to make the set harder if the first live run passes everything.

**Decision.** The eval plan, set out in full in [`docs/EVALS.md`](../EVALS.md). The parts that are choices:

- **Kept from the earlier draft:** structural validity 1.00; 100% of stored claims cite an existing segment; 100% of numbers, dates and names appear in the cited text; judged groundedness mean at least 0.90 with no case under 0.80; the corrected-number, contradiction, injection-with-canary and must-refuse cases.
- **Added, because without them the set can be passed by doing nothing:**
  - Coverage (E8). An article of one safe sentence would pass every grounding check. Each case lists by hand the segments a fair article must touch.
  - Refusals in both directions (E5). A pipeline that refuses everything would pass a refusal-only check.
  - Removal rate (E9), reported first and given a ceiling from the first live run, so the cost of the strict ground check is visible.
  - Judge calibration (J2): about 24 hand-labelled pairs with known negatives. Without it, a judge that says "supported" to everything scores 1.00.
  - Two baseline tests: a hand-built perfect run passes, an empty article fails.
- **Expected values are written by hand,** never taken from a model's output, so the eval does not reward imitating the model under test.
- **Plumbing failures are not wrong answers.** A timeout, an API error, a truncated response and a model refusal are recorded as their own outcome.
- **The default mode is free and enforced.** Fixture mode runs in `make check` with thresholds and a non-zero exit. The live run is a separate command that asks first.
- **The judge** is a different model from the writer (`0005`), gets the claim and its cited segments as delimited data, returns a structured verdict, and is clamped in code: a claim that failed a code check is never sent, and a verdict cannot name segments the claim did not cite.

**What the numbers can and cannot show.** Twelve cases and one run is a small sample: a pass-rate difference smaller than roughly one case in four is noise. The table in the README is evidence that the checks can fail and were made to pass honestly, not a benchmark. If a change needs finer resolution, add cases or repeats first.

**Consequence.** The untested thresholds (coverage 0.70, the judged pair) may prove wrong in either direction. They are changed only by a new decision record with the run that justifies it, never to make a check pass. If the first live run passes everything, harder cases are added until something fails; that failure and its fix are the "one real failure" the README needs.
