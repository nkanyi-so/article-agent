# 0013: fixing over-removal with the draft prompt and one narrow rule

**Status:** accepted by the owner on 2026-11-19, after the Phase 4 trial.

**Context.** Phase 3 built the ground check and measured its cost: on real drafts it removed about one true sentence in six, every article lost its lead, and most model headlines were rejected. One cause: with one citable block per transcript sentence, a fact and the name it is about often sit in different blocks, and the model cited only the block with the fact. The owner's instruction for Phase 4: fix it with the draft prompt, do not loosen the check to get there, measure over repeated runs, and if the prompt alone falls short, stop and bring options. The bar: the lead survives, the model's headline is accepted on most runs, true sentences removed drop to roughly one in twenty or better, and every altered-copy test is still caught.

**What was measured.** `backend/tools/prompt_trial.py`: live calls, `claude-sonnet-5-5` at medium effort, three runs per transcript per prompt, on four transcripts (the three seeds and the short correction transcript). Each run is the real extract and draft stages followed by the real ground check. Every request and response is saved under `trials/phase4/`; `cd backend && uv run --locked python -m tools.trial_report` reproduces everything below with no key.

With the ground check as it now stands (including the first-name rule below):

```
baseline: 12 runs, 216 sentences, 34 removed (15.7%), lead kept in 3 of 12, model headline accepted in 5 of 12, draft cost $0.0177 a run
cite-all: 12 runs, 203 sentences, 12 removed (5.9%), lead kept in 10 of 12, model headline accepted in 6 of 12, draft cost $0.0177 a run
cite-all-2: 12 runs, 205 sentences, 13 removed (6.3%), lead kept in 11 of 12, model headline accepted in 11 of 12, draft cost $0.0186 a run
cite-all-3: 12 runs, 195 sentences, 1 removed (0.5%), lead kept in 12 of 12, model headline accepted in 12 of 12, draft cost $0.0189 a run
neutral: 12 runs, 197 sentences, 10 removed (5.1%), lead kept in 11 of 12, model headline accepted in 11 of 12, draft cost $0.0188 a run
```

- `baseline` is the Phase 1 prompt.
- `cite-all`, `cite-all-2` and `cite-all-3` are three rounds of a prompt that explains the check to the model; each round was written from what the round before still lost.
- `cite-all-3` looked like a win, and is rejected: **its worked examples were taken from the seeded transcripts** ("Farrow Bank", "Abbey Row", "Hana"). That is tuning the prompt on the test.
- `neutral` is the same prompt with every name and noun in its examples replaced, so that no prompt contains anything from a test transcript. It is the prompt in the code. **Its examples are still the seed examples in disguise:** "Still one person short" answering "And Abbey Row reception?" became "Still two drivers short" answering "And the north depot?"; "Hana, run the calls in November" became "Marta, send the figures by Friday"; and so on for all five. The situations the prompt warns about were chosen by looking at these transcripts.

Before and after, run by run:

