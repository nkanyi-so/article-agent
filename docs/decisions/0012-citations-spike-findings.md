# 0012: what the citations spike found

**Status:** findings recorded 2026-11-18; **the owner decided its three proposals the same day** (see "The owner's decisions" at the end), and `0003` and the spec now carry them. It proposed no change to `0002` or `0005`. Corrected the same day after the reviewer found a bug in the analysis and several overstated figures (see the Phase 1 log).

**Context.** Phase 1 ran the draft call for real before the design depended on it. Code: `spikes/citations_spike.py`. Every raw request and response: `spikes/results/`. The numbers below come from `python3 spikes/analyze.py`, which reads those files and needs no key (`spikes/results/summary.json`).

**What was run.** 18 billed calls and one unbilled, on 2026-11-18, SDK `anthropic` 2.10.0. Afterwards a depot's name in transcript 2 was changed to an invented one at the owner's request (the original was also a real company's name), and the seven calls that used transcript 2 were run again; their first results were deleted. All transcript 2 figures below are from the second run. 25 billed calls in total:

- 15 draft calls with citations on: `claude-sonnet-5-5` and `claude-opus-5-5`, effort `low` and `medium`, one block per sentence and one per turn, both transcripts, the main variant (Sonnet, medium, per sentence, transcript 1) three times, and one Sonnet call with thinking switched off.
- 2 extract calls (Sonnet, `low`, structured output) and 1 judge call (Opus, `medium`, structured output), added so that the cost of a whole run is measured and not estimated. That is two more billed calls than the "about 16" in the plan.
- 1 request with citations and an output schema together, to confirm the documented 400.

**Spend, from the API's usage figures: $0.55** against an estimate of about $1 and a stop at $3: $0.44 for the first run and $0.12 for the seven re-run calls. The saved results sum to $0.43, because the replaced results ($0.13) are no longer in the tree. Every call ended with `end_turn` and was served by the model requested. No refusal occurred, so what a refusal looks like is still unobserved.

**Limits of this evidence.** Two transcripts, one prompt, at most three repeats. Differences of one or two sentences between variants are noise. The name check used here is a rough stand-in (a capitalised word, with a short list of ordinary sentence-opening words excused), not the Phase 3 rule.

## What citations did

Transcript 1 is 63 turns, 100 sentences, 832 words. Transcript 2 is 18 turns, 32 sentences, 265 words.

| | Sonnet medium, per sentence (3 runs, t1) | Sonnet low (t1) | Opus medium (t1) | Sonnet medium (t2) | Opus medium (t2) |
|---|---|---|---|---|---|
| Thinking tokens used | 0, 0, 0 | 0 | 481 | 0 | 490 |
| Article words | 311, 331, 325 | 311 | 355 | 191 | 222 |
| Cited text blocks | 22, 23, 22 | 23 | 21 | 10 | 16 |
| Share of words in uncited blocks | 17%, 5%, 16% | 33% | 47% | 14% | 54% |
| Headline cited | no, no, no | no | no | no | no |
| Cited blocks holding more than one sentence | 0, 0, 0 | 0 | 0 | 0 | 0 |
| Widest citation, in blocks | 2 | 2 | 1 | 2 | 1 |
| Cited text per block, mean / longest (words) | 15 / 27, 15 / 27, 17 / 32 | 14 / 19 | 13 / 20 | 15 / 22 | 10 / 18 |
| Cost | $0.021 each | $0.021 | $0.051 | $0.011 | $0.034 |
| Latency | 6.8 s, 6.7 s, 7.5 s | 6.6 s | 12.9 s | 4.2 s | 10.5 s |

1. **Citations and thinking combine, as far as it was seen: on Opus at `medium` only.** There a thinking block and cited text blocks came back in the same response, on both transcripts (four calls). Opus at `low` used no thinking tokens. Sonnet, the proposed writer, accepted the adaptive-thinking setting and used no thinking tokens at `low` or `medium` in any of its nine calls, so the combination was never seen on the writer. For the same reason the Sonnet call with thinking switched off shows nothing: it is compared against calls that did not think either.
2. **Pointers are tight and valid.** Every citation was a real block range. No citation spanned more than two blocks. Cited text per block averaged 10 to 19 words across the 15 drafts and never exceeded 32.
3. **A cited block is usually part of a sentence, not a sentence.** The typical shape is an uncited lead-in followed by a cited clause: `Operations director Teodor Vance said ` (uncited) then `tomato water use went from 22 litres per kilo of fruit to 15 litres.` (cited). Sonnet cites whole clauses; Opus cites short fragments inside its own prose, which is why half of its words sit in uncited blocks. A cited block held at most two sentences, and that only in 3 of the 15 drafts, all Opus; in the other 12 no cited block held more than one.
4. **The headline was never cited:** 0 of 15.
5. **A whole sentence with no citation is rare.** Counting sentences instead of blocks: Sonnet at `medium` produced 0 or 1 uncited sentence per article (the one that recurs is a bridge such as "The two differ on yield."); Opus produced 0 to 3.
6. **Quotations were verbatim:** 6 quoted spans across the 15 drafts, all exact substrings of their cited text. Opus twice altered cited wording in brackets (`grow[s]`), outside quotation marks.
7. **The corrected figure was handled correctly in all six drafts of transcript 2.** Each reported 4,300 as the fact. Where 4,800 appeared it was as the earlier figure or the forecast. The extract call named the correction on its own: segment 4 superseded by segment 16.
8. **Per sentence against per turn.** On these transcripts there is no measurable difference in how tight the spans are, because turns are short (1.6 sentences a turn): the longest cited text was 31 words per turn against 27 to 32 per sentence. A transcript with long turns was not tried. Per sentence cost 23% more input tokens (4,886 against 3,965), about $0.002 a call. What per sentence does cost is in the next section.
9. **Citations and an output schema together:** HTTP 400, `Citations cannot be enabled when output format is set. Please disable citations on uploaded document blocks.` Not billed.
10. **Output tokens.** A 311-word article used 1,089 output tokens with no thinking, roughly two and a half times what the prose alone would need. The documentation says the quoted `cited_text` is not counted; the citation structure evidently is. This is an inference from the totals, not a documented figure.
11. **Runs differ.** The three identical requests gave three different articles under one identical headline. Sampling settings cannot be set, so determinism has to come from recordings, as `0004` assumes.

## What a strict ground check would do to these drafts

With the **sentence** as the unit. This table applies two of the four rules in `0003`, and roughly: rule 1 (the sentence overlaps at least one cited block) and rule 2 (every number, and every capitalised word taken as a name, appears in the sentence's cited text; dates through their digits only). Rule 3 was measured separately (finding 6). Rule 4 is not in the table; the transcript 2 drafts were read by hand for it.

| | Sentences | No citation | Fail numbers | Fail names | Kept | Words kept |
|---|---|---|---|---|---|---|
| Sonnet medium, per sentence, t1 (3 runs) | 22, 23, 22 | 1, 1, 1 | 1, 0, 0 | 2, 2, 2 | 18, 20, 19 | 80%, 86%, 87% |
| Sonnet low, per sentence, t1 | 16 | 1 | 0 | 2 | 13 | 80% |
| Sonnet medium, per turn, t1 | 24 | 1 | 0 | 2 | 21 | 87% |
| Opus medium, per sentence, t1 | 20 | 3 | 1 | 3 | 13 | 67% |
| Opus low, per sentence, t1 | 17 | 3 | 2 | 3 | 11 | 66% |
| Opus medium, per turn, t1 | 18 | 0 | 0 | 1 | 17 | 90% |
| Sonnet medium, per sentence, t2 | 10 | 0 | 0 | 1 | 9 | 92% |
| Sonnet low, per sentence, t2 | 13 | 0 | 0 | 2 | 11 | 86% |
| Sonnet medium, per turn, t2 | 11 | 0 | 0 | 1 | 10 | 85% |
| Opus medium, per sentence, t2 | 12 | 1 | 0 | 3 | 8 | 69% |
| Opus low, per sentence, t2 | 10 | 0 | 0 | 2 | 8 | 75% |
| Opus medium, per turn, t2 | 16 | 2 | 0 | 4 | 10 | 53% |

No article is gutted, and none comes near the three-sentence floor. But the sentences removed from the Sonnet drafts are nearly all **true**, and they fail for one reason: with one block per sentence, a fact and the thing it is about sit in different blocks, and the model cites only one of them.

- "Korvath Greenhouses began an irrigation pilot in March 2025..." cites "We started in March 2025 with a pilot in one block." The company's name is in another sentence, and in the title.
- "Korvath plans the same system at Farrow Bank in spring 2026" cites "We plan to install the same system there in spring 2026." "Farrow Bank" is the sentence before.
- "...since the full rollout finished in October 2025" cites "Every block at Ellsmoor has been on sensors since then."

The judge saw the same thing. Asked whether each of the 22 cited claims in one Sonnet draft is supported by its cited text alone, Opus said no to four: those three, and "Ellsmoor has 420 sensors", whose cited text is "Across Ellsmoor, 420." with the word "sensors" in the question before it. That is 18 of 22, or 0.82, under the 0.90 the spec asks for. After the ground check removes the three that fail its own rules, one judged-unsupported claim remains among the survivors, about 0.95. One judge call on one draft: an indication, not a measurement.

## Each assumption, confirmed or changed

### `0002` citations for the draft

| Assumption | Verdict |
|---|---|
| Citations and thinking can be used together (the record calls this inference) | **Confirmed on Opus at `medium` only** (four calls). Never observed on Sonnet, the writer, which did not think at `low` or `medium`. |
| A custom content document with one block per sentence; the citation's block indexes map straight onto segments | **Confirmed.** |
| No output schema on the draft call; sending both returns a 400 | **Confirmed**, message recorded above. |
| The speaker's name at the start of each block lets the model attribute | **Confirmed.** Attributions named the right speaker, and the name is inside `cited_text`, so the "speaker of a cited segment" part of rule 2 needs no lookup. |
| Per sentence gives spans tight enough for the number and name check | **Confirmed for numbers** (0 or 1 failure per draft). **Changed for names and dates:** the span is so tight that the referent is often outside it. See the proposal below. |
| "If the uncited share is high enough that articles are gutted, this record is rewritten" | **Not triggered**, provided the unit is the sentence. With the block as the unit it would be: 5% to 33% of Sonnet's words and about half of Opus's are in uncited blocks. |
| The transcript goes in as one block per sentence (the owner's answer to Q3), because per turn "a cited span can be a paragraph long, too loose" | **The decision stands as the owner's answer; its stated reason was not borne out here.** With turns this short, spans were as tight per turn as per sentence, and Sonnet kept a similar share of words either way (87% and 85% per turn, 80% to 92% per sentence). The reason would bite on a transcript with long turns, which was not tried. Untested, not disproved. |
| `cited_text` does not count toward output tokens | **Not contradicted, but the overhead is real:** output tokens were about two and a half times what the prose needs (finding 10). |
| Stages that need a schema are separate calls with no citable document | **Confirmed:** extract and the judge returned valid structured output with no document block; the combination returns a 400. |
| No stated limit on the number of blocks | **Confirmed up to 100 blocks.** |

### `0003` the ground check

| Assumption | Verdict |
|---|---|
| What counts as a unit "is settled by Phase 1" | **Settled: the sentence**, assembled from the response's text blocks. A sentence is kept if at least one of its blocks is cited and the whole sentence passes rules 2 to 4 against the union of its cited text. A block cannot be the unit: it is a fragment, and removing uncited blocks would delete every "Vance said". |
| Rule 1, at least one citation | **Confirmed** with the sentence as unit. Bridge sentences ("The two differ on yield.") are removed, as designed. |
| Rule 2 is a heuristic that "will sometimes remove a true sentence" | **Confirmed, and more often than "sometimes":** two or three true sentences per article on transcript 1, usually including the one that names the company. |
| Rule 3, quotations verbatim | **Confirmed** as checkable: 10 of 10 were exact. |
| Rule 4, not resting only on a corrected segment | **Not exercised by a real response; needs a hand-altered fixture in Phase 3.** In the saved transcript 2 drafts no sentence rests on the superseded segment alone: the old figure appears in an uncited lead-in ("He had first given a figure of 4,800, but") inside a sentence whose cited clause is the correction. That is one more reason the unit is the sentence: per block, that lead-in is just uncited text. |
| Rule 4 "depends on extract naming corrections correctly" | **Confirmed twice on one transcript:** in both runs extract named segment 4 as superseded by segment 16. |
| "Revisit if the removal rate leaves articles unreadable: the fix is then a better draft prompt, not a looser rule" | **Not triggered:** nothing here is unreadable. It bears on proposal 2 below, where option (b) is a looser rule. |
| "The same rules apply to the headline; a failed headline is replaced by the transcript's own title and recorded" | **Changed.** No headline was cited in 15 drafts, so as designed every run would fall back to the title and record a headline failure. See the proposal below. |
| Fewer than three surviving units fails the run | **Confirmed** as a sane floor: the worst draft kept 8. |

### `0005` models

| Assumption | Verdict |
|---|---|
| Writer `claude-sonnet-5-5` | **Confirmed.** At `medium` Opus cost 2.5 to 3.2 times as much and took two to two and a half times as long; at `low`, 1.8 to 1.9 times as much and 10% to 25% longer. Opus cited fragments, leaving more for the ground check to remove: across its six drafts it kept 53% to 90% of words, against 80% to 92% across Sonnet's nine. |
| Draft effort `medium`; "Phase 1 measures the difference" | **Confirmed, with no measured difference in cost:** `low` and `medium` cost the same ($0.021) and kept the same share at sentence level. `medium` put fewer words in uncited blocks. Nothing is saved by going lower. |
| Extract effort `low` | **Confirmed** as workable: valid structured output both times, the correction and the disagreement both named. |
| Judge `claude-opus-5-5` at `medium` | **Confirmed** as workable: one valid structured verdict per claim, and it caught real gaps. |
| Thinking is on for these models | **Confirmed for Opus at `medium` only.** Opus at `low` and Sonnet at both levels accepted the setting and used none. |
| No sampling parameters | **Confirmed** by consequence: three identical requests, three articles. |
| Timeout 60 seconds per call, 240 seconds per run | **Confirmed with room:** the slowest call took 12.9 s; extract, draft and judge on transcript 1 total about 27 s. |
| A refusal, a `max_tokens` stop and a model mismatch are typed errors; no fallback model | **Neither confirmed nor changed: unverified.** None occurred in 25 calls, so the spike has nothing to say. Carried to Phase 4, which builds those errors and must test them against hand-built responses. |
| Cost per run "is measured in Phase 1" | **Measured**, below. |

## Cost

Per call, from usage. Prices: Sonnet $2 and $10, Opus $4 and $20 per million input and output tokens.

| Call | Transcript 1 (100 sentences) | Transcript 2 (32 sentences) |
|---|---|---|
| Extract, Sonnet `low` | $0.017 (3,451 in, 1,041 out) | $0.008 |
| Draft, Sonnet `medium`, per sentence | $0.021 (4,886 in, about 1,100 out) | $0.011 |
| Judge, Opus `medium` | $0.033 (2,356 in, 1,171 out) | not run; smaller |
| **One run** | **$0.071** | under $0.04 |

- **One live run of the pipeline:** about 7 cents for a transcript of this size, of which the judge is 46%.
- **One live eval run** of the twelve-case set: about **$0.60**, estimated from these figures and not yet run: eight cases that reach the judge at up to $0.071, one `no_checkable_facts` case at one extract call, three refused in code for nothing, and the judge calibration pairs in one or two judge calls. The plan guessed $3 to $5.
- **Recording the three seeded transcripts:** about $0.20.
- The hosted demo costs nothing: it replays recordings.

**The cheapest setup that does not weaken the eval** is the one already proposed: Sonnet writes (extract at `low`, draft at `medium`), Opus judges at `medium`. A cheaper writer setting buys nothing, because `low` costs the same. The only real saving left is the judge. The judge has to be a different model from the writer, so the candidates are Opus at `low` (saves the thinking, roughly a cent a run) or `claude-haiku-5-5` (well under a cent). Neither is known to be as good a judge, and a weaker judge is exactly what would weaken the eval. The calibration set (J2) is the test for that: either may replace Opus `medium` only after passing it. At $0.60 an eval run, the saving on offer is about 25 cents.

## Proposed changes, for the owner

1. **`0003` and the spec: the unit is the sentence.** Stated above. This fills a gap the record left open; it changes no rule.
2. **`0003` rule 2: decide what a name or date may be checked against.** As written, cited text and cited speakers only. Options:
   - (a) Leave it. Two or three true sentences are removed per article, typically the lead. Strictest, and the removed list shows real removals on every run.
   - (b) Also accept names that appear in the transcript's title, which is input the pipeline was given, not something the model wrote. On these drafts that keeps the company-name sentences (Sonnet, transcript 2: 9 of 10 kept becomes 10 of 10). It does not help "Farrow Bank" or "October 2025". **This is a looser rule, and `0003` says the fix for a high removal rate is a better prompt, not a looser rule.** Choosing it is a knowing departure from that sentence.
   - (c) Ask the model, in the draft prompt, to cite every sentence it drew on, including the one that names the subject. Untested; a prompt change and a few cents to try in Phase 4. This is the fix `0003` itself points to.
   - Recommended: (a) now and (c) in Phase 4, measured before it is relied on; (b) only if the owner wants it after seeing (c)'s numbers. Not recommended at all: letting a name pass because it appears anywhere in the transcript, which would stop the check from failing.
3. **`0003` and the spec: the headline.** Options:
   - (a) Keep the design. Every run records a headline failure and shows the transcript's title.
   - (b) Do not ask for a headline. The article always carries the transcript's own title, and the spec's sentence about the headline goes. Simplest and honest.
   - (c) Ask for the headline as an ordinary first sentence that must be cited. Untested.
   - Recommended: (b). The claim is about grounding, not headlines, and a failure recorded on every run teaches the reader to ignore the removed list.
4. **The judged threshold (J1) is not changed.** The 0.82 above is on a draft before the ground check and is one call. It is recorded here because it is the likeliest first real failure in Phase 6, which the plan wants.
5. **The plan's estimates** for Phases 4 and 6 can come down to about $0.20 and about $0.60 a run. The stops stay where they are.

**Consequence.** `0002` and `0005` stand as written, with two caveats recorded above: the reason given for one block per sentence was not borne out on transcripts with short turns, and the three typed model errors are unverified. `0003` needed the unit stated and two decisions (names, headline) before Phase 3 builds the ground check; all three have since been decided (below). The saved responses in `spikes/results/draft/` become Phase 3's first fixtures: they already contain an uncited sentence, a name outside its cited text, a date outside its cited text, and a sentence that mentions a superseded figure correctly inside a sentence citing its correction.

## The owner's decisions, 2026-11-18

1. **The unit is the sentence.** Accepted. Written into `0003` and the spec.
2. **The name rule stays strict** (option a). The prompt change (option c: ask the model to cite every sentence it drew on) is tried and measured in Phase 4. Accepting names from the title (option b) is not adopted.
3. **The headline: not the record's recommendation.** The owner does not want the transcript's title as the article's headline. Decided instead: the model writes a headline, which is checked against the article body that has already passed the ground check; if it fails, the article takes the transcript's title and the failure is recorded in the trace. What that check can and cannot show is set out in `0003`.
4. **The gate's wording:** "unverified, carried to Phase 4" is accepted for the three typed model errors.
5. **The depot's name in transcript 2** was changed and its calls re-run, as recorded at the top.

