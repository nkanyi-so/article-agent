# Plan: article-agent

This file is the single record of progress. Each phase lands as its own branch and pull request; the description links to the phase log here. A gate is ticked only when its evidence (the commands run and their real output) is written in the phase log. Never start a phase before the previous gate is ticked.

**Status:** blueprint approved by the owner on 2026-11-18 and committed as the base for the phase pull requests. Phase 0 is next.

**Owner's decisions at approval (2026-11-18).** Hosting: Vercel Hobby for both projects, Fly.io as the fallback if Phase 2 shows the stream buffering (`decisions/0009`). Branch protection: do not pay; if GitHub refuses on the private repository, the item is carried to Phase 9. The separate Anthropic workspace recommended below is skipped: the owner reuses an existing API key and adds it to `.env` personally, so the spend stops in each paid step are the only guard. After the Phase 1 spike, the real cost per run and per eval run, and the cheapest model setup that does not weaken the eval, are reported before any larger paid step. All other intake calls and assumptions are accepted.

**Steps that spend money or act outside this machine.** Each asks the owner first, every time, with an estimate. Estimates are rough until Phase 1 measures real token counts.

| Phase | Step | Estimate |
|---|---|---|
| 0 | First push to GitHub; branch protection setting | free |
| 1 | Citations spike, about 16 model calls | about $1, stop at $3 |
| 2 | Connect two Vercel projects; first deploys | free |
| 4 | Record the three seeded transcripts | about $1 |
| 6 | Record the remaining eval cases; first judged live run | about $3 to $5 |
| 6 | Second judged run after the first real failure is fixed | about $3 to $5 |
| 8 | Production deploy of the demo | free |
| 9 | Make the repository public | free |

Whole project: about $15. Recommended guard, an owner action before Phase 1: a separate Anthropic workspace for this project with a monthly spend limit of $25, and a key from that workspace only.

**What a merge to `main` does.** Until Phase 2, nothing. From Phase 2, it deploys the frontend and the backend to Vercel.

---

## Phase 0: scaffold and process layer

- [ ] `backend/`: uv project on Python 3.14, FastAPI app factory with `GET /health` only, ruff, mypy (strict), pytest. The `anthropic` package sits in an optional `live` dependency group and is not in the base set.
- [ ] Tests cannot read `.env` or open a socket: env-file loading is off under pytest and sockets are blocked. One test proves each (a socket attempt fails; a planted `.env` value is not seen).
- [ ] `frontend/`: Node pinned to 24 (`.nvmrc`, `engines`); upgrade Next.js 16.2.9 to the current 16.4 patch, after reading the bundled guide per `frontend/AGENTS.md`; if the upgrade breaks the build, stay on 16.2.9 and log why. Fix the three lint errors and the stale directive (fix, not quarantine). Delete `src/app/design-system/`. Add Vitest with one passing test.
- [ ] `Makefile` with `setup` (installs both sides, runs `git config core.hooksPath .githooks`, warns if gitleaks is missing), `dev`, `check`, `format FILE=`.
- [ ] Harness layer adapted to this stack: allow list in `.claude/settings.json`, `protected-paths.txt` (the generated types file, `backend/recordings/`), CI setup steps for uv and Node with actions pinned by commit. List every change in the log.
- [ ] `.env.example`; `.gitignore` already ignores `.env`.
- [ ] No `*.harness-new` file left.
- [ ] `BRIEF.md` moved to `docs/archive/` as history. `reference/` stays until Phase 6 replaces it.
- [ ] Check the history about to be pushed against the synthetic-data rule: search the tree for the real names the brief says were replaced.
- [ ] First commit and push (asks first). Branch protection on `main`: no force-push, CI must pass.

**Gate:** `make check` exits 0 with at least one passing test on each side. The pre-commit hook refuses a commit when a test is made to fail (show it, then undo). CI runs green on the first push. Branch protection is shown to be on, **or** GitHub's refusal is pasted (protection on a private repository may need a paid plan) and the owner decides: pay for it, or carry this one item to Phase 9 when the repository goes public.

**Log:**