```
variant | run | sentences | kept | uncited | number | name | other | lead kept | headline
baseline | hartwell-correction-1 | 12 | 11 | 0 | 0 | 1 | 0 | NO | title (name)
baseline | hartwell-correction-2 | 11 | 10 | 0 | 0 | 1 | 0 | NO | title (name)
baseline | hartwell-correction-3 | 12 | 11 | 0 | 0 | 1 | 0 | NO | title (name)
baseline | korvath-greenhouses-1 | 21 | 18 | 1 | 0 | 2 | 0 | NO | title (name)
baseline | korvath-greenhouses-2 | 20 | 16 | 1 | 0 | 3 | 0 | NO | title (name)
baseline | korvath-greenhouses-3 | 22 | 19 | 1 | 0 | 2 | 0 | NO | title (name)
baseline | quillmoor-books-1 | 20 | 16 | 1 | 0 | 3 | 0 | yes | model
baseline | quillmoor-books-2 | 19 | 16 | 1 | 0 | 2 | 0 | yes | model
baseline | quillmoor-books-3 | 20 | 17 | 1 | 0 | 2 | 0 | yes | model
baseline | sallowfield-dental-1 | 20 | 15 | 1 | 3 | 1 | 0 | NO | model
baseline | sallowfield-dental-2 | 19 | 17 | 0 | 0 | 2 | 0 | NO | model
baseline | sallowfield-dental-3 | 20 | 16 | 2 | 0 | 2 | 0 | NO | title (name)
neutral | hartwell-correction-1 | 12 | 12 | 0 | 0 | 0 | 0 | yes | model
neutral | hartwell-correction-2 | 12 | 12 | 0 | 0 | 0 | 0 | yes | model
neutral | hartwell-correction-3 | 13 | 13 | 0 | 0 | 0 | 0 | yes | model
neutral | korvath-greenhouses-1 | 18 | 17 | 0 | 0 | 1 | 0 | NO | title (name)
neutral | korvath-greenhouses-2 | 19 | 18 | 0 | 0 | 1 | 0 | yes | model
neutral | korvath-greenhouses-3 | 19 | 16 | 1 | 0 | 2 | 0 | yes | model
neutral | quillmoor-books-1 | 16 | 16 | 0 | 0 | 0 | 0 | yes | model
neutral | quillmoor-books-2 | 15 | 15 | 0 | 0 | 0 | 0 | yes | model
neutral | quillmoor-books-3 | 14 | 14 | 0 | 0 | 0 | 0 | yes | model
neutral | sallowfield-dental-1 | 20 | 19 | 0 | 0 | 1 | 0 | yes | model
neutral | sallowfield-dental-2 | 20 | 18 | 1 | 0 | 1 | 0 | yes | model
neutral | sallowfield-dental-3 | 19 | 17 | 1 | 0 | 1 | 0 | yes | model
```

Without the first-name rule the same saved runs give: baseline 37 of 216 removed (17.1%), neutral 13 of 197 (6.6%). The prompt alone met the lead and headline bars and missed the removal bar, so the phase stopped and the owner chose from six options.

**Decision.**

1. **The draft prompt tells the model how it is checked, with examples that name nothing from a test transcript** (`backend/app/pipeline/draft.py`). It says each sentence is checked alone against only what it cites; to cite every sentence a statement relies on, including a question or an introduction where a name is said; that the first sentence must name the organisation and cite where its name is spoken; to write "the company" where the speaker said "we"; to use a surname only in a sentence citing that person; that a role or place attached to a person needs its own citation; to write no uncited linking sentences; and that the headline may use only names and figures from sentences that follow these rules. A test fails if any prompt contains a name from a seeded or fixture transcript.
2. **One narrow rule is added to the ground check: a first name that matches exactly one speaker label supports that speaker's surname.** If the cited text says "Hana, run the calls" and exactly one speaker of the transcript is labelled "Hana ...", a sentence may say "Olund". It does nothing when two speakers share the first name; when the first name is also a word in another speaker's label; when the transcript also uses it as an ordinary word ("will", "mark") or it is a month or a weekday ("June", "May"); when it matches no label; or when it is not written as a name in a cited sentence (inside the sentence, or opening it as a form of address: "Hana, run the calls", not "Will do."). Each use is recorded on the kept sentence (`name_resolutions`), so the trace shows which sentences were kept this way. Written into `0003`.
3. **No more prompt rounds.** The owner's reason: further rounds would tune the prompt to habits seen on these same four transcripts, a softer form of tuning on the test. The honest measure is Phase 6, on cases this prompt has never seen.

**The result, stated as it is.**

