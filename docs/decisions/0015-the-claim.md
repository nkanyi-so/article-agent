# 0015: the claim, reworded to what is exactly true

**Status:** decided by the owner on 2026-11-19, after the third judged run.

**Context.** The project's claim was "the model added nothing the speakers did not say, and you can check that". The third judged run (`0014`) showed it is not true as an absolute. With every code check passing in all 30 runs, the judge still found 23 of 484 kept sentences unsupported, and 20 of those were additions by the writer that no code rule can see: a role the cited lines do not state, the host's words given to the guest, a comparison or arithmetic in a headline, a cause the speaker did not give. About one sentence in twenty-five.

**Decision.** The claim, wherever it is stated:

> Every sentence of the article points at the transcript lines behind it. Code removes any sentence in which a number, date, name or quotation it can read is not in those lines or their speaker labels. A judge model then reads each sentence that is left against its lines and flags the ones it finds unsupported, and every flag is shown to the reader.

The owner's wording was: "Every sentence points at the transcript lines behind it. Code removes any sentence whose numbers, dates, names or quotes are not in those lines. A judge model then flags what code cannot see, and every flag is shown to the reader." Three small changes were made to keep it exactly true, as the owner allowed:

- "of the article", and the spec says beside it that the headline cites no lines of its own (code checks it against the kept sentences; the judge reads it against the whole kept article).
- "or their speaker labels": a speaker's name comes from the label of a line they spoke, and a surname can stand on a first name that only one speaker has (`0013`).
- "flags the ones it finds unsupported" in place of "flags what code cannot see": the judge is a model and can miss things. It failed every known negative in calibration, which is evidence, not a guarantee.

**What follows from it.**

- A flagged sentence stays in the article. It is not removed: removal is for what code can show, and a judge's opinion is shown as an opinion, with its reason.
- The screen has to make the two visibly different: removed by code, and flagged by the judge (Phase 7).
- The README states the claim in these words and gives the rate at which the judge flags sentences, not only the rate at which code removes them.
- Earlier records that argue from "the model added nothing" (`0003`, `0013`) keep their reasoning and now point here.

**Changed once more by the owner on 2026-11-19, after the final review of the README.** The second sentence read "Code removes any sentence whose numbers, dates, names or quotations are not in those lines or their speaker labels." The reviewer pointed out that the code does not read every number or name: it does not see "a third", "one", an ordinal, a name in lower case, or a quotation in single quotation marks (`0003`, "What the code does not check"), and a headline's "about a third" passed the code in the recorded runs. The sentence now says "a number, date, name or quotation it can read", which is exactly what the code does. The sentence that follows the claim wherever it is stated, saying what it does not claim, stays.