---

## Phase 1: citations spike (paid)

Nobody has seen how citations behave on a transcript with thinking on. This phase finds out before the design depends on it. Throwaway code in `spikes/`, not application code.

- [ ] Write the first seeded transcript (fictional company, about 60 turns) and a short second one in which a speaker corrects a figure. Owner reads both before any call.
- [ ] Ask the owner, with the estimate. Then run about 16 calls: `claude-sonnet-5-5` and `claude-opus-5-5`, two effort levels each, one block per sentence against one block per turn, both transcripts, two repeats of the main variant.
- [ ] One request with citations and an output schema together, to confirm the documented 400 (not billed).
- [ ] Measure and record: whether citations and adaptive thinking combine at all; the share of text blocks that come back uncited; how many sentences one cited block holds; whether a headline line gets cited; what the model does with the corrected figure; whether cited spans are tight enough for the number and name check; tokens, cost and latency per call.
- [ ] Save every raw request and response. They become the first test fixtures.
- [ ] Write the findings as a decision record. If they contradict `decisions/0002`, `0003` or `0005`, stop: the records and the spec change first, with the owner's approval.

**Gate:** the findings record exists with real numbers and the saved responses it rests on; total spend is stated from the API's usage figures; each design assumption in `0002`, `0003` and `0005` is marked confirmed or changed.

**Log:**

---

## Phase 2: walking skeleton on the host

Proves the host before anything is built on it. No pipeline yet.

- [ ] A dummy event stream route that emits five typed events over about ten seconds and ends with a terminal event.
- [ ] Ask the owner, then connect two Vercel projects to the repository (`frontend/`, `backend/`) and deploy. Point the old paused frontend project at the new repository or create a new one: owner's choice at that moment.
- [ ] Show on the deployed backend: the stream arrives event by event, not in one lump; the cold start time; the `anthropic` package is absent from the deployed dependency set; a scratch SQLite file can be created and read.
- [ ] Frontend calls the deployed `/health` across origins with CORS limited to its own origin.

**Gate:** timestamps from a real request to the deployed stream show events arriving spread over time; cold start measured; the deployed dependency list pasted without `anthropic`. If the stream is buffered or the runtime does not fit, stop and write the hosting record's replacement (the Fly.io fallback, about $2.35 a month) for approval.

**Log:**

---

## Phase 3: ingest and the ground check

Pure code, test-first. Uses the Phase 1 responses as fixtures.