| | Old prompt, check as in Phase 3 | Final prompt and check |
|---|---|---|
| Sentences removed, 12 trial runs | 37 of 216: 17.1%, about 1 in 6 | 10 of 197: 5.1%, about 1 in 20 |
| Sentences removed, all 15 runs with the final setup | | 14 of 252: 5.6%, about 1 in 18 |
| Lead sentence survives | 3 of 12 runs | 11 of 12 runs |
| Model's headline accepted | 5 of 12 runs | 11 of 12 runs |
| Draft cost | $0.0177 a run | $0.0188 a run |

- Of the drop from 37 to 10, the prompt accounts for all but 3; the first-name rule recovered 3 sentences (13 to 10), one in each Sallowfield run.
- The three seeds were then recorded for the demo, each time once and without choosing among runs: 55 sentences, 4 removed (7.3%), the lead kept and the model's headline accepted in all three. One of the 51 kept sentences stands by the first-name rule. (They were recorded three times in all, because the prompt and then the extract request changed after earlier recordings; only the last set is in the repository.)
- Together: 15 runs, 252 sentences, 14 removed, **5.6%, about 1 in 18.** With 14 events in 252 the plausible range is wide, roughly 3% to 9%, and 12 of the 15 runs are the same three seeds.
- Read by hand against the transcripts, every removed sentence in every round is true. What is still lost: a place named outside the cited sentence (the same two sentences recur across runs), a name that is only in the question being answered, and uncited bridge sentences.
- Every altered-copy test from Phase 3 passes unchanged, and the Phase 3 report on the eleven older drafts is identical (186 sentences, 146 kept). One Phase 3 test was replaced, not weakened: the check that no module imports a model client became two tests in `tests/test_model_seam.py`, that only the live client's module imports the SDK and that only it can reach the network at all. The first-name rule has its own tests: a wrong surname, another person's surname, a shared first name, an unmatched first name, a first name that is an ordinary word or a month, and a first name that only opens a sentence are each still removed.

**This figure was measured on four transcripts, all written for this project, and the prompt was developed while looking at them.** Its examples are neutral, but its rules were chosen from what these transcripts lost. A transcript it has never seen may do worse. The removal rate on the Phase 6 eval set (E9) is the number to trust, and is the one the README should lead with.

**Options the owner rejected, and why.**

- *Keep the prompt with seed-derived examples and report 2.1%.* The number would overstate: it was tuned on the test, and it leaves the seeds' names in the system prompt for every transcript.
- *Let a question count as cited when its answer is cited.* A name from a sentence the model did not cite would count, and an answer can contradict its question ("And Abbey Row?" "No, Kiln Street."). That weakens the claim (then worded "the model added nothing the speakers did not say"; reworded in `0015`) more than it buys.
- *One citable block per turn instead of per sentence.* Places named earlier in the same turn would fall inside the cited block, but what the reader sees highlighted becomes a whole turn, a looser pointer, and it reverses `0002`.
- *More prompt rounds* (not chosen): see decision 3.

**What the first-name rule costs the claim.** It is the first place the check accepts a name that is not literally in the cited text or its speaker label. It is derived only from the transcript's own speaker labels, never from the model, and it is recorded. Its limits, plainly:

- It trusts that "Hana" in the cited sentence is the speaker labelled "Hana Olund". If a transcript mentions a different Hana who never speaks, a sentence could give that Hana's doings to Olund and pass.
- Every word of a label after the first counts as a surname, so a label such as "Hana Olund Operations Lead" would also support "Operations" and "Lead".
- A first name that is an ordinary word the transcript happens never to write in lower case is still taken for a name when it appears inside a sentence.
- Like the rest of rule 2, it checks that the name is supported, not what is said about the person.

The reviewer's first attempt at this rule found it matching "will" to a speaker called Will and "June" to a speaker called June; those are closed and tested.

**Consequence.** The check stays strict in every other respect and stops costing most articles their lead and headline. Every prompt edit needs the seeds re-recorded (about 11 cents), which the fixture client enforces by missing loudly. Revisit if Phase 6's removal rate on unseen cases is well above this: the owner then decides between prompt work against those cases and the rejected options, with that evidence.
