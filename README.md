# article-agent

Turns a meeting or interview transcript into a short article in which every sentence can be checked against what was said.

**Live demo:** https://article-agent-web.vercel.app. It replays recordings of real model calls, so it needs no key and spends nothing. Every transcript, person and company in it is invented. One of the four demo runs has a draft altered by hand, and says so, to show the code removing something false.

![A flagged sentence, the transcript line it cites, and the judge's reason](docs/screens/05-sentence-flagged-light-desktop.png)

## The point

Every sentence of the article points at the transcript lines behind it. Code removes any sentence in which a number, date, name or quotation it can read is not in those lines or their speaker labels. A judge model then reads each sentence that is left against its lines and flags the ones it finds unsupported, and every flag is shown to the reader.

The judge is a second model, a different one from the model that writes, so the writer does not mark its own work. A sentence is grounded when the lines it cites support it. This does not claim the writer adds nothing: code can only see what is missing from the cited lines, the judge is a model and can miss things, and a sentence the judge flags stays in the article, marked, where a sentence code can show to be wrong is removed.

## How it works

```mermaid
flowchart LR
  A["ingest<br/>code"] --> B["extract<br/>writer model"]
  B --> C["draft<br/>writer model, citations"]
  C --> D["ground<br/>code"]
  D --> E["evaluate<br/>code, then judge model"]
  E --> F["article, flags<br/>and stored trace"]
```

1. **Ingest** splits the transcript into sentences, each a block that can be cited, or refuses an input it cannot use (empty, too short, too long, or not in `Speaker: text` form).
2. **Extract** asks the writer model for the points, corrections and disagreements, as structured output.
3. **Draft** has the writer model write the article using the model API's citations feature: the transcript is passed as a document, and each sentence comes back with pointers into it, so it cannot cite a line that does not exist.
4. **Ground**, in code, removes a sentence that cites nothing, has a number, date or name missing from its cited lines, misquotes, rests on a statement a speaker later corrected, or gives a statement to a speaker whose line it does not cite. A removed sentence is listed with its reason. It is never re-cited or reworded.
5. **Evaluate** runs the code checks, then sends each kept sentence with its lines to the judge. Every stage's input and output is stored, the trace, and a run can be re-run from any stage.

The writer is `claude-sonnet-5-5` and the judge is `claude-opus-5-5`. Every model call goes through one interface, live or recorded. A recording is filed under a hash of the exact request, so an edited prompt fails the replay loudly. See [ARCHITECTURE.md](docs/ARCHITECTURE.md) and [decisions/](docs/decisions/).

## Results

Judged groundedness: the share of kept sentences, and the headline, that the judge found supported by the lines they cite. The eval set is ten transcripts, each run three times; a case mean is one transcript's average over its three runs. `make check` replays the set from recordings and fails on a missed threshold.

| | Read with the question shown | Cited lines alone |
|---|---|---|
| Mean of case means | 0.959 | 0.904 |
| Lowest case mean | 0.906 | 0.730 |

The thresholds are a mean of at least 0.90 and no case under 0.80.

"The question shown" needs explaining. In an interview the writer often cites a bare answer, such as "October 2025.", which supports nothing without the question it replied to. So the code now attaches the question asked directly before each cited answer and shows it to the judge, and to the reader, marked as added by code and not evidence. "Cited lines alone" is the judge reading without it.

"Read with the question shown" is the second measure: it was introduced after two runs failed the first, cited lines alone, and the pass comes from that change. No threshold number was changed, and on cited lines alone this run would still fail the 0.80 floor.

Two more numbers give the scale. Code removed 14 of 468 drafted sentences (3.0%). The judge still flags about one kept sentence in 23, mostly additions by the writer that no code rule can see, such as a job title the cited lines do not state. The judge itself was checked against 29 hand-labelled pairs, 13 of them known to be unsupported, and agreed on all of them.

All ten transcripts were written for this project: this is evidence that the checks can fail and were made to pass honestly, not a benchmark. Full detail: [docs/EVALS.md](docs/EVALS.md).

## Run it

Needs Python 3.14 with [uv](https://docs.astral.sh/uv/), and Node 24.

```
make setup     # install both sides, enable the pre-commit hook
make dev       # backend on :8000 in demo mode, frontend on :3000. No key.
make check     # format, lint, types, tests, the eval set replayed from recordings, the build
```

Then open http://localhost:3000. `node scripts/browser-check.mjs`, also in CI, drives Chrome through a visitor's steps.

Demo mode replays the four seeded transcripts from recordings. Live mode writes about a transcript you paste and costs a few cents a run. It needs `APP_MODE=live`, `ANTHROPIC_API_KEY` in `.env` and the `live` dependency group, which holds the Anthropic SDK. No `make` target starts it.

## Production notes

- **Spend:** the hosted backend has no key and does not install the SDK. Live mode puts every route that can start a run behind a per-address rate limit (10 a minute) and a daily budget ($2 by default).
- **Auth:** there are no accounts. The hosted demo takes only the seeded transcripts.
- **Failure handling:** 60 seconds a call, one retry, 240 seconds a run. Every event stream ends with `run_completed` or `run_failed`.
- **Untrusted input:** transcript text reaches a model only as a citable document or as escaped, delimited data. Model output is validated before use.
- **Tests** never read `.env` and cannot open a network socket.
- **Known limits:** the code does not read "a third", ordinals or a name in lower case, so those rest on the judge. English `Speaker: text` transcripts only.

## How it was built

Built with AI assistance (Claude Code) under checks I set: a plan reviewed before any code, tests first on the core logic, `make check` and CI with a secret scan on every pull request, and an independent review of each phase's diff. The full build record is kept at the [`build-log` tag](https://github.com/nkanyi-so/article-agent/tree/build-log).

## Next

- Repeat the eval on transcripts written by someone else.
- Have the writer cite the question itself, measured over enough runs to tell, and add a second judge.
- Shared storage on the host, so the rate limit and the run list are one.