- [ ] Schemas: segment, claim, citation, removed unit, stage record, typed errors (the old hierarchy's shape, new members).
- [ ] Ingest: turn parser, sentence splitter, segment numbering with speaker and source line, the four code refusals.
- [ ] Ground: draft blocks to claims; the four removal rules; removed units recorded with a reason; the fewer-than-three failure; headline handling as Phase 1 settled it.
- [ ] Tests on real recorded responses and on hand-altered ones (a wrong number, an uncited sentence, a misquote, a claim resting only on a corrected segment). Each must be removed with the right reason.

**Gate:** `make check` exits 0. The test list shows each removal rule failing a hand-altered response and passing the real one. No module in this phase imports a model client.

**Log:**

---

## Phase 4: model seam, extract, draft, runner

- [ ] `ModelClient` interface and its request and response models; the request hash; `FixtureModelClient` (loud miss); `LiveModelClient` with explicit timeout and retries, cost and latency from usage, typed errors for refusal, truncation and a model mismatch.
- [ ] A test that only the live client module imports `anthropic`, and that demo mode cannot construct it.
- [ ] Extract stage (structured output, validated segment indexes) and draft stage (citable document, no schema). Transcript text only as document blocks or delimited data.
- [ ] The runner: stage order, stage records in memory, events, the terminal-event guarantee, the run ceiling.
- [ ] Write the other two seeded transcripts. Ask the owner, then record all three with the live client (about $1).
- [ ] A command that runs a seeded transcript end to end in fixture mode and prints the article with its citations and removed units.

**Gate:** `make check` exits 0 with the three seeds running end to end from recordings. Editing one word of a prompt makes the fixture client fail with a miss (show it, then undo). The recording run's spend is stated.

**Log:**

---

## Phase 5: stored runs, replay, API, guards

First working draft.

- [ ] `Store` over SQLite: the four tables, seeded runs created at startup through the real pipeline.
- [ ] Replay from a stage: a new run, earlier stages copied and marked, later stages re-executed from stored input.
- [ ] The HTTP routes in the architecture, the typed event union, uniform error mapping with no upstream text.
- [ ] Rate limit and daily budget as a dependency on every run-starting route; a test that fails when such a route lacks it; `paste_disabled_in_demo`.
- [ ] A script that writes `openapi.json` with no server and no key.
- [ ] Verifier run against the local backend in demo mode.

**Gate:** `make check` exits 0. Verifier table: a seeded run streams to `run_completed`; a replay from `draft` yields a linked run; a reload mid-run finds the run; an induced stage failure still ends in `run_failed`; pasted text in demo is refused; the budget test refuses a run when the day's recorded cost is at the cap.

**Log:**

---

## Phase 6: evals

- [ ] The case set (at least twelve, hand-written expectations) and about 24 hand-labelled judge calibration pairs.
- [ ] Code checks E1 to E9, the report builder, the judge wrapped in code (hard-fail before asking, clamp what comes back), thresholds in one file.
- [ ] The harness: fixture mode by default and in `make check`, non-zero exit on any failed threshold, plumbing failures kept apart from wrong answers, a dated result file.
- [ ] Baseline tests: a hand-built perfect run passes; an empty article fails.
- [ ] Ask the owner, then record the remaining cases and run the first judged live run. If everything passes, add harder cases until something fails.
- [ ] Fix one real failure without touching a threshold. Ask the owner, then run again. Keep both result files.
- [ ] Delete `reference/`.

**Gate:** `make check` exits 0 including fixture-mode evals. Two dated live result files, the first with at least one real failure, the second with its fix; both spends stated. The removal-rate ceiling for E9 is set by decision record from the first run.

**Log:**

---

## Phase 7: frontend

Read `frontend/AGENTS.md` and the bundled Next.js guide first.

- [ ] Generated types from `openapi.json`, with the freshness check in `make check`. Delete the hand-copied type files.
- [ ] Remove the name-lookup UI and every vendor name that came with it.
- [ ] Entry: three seeded transcripts to choose from; the paste box shown and disabled in demo with its one line, enabled in live mode from `/api/config`.
- [ ] Run page: the article with clickable claims that highlight their transcript sentences; the removed-units list with reasons; the trace with each stage's input, output, cost and latency; re-run from a stage; eval cards.
- [ ] Fix the known defects: a stream that closes without a terminal event; every error shown as "not found"; the address changing before the run exists.
- [ ] Tests for the stream parser and claim rendering. Verifier run in a browser-like flow.

**Gate:** `make check` exits 0 on both sides. Verifier table for the flow in the spec's "Done when", run locally in demo mode with no key. No vendor name from the old lookup path remains (`git grep` output pasted).

**Log:**

---

## Phase 8: hosted demo

- [ ] Deploy both projects in demo mode (asks first). Production settings: CORS origin, body size cap, rate limit.
- [ ] A fourth, clearly labelled demo run built from a hand-altered recording, so a visitor sees the ground check remove a wrong number and an uncited sentence.
- [ ] Verifier against the public address, read-only requests and seeded runs only.

**Gate:** verifier table against the hosted address: page loads with no key, seeded run streams, claim click works, replay works, removed units visible. The deployed backend's dependency list has no `anthropic`.

**Log:**

---

## Phase 9: release

- [ ] README with the seven profile sections; every claim traced to code or to a result file.
- [ ] Reviewer in security mode over the whole repository; fix every blocking finding.
- [ ] History check against the synthetic-data rule and a full-history secret scan.
- [ ] Ask the owner, then make the repository public. Confirm branch protection is on.
- [ ] Walkthrough video (owner).

**Gate:** the spec's "Done when", item by item, each with its evidence.

**Log:**
