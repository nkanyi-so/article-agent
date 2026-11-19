# 0014: what the first judged runs showed, the removal ceiling, and what the judge should be shown

**Status:** accepted by the owner on 2026-11-19. Part 1 (the removal ceiling) was set from the first run. In part 2 the owner approved options 1 and 2, asked for every case to be run three times with the gate judged on the means, for both scores to be shown side by side, and for the wrong calibration label to be corrected. All of that is built; the third run is at the end of this record.

**Context.** Phase 6 ran the eval set live twice on 2026-11-19: ten transcripts through the writer and the judge, five inputs that must be refused, and 25 hand-labelled pairs for the judge. Result files: `backend/evals/results/2026-11-19-first.json` and `2026-11-19-second.json`. Every code check (E1 to E8) passed in both runs. The judge's calibration (J2) passed in both. Judged groundedness (J1) failed in both.

| | First run | Second run | Needs |
|---|---|---|---|
| J1 mean over cases | 0.917 | 0.902 | at least 0.90 |
| J1 lowest case | 0.773 (Korvath) | 0.765 (Quillmoor) | at least 0.80 |
| Sentences judged | 172 | 153 | |
| Body sentences judged unsupported | 9 | 9 | |
| Model headlines judged unsupported | 6 of 7 | 7 of 8 | |
| J2 agreement, known negatives failed | 96%, 11 of 11 | 100%, 11 of 11 | 90%, all |
| E9 removed by the ground check | 9 of 174 (5.2%) | 3 of 148 (2.0%) | |
| Spend | $0.67 | $0.64 | |

## Part 1: the removal ceiling (E9)

**Decision.** `REMOVAL_RATE_MAX = 0.10`: an eval run fails if the ground check removes more than one drafted sentence in ten.

**Why 10%.** The first run removed 9 of 174 (5.2%); Phase 4 measured 5.6% on 252. With 174 sentences, a true rate of 5% produces a single run anywhere from about 2% to 8%. A ceiling inside that range would fail on chance; 10% fails only on a real change. The ceiling was set from the first run and before the second, which was held to it (2.0%).

**On transcripts the prompt had never seen:** 3 of 93 (3.2%) in the first run, which is the only run where "never seen" is true: the prompt was edited after reading that run. Two of the three removals were correct catches, not costs. The model wrote "Chair Morag Sewell" and "Chair Bettina Kovac"; nobody in either transcript calls anyone the chair, and the ground check removed both sentences. The third was true: it named the company, which appears only in the title.

## Part 2: what failed, and why the first fix did not work

**What the judge found.** The nine unsupported body sentences in the first run:

- **A bare answer cited without its question: 4.** "He said the full rollout finished in October 2025" cites only `October 2025.` The figures and names are there, so the ground check keeps it, but the cited line alone does not say what happened in October 2025. The question (`When was the full rollout finished?`) is the line before.
- **A role nobody stated in the cited lines: 2.** "operations director Teodor Vance", "head grower Priya Lindqvist".
- **A cause the speaker did not state: 2.** "sent reminders for cancelled appointments, *prompting* 23 complaints".
- **Framing: 1.** "Varga *closed the meeting* by saying".

And six headlines, for a different reason: see below.

**The fix that was tried.** Two rules added to the draft prompt (6 and 7 in `backend/app/pipeline/draft.py`): cite the question as well as a short answer; do not join statements with a cause the speaker did not give. No threshold was touched.

**It did not work.** In the second run the bare-answer class went from 4 to 7, not down. The writer does not reliably cite a question because it is told to. Case scores moved by more between the two runs (Quillmoor 1.00 to 0.76, Fennimore 0.81 to 1.00) than any effect of the prompt: with about 15 sentences a case, one run per case is too noisy to show a small improvement. This is the same lesson as Phase 4: a habit of the writer is not dependably changed by a sentence in the prompt.

**The headlines are a fault in the measure, not in the headlines.** The judge is given, for a headline, the cited lines of its "supporting sentences". The ground check picks those as the kept sentences that share a name or a figure with the headline, which is right for its own job (checking the headline's names and figures) and wrong for this one. "Korvath Greenhouses sensor irrigation cuts tomato water use by about a third" was judged against the one sentence that contains "Korvath Greenhouses", and the judge correctly said those lines mention no water. The sentences about water were in the article and were not shown.

## The options

A trial put the second run's articles to the judge again under two changes (`backend/tools/judge_trial.py`, saved in `trials/phase6/judge-trial.json`, $0.38). It changed nothing in the product.

| What the judge is shown | J1 mean | J1 lowest case | Passes |
|---|---|---|---|
| As specified now | 0.902 | 0.765 | no |
| 1. The question a cited answer replies to, as context | 0.937 | 0.824 | yes |
| 2. A headline against the whole kept article | 0.930 | 0.765 | no |
| 1 and 2 | 0.966 | 0.824 | yes |

The judge's calibration under the trial prompt: 25 of 25, all 11 known negatives failed.

**Option 1: show the question.** When a sentence cites a line that opens a turn, and the turn before ends with a question, the ground stage records that question on the claim as context. The trace shows it beside the cited lines, marked as added by code; the judge is shown it the same way. It is never evidence: it is not used by any ground rule (a figure in a question still cannot support a sentence), and a judge's verdict still has to rest on a cited line.
- *For:* it is found by code, the same way every time, and it is what a reader checking the sentence would look at. It fixes the largest class.
- *Against:* the claim becomes "each sentence points at the lines that support it, read with the question they answer", which is a little weaker than "the cited lines alone". It needs a field on the claim, a change to the spec's wording of J1 and to decision `0003`.
- *What it does not hide:* under options 1 and 2 together, what remains unsupported is all the writer's own: two roles nobody stated in the cited lines, one invented cause, and three headlines that add a comparison or a cause ("missed its on-time target", "cuts missed appointments").

**Option 2: judge the headline against the whole kept article.** The spec already does this for a headline with no name or figure in it; this makes it the rule for every headline.
- *For:* a headline sums up the article, so the fair question is whether the kept article supports it.
- *Against:* it changes the wording of J1 in the spec. On its own it does not pass the gate.

**Option 3: change nothing and try the prompt again.** Rejected as a recommendation: the first attempt moved the wrong way, the measure is too noisy to tune against at this size, and Phase 4 already decided against tuning the prompt on the transcripts it is tested with.

**Option 4: a new ground rule that removes a sentence citing a bare answer without its question.** Stricter, and in keeping with "the doubt goes against the sentence". But code cannot tell which answers need their question ("Two days." does; "We cancelled 14 sailings in October." does not), so it would be a guess by length, and it would remove true sentences. Not recommended.

**Recommended:** options 1 and 2, then one more full run (about $0.65, total about $2.35 of the $3.00 limit) to produce the result file that shows the fix. The two prompt rules stay: they did no harm (removals 2.0%) but there is no evidence they helped, and the write-up will say so.

**What stays true whichever is chosen.** No threshold has been changed. Both result files are kept as they came out. `make check` runs the eval set from the second run's recordings and exits non-zero on J1, so nothing in this phase has been committed.


## What the owner decided, and the third run

**Decided on 2026-11-19.**

1. Options 1 and 2, both. The question must reach the reader exactly as the judge sees it, marked as added by code: it is the claim's `question_segments`, printed by `tools/show_run` and served by the API, and a test holds that the line in the judge's request is the line on the stored claim.
2. Every case is run three times and the gate is judged on each case's mean. No number was changed. As restated: E1 to E7 must pass in every run; E8, J1 and J1-alone take each case as its mean over its three runs; E9 pools the runs; J2 must hold in every run.
3. The measure changing is stated wherever the score is. Every result carries both scores: J1 (each cited answer read with its question) and J1-alone (the cited lines entirely alone, which is what J1 was for the first two runs, except that the headline is now judged against the whole article in both). The README table must show both, and say that the first was introduced after the first two runs failed.
4. The calibration label the judge proved wrong is corrected, with the change and its reason recorded in `backend/evals/calibration.json`. Four pairs were added for the question: two supported only with it, two where only the question says what the sentence says, which must fail.

**How the two scores are produced.** One judge request per run. For each sentence the judge gives two answers: with the context lines, and with them taken away. Code then holds the two together: where no question was shown the two answers are one answer, and a sentence cannot be better supported without its question than with it. The cost of doing it in one request is that the judge has seen the question when it answers "without"; the calibration pairs include three whose two answers differ, and it got all of them right in all three runs.

```
Third run, 2026-11-19: every case run three times. Judged groundedness per case.

                       cited answer read with      cited lines alone,
                       its question (J1, gate)     no question shown (J1-alone)
case                   mean   each run             mean   each run             coverage  removed
korvath-greenhouses    0.906  1.00 0.90 0.82       0.730  0.90 0.70 0.59       0.93      0 of 59
sallowfield-dental     0.928  1.00 0.89 0.89       0.870  0.88 0.83 0.89       0.93      4 of 55
quillmoor-books        0.967  1.00 0.90 1.00       0.808  0.94 0.75 0.73       1.00      0 of 49
hartwell-correction    1.000  1.00 1.00 1.00       1.000  1.00 1.00 1.00       1.00      0 of 35
marrowbeck-ferries     0.949  0.92 0.92 1.00       0.874  0.85 0.85 0.93       1.00      0 of 37
tidewell-kitchens      0.961  1.00 0.94 0.94       0.941  1.00 0.88 0.94       1.00      0 of 47
pennockby-energy       0.951  1.00 0.92 0.93       0.880  0.87 0.85 0.93       1.00      2 of 41
fennimore-print        0.952  1.00 1.00 0.86       0.952  1.00 1.00 0.86       0.90      5 of 47
calderwick-museum      0.963  1.00 0.94 0.95       0.963  1.00 0.94 0.95       1.00      0 of 51
wrenlow-couriers       0.979  1.00 0.94 1.00       0.979  1.00 0.94 1.00       1.00      1 of 47
mean of case means     0.956                       0.900
lowest case mean       0.906                       0.730
single runs            0.82 to 1.00                0.59 to 1.00

E1 to E7 (exact)       pass in all 30 runs; the five refusals correct in all 15
E8 coverage            mean of case means 0.98, lowest 0.90          needs mean >= 0.70    pass
E9 removed             12 of 468 (2.6%)                              needs <= 10%          pass
J1                     mean 0.956, lowest case mean 0.906            needs >= 0.90, none < 0.80   pass
J1-alone               mean 0.900, lowest case mean 0.730            reported, not a gate (it would fail the 0.80 floor)
J2 calibration         87 of 87 answers; 39 of 39 known negatives    needs >= 90%, all     pass
spend                  $2.38, 99 calls
```

**Read plainly.** With the question shown, every case's mean is over 0.90. With the cited lines alone, the mean over cases is 0.900 and one case (Korvath, 0.730) is under the 0.80 floor: on the measure the first two runs were held to, this run would also have failed. The pass comes from the change of measure, not from a change in the writer. What the change buys is that the judge and the reader see what a person checking the sentence would look at; what it costs is that "supported" now means "supported by the cited lines read with the question they answer".

**What the judge still finds unsupported with the question shown: 23 of 484 sentences.** All but two or three are the writer's own additions:

- **A role or title the cited lines do not state: 10.** "Mirela Stanek chaired", "Nadia Brandt chaired" (nobody in either transcript says who chairs: the writer inferred it from who opens the meeting); "operations director Teodor Vance", "head grower Priya Lindqvist", "harbour master Bram Oxley" (said in the transcript, in a line the sentence does not cite).
- **Something the host said, given to the guest: 3.** "Banks said the museum reopens next month" (the interviewer said it, in her introduction).
- **A comparison or arithmetic in a headline that no speaker made: 4.** "output rises", "falls short of target", "about a third".
- **A cause the speaker did not give: 3.** "sent reminders for cancelled appointments, prompting 23 complaints".
- **Not the writer's fault, or arguable: 3.** A question two turns back that the code does not find ("Will you?" answering a question about price, asked two turns earlier); a topic named only in an earlier one-word turn; one sentence the judge read more strictly than I would.

The ground check cannot see any of the first four kinds: they contain no figure or name that is missing from the cited lines. They are what the judge is for, and they are the honest size of the gap between "every name and number is in the cited lines" and "the cited lines say this": about one sentence in twenty-five.

**Removed by the ground check in the third run: 12 of 468 (2.6%).** Six are true sentences lost to the name rule (a clinic, the company or another speaker named where the cited line does not name them). Two more are true and were lost to a capitalised first word ("Told by Kit Varga...") that the name rule took for a name. Four were the writer's own and rightly removed: a title nobody gave ("Chair Morag Sewell"), two summing-up sentences with no citation, and one remark about the transcript's title ("the name comes from no spoken line").

