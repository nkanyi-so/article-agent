# Plan: article-agent

This file is the single record of progress. Each phase lands as its own branch and pull request; the description links to the phase log here. A gate is ticked only when its evidence (the commands run and their real output) is written in the phase log. Never start a phase before the previous gate is ticked.

**Status:** blueprint approved by the owner on 2026-11-18 and committed as the base for the phase pull requests. Phase 0 is built on `phase-0-scaffold` and waits for the owner's review of its pull request, and for one owner step: the allow-list lines in `.claude/settings.json` (see the Phase 0 log).

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

- [x] `backend/`: uv project on Python 3.14, FastAPI app factory with `GET /health` only, ruff, mypy (strict), pytest. The `anthropic` package sits in an optional `live` dependency group and is not in the base set.
- [x] Tests cannot read `.env` or open a socket: env-file loading is off under pytest and sockets are blocked. One test proves each (a socket attempt fails; a planted `.env` value is not seen).
- [x] `frontend/`: Node pinned to 24 (`.nvmrc`, `engines`); upgrade Next.js 16.2.9 to the current 16.4 patch, after reading the bundled guide per `frontend/AGENTS.md`; if the upgrade breaks the build, stay on 16.2.9 and log why. Fix the three lint errors and the stale directive (fix, not quarantine). Delete `src/app/design-system/`. Add Vitest with one passing test.
- [x] `Makefile` with `setup` (installs both sides, runs `git config core.hooksPath .githooks`, warns if gitleaks is missing), `dev`, `check`, `format FILE=`.
- [ ] Harness layer adapted to this stack: allow list in `.claude/settings.json`, `protected-paths.txt` (the generated types file, `backend/recordings/`), CI setup steps for uv and Node with actions pinned by commit. List every change in the log.
- [x] `.env.example`; `.gitignore` already ignores `.env`.
- [x] No `*.harness-new` file left.
- [x] `BRIEF.md` moved to `docs/archive/` as history. `reference/` stays until Phase 6 replaces it.
- [x] Check the history about to be pushed against the synthetic-data rule: search the tree for the real names the brief says were replaced.
- [x] First commit and push (asks first). Branch protection on `main`: no force-push, CI must pass. *Pushed; protection refused by GitHub on the private repository and carried to Phase 9 by the owner's decision.*

**Gate:** `make check` exits 0 with at least one passing test on each side. The pre-commit hook refuses a commit when a test is made to fail (show it, then undo). CI runs green on the first push. Branch protection is shown to be on, **or** GitHub's refusal is pasted (protection on a private repository may need a paid plan) and the owner decides: pay for it, or carry this one item to Phase 9 when the repository goes public.

**Log:**

### 2026-11-18, Phase 0 built on `phase-0-scaffold`

**Before the branch: the base commit.** The blueprint was committed on `main` and then amended while still local, with the owner's approval: three profile URLs on a real social network's domain became `example.com` URLs, and the message gained `[skip ci]` because the base commit has no Makefile for CI to run. The whole-tree search the owner asked for then found more in `design/Bylined.dc.html`, the mock of the old lookup screen: three real companies named as sample people's employers, and a real news site and a real code host as sample source domains. All were replaced with invented names and `example.com` hosts in the same amend. What the search covered: every URL host in the tree (what remains is tool documentation, fonts, `localhost`, `example.com`), every e-mail address (none), social handles, and capitalised name pairs in string literals. Names left in place because they are placeholders or invented: Jane Doe, Acme, Northwind, Alex Chen, Maya Okafor, Halden Robotics. The brief does not list the real names it replaced (they stay in the private legacy repository), so the search was for anything real-looking, not for those names.

**Backend.** uv project in `backend/` on Python 3.14 (3.14.6 here). FastAPI 0.164.0 app factory, `GET /health` only, returning status, mode and version. Base set: `fastapi`, `pydantic`, `pydantic-settings`, `uvicorn`. `anthropic` is in the `live` dependency group, which nothing installs by default. ruff (format and lint), mypy strict with the Pydantic plugin, pytest with warnings as errors.

**Test isolation.** `tests/conftest.py` sets `APP_ENV_FILE=""` before any app module is imported, which switches env-file loading off. pytest runs with `--disable-socket`. Three tests: a network socket attempt raises; a planted `.env` is not seen; and a control showing the same planted file *is* seen once the switch is removed, so the second test cannot pass by accident. Unix sockets stay allowed (`--allow-unix-socket`): without it the two health tests error, because the asyncio event loop opens a local socket pair to wake itself. They cannot reach a network.

**Frontend.** Node pinned to 24 (`.nvmrc`, `engines`). Next.js 16.2.9 to 16.4.6 with React 19.3.1, after reading the bundled upgrade guides; the build passed, so no fallback was needed. TypeScript stays on 5 and ESLint on 9 by the owner's decision. `src/app/design-system/` deleted, which removed one of the three lint errors with it. The other two fixed, not silenced: `ThemeToggle` reads the theme from `<html data-theme>` with `useSyncExternalStore` instead of copying it into state in an effect; `Sidebar` derives "loading" from which path the list was last loaded for, and ignores a response that arrives after the path changed. The stale disable directive in `ThemeScript` is gone, and lint now runs with `--max-warnings 0`. Vitest 5.1.1 with five tests on the formatting helpers. It runs in the `node` environment; jsdom and the React testing library are added in Phase 7 when a component test needs them. `npm audit fix` (no forced upgrades) cleared 12 advisories in development dependencies; the audit now reports 0.

**Makefile.** `setup`, `dev`, `check` (split into `check-backend` and `check-frontend`), `format FILE=`. Every backend command runs with `uv run --locked`, so a lockfile that has drifted from `pyproject.toml` fails the gate. `dev` runs `scripts/dev.sh`, which forces `APP_MODE=demo` and stops both servers when it is interrupted or either one exits. `format` formats Python only: the frontend has no formatter and none was added.

**Node in non-interactive shells.** On this machine a git hook resolves the system Node 20 ahead of nvm. `scripts/with-node.sh` wraps every frontend command: it uses the active Node if its major version matches `frontend/.nvmrc`, otherwise tries nvm, otherwise fails loudly. Shown below.

**Harness changes, every one.**
- `.github/workflows/ci.yml`: the setup placeholder replaced by `astral-sh/setup-uv` (v10.3.3, pinned by commit, uv 0.13.9), `actions/setup-node` (v7.1.0, pinned by commit, version from `frontend/.nvmrc`), then `make setup` and `make check`. The secret-scan job is untouched.
- `.claude/hooks/protected-paths.txt`: `frontend/src/lib/generated/*` and `backend/recordings/*`.
- `.claude/settings.json`: **not changed.** The edit adding `make check-backend`, `make check-frontend` and `make format FILE=*` to the allow list was refused by the session's permission layer, which does not let the agent widen its own permissions. The box above stays open for this one line; the owner can add the three entries by hand or leave the list as it is (nothing depends on them).
- `.githooks/pre-commit`: unchanged.

**Housekeeping.** `.env.example` added. `BRIEF.md` moved to `docs/archive/`. No `*.harness-new` file exists.

**Gate evidence.**

`make check`, exit 0:

```
cd backend && uv run --locked ruff format --check .
6 files already formatted
cd backend && uv run --locked ruff check .
All checks passed!
cd backend && uv run --locked mypy
Success: no issues found in 6 source files
cd backend && uv run --locked pytest -q
5 passed in 0.16s
cd frontend && scripts/with-node.sh npm run lint        (no output, exit 0)
cd frontend && scripts/with-node.sh npm run typecheck   (no output, exit 0)
cd frontend && scripts/with-node.sh npm run test
 Test Files  1 passed (1)
      Tests  5 passed (5)
cd frontend && scripts/with-node.sh npm run build
✓ Compiled successfully in 297ms
```

The same gate from a bare shell that resolves Node 20 first, and the wrapper's refusal when Node 24 cannot be found:

```
$ env -i HOME=$HOME PATH=/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin bash -c 'node -v; ./scripts/with-node.sh node -v; make check; echo "make check exit=$?"'
v20.18.0
v24.22.3
make check exit=0
$ env -i HOME=/nonexistent PATH=/usr/local/bin:/usr/bin:/bin bash -c './scripts/with-node.sh node -v; echo "exit=$?"'
with-node: need Node 24 (frontend/.nvmrc) but found: 20.
with-node: install it, for example: nvm install 24
exit=1
```

The pre-commit hook refusing a commit. `test_health.py` was edited to expect status 201, staged, and committed:

```
$ git commit -m "test: deliberately failing commit, must be refused"
INF no leaks found
>       assert response.status_code == 201
E       assert 200 == 201
tests/test_health.py:18: AssertionError
FAILED tests/test_health.py::test_health_reports_mode_and_version - assert 20...
1 failed, 4 passed in 0.18s
make: *** [check-backend] Error 1
pre-commit: make check failed. Fix the cause before committing.
HEAD unchanged: 3bc14205baa57276d1ebe6ba92639ae54fc80fac
```

The assertion was put back to 200 and the gate re-run (the output at the top of this section is from after the restore).

The Anthropic SDK is not in the base set: `uv export --locked --no-dev` lists no `anthropic` line, and `uv pip list` in the synced environment shows none.

**Reviewer** (fresh context, over the staged diff against `main`). Its verdict: "No blocking findings. Two non-blocking findings." It re-checked for itself, rather than from this log: the three action pins against `git ls-remote --tags` (all real commits for the stated tags), the CI and protected-paths changes (only additions, nothing loosened), test isolation (including that the planted-file test has a working control), `anthropic` outside the base set (`uv export`, `uv pip list`, the lockfile), both lockfiles against their manifests, the lint fixes ("real fixes, not suppressions ... Behaviour is unchanged"), the Makefile and the Node wrapper, and the synthetic-data rule across the tree. Findings as reported:

1. *Non-blocking: `make check` failed once with no diagnostic, and I could not reproduce it.* On its first run `next build` printed "Running TypeScript ... Failed to type check." with no TypeScript error; the next four runs passed. Its suggested cause: stale generated route types under `frontend/.next`, since the `/design-system` route was deleted this phase. Its suggested fix: if it recurs, delete `frontend/.next` and note it; if it keeps recurring, have `check-frontend` clear the generated types first.
   - *What I did:* nothing to the gate. The reviewer reported that nothing else was running, but the verifier was running `make dev` and `make check` in the same folder during that window (the verifier in turn noticed the reviewer's runs), and a dev server and a build share `frontend/.next`. That is the likelier cause, but it is not proven, and I have not seen the failure in any of my own runs. Logged in the harness notes; the reviewer's fix is the next step if it happens with nothing else running.
2. *Non-blocking: the status line in `docs/PLAN.md` is out of date* ("Phase 0 is next").
   - *What I did:* fixed.

It also observed, not as a finding: tests read the shell's environment, though not `.env`, so an exported `APP_MODE=live` would fail `test_health` (safely). Carried to Phase 4, where `conftest.py` should also unset `APP_MODE` and `ANTHROPIC_API_KEY`.

**Verifier** (ran the documented commands from a shell that resolves Node 20 first).

| # | What it did | Expected | What happened | Result |
|---|---|---|---|---|
| 1 | `make setup` | Installs both sides, sets the hooks path, no PATH fix needed | `uv sync --locked` ok; `npm ci` through the wrapper, 384 packages, 0 vulnerabilities; hooks path set; no gitleaks warning | pass |
| 2 | `make check; echo EXIT=$?` | Exit 0, a passing test on each side | `EXIT=0`; backend 5 passed, frontend 5 passed, build ok on Next 16.4.6 | pass |
| 3 | `make dev`, then `curl -si localhost:8000/health` | 200, demo mode | `200`, `{"status":"ok","mode":"demo","version":"0.1.0"}` | pass |
| 4 | `curl -si localhost:8000/nope`; `curl -XPOST localhost:8000/health` | 404 and 405 as JSON | `{"detail":"Not Found"}`; `{"detail":"Method Not Allowed"}` | pass |
| 5 | `curl localhost:3000/`, `/runs/abc`, `/zzz` | Pages render | 200 with real HTML, 200, 404 | pass |
| 6 | `APP_MODE=live make dev`, then `/health` | Live mode cannot start by accident | `"mode":"demo"` | pass |
| 7 | `make format FILE=backend/app/zz_tmp.py` on a mis-formatted file | Formatted | Exit 0, file reformatted, then deleted | pass |
| 8 | `make format` with no `FILE` | Usage, non-zero exit | `usage: make format FILE=<path>`, exit 2 | pass |
| 9 | `make format FILE=frontend/zz.py` | Left alone, as the Makefile says | Exit 0, unchanged | pass |
| 10 | `cd backend && uv run --locked python -c "import anthropic"` | Not installed | `ModuleNotFoundError: No module named 'anthropic'` | pass |
| 11 | Shutdown, then `lsof -i :8000 -i :3000` | Ports free | Free at the end, but only after killing processes by hand (finding 2) | pass with a caveat |
| 12 | `git status --short` before and after | Identical | Identical, after it restored `frontend/AGENTS.md` (finding 1) | pass |

Its findings, and what I did about each:

1. *`make dev` modifies a tracked file.* Next 16.4 rewrites its managed block in `frontend/AGENTS.md` on every `next dev`. **Fixed:** the bundled `agentRules` reference says to commit the block, so `frontend/AGENTS.md` now holds the 16.4 text exactly. Its checksum is the same before and after two `make dev` runs.
2. *Stopping `make dev` from outside left orphans* (uvicorn, `next dev` and `next-server` still holding both ports), and 3. *an orphaned uvicorn needed `kill -9`*, the same cause. **Fixed for the documented use, with a limit that stays.** The recipe is now `scripts/dev.sh`, which puts each server in its own process group and stops both groups on interrupt, on terminate, and when either server exits. Shown: an interrupt and a terminate sent to the foreground process group (what Ctrl-C in a terminal does) each leave 0 listeners and 0 leftover processes:

   ```
   [INT] up: 3 listeners
   [INT to the foreground group] listeners after: 0  leftover procs: 0
   [TERM] up: 3 listeners
   [TERM to the foreground group] listeners after: 0  leftover procs: 0
   AGENTS.md before=5ec4789692f7 after=5ec4789692f7
   ```

   The limit: a signal sent to the `make` process alone, which is what the verifier did, still orphans the servers, because make dies without telling its child. Signal the group, or `scripts/dev.sh` itself.
4. *Another process was running `make check` in a loop.* That was the reviewer, running at the same time. See the reviewer's finding 1.

What the verifier could not exercise: the pre-commit refusal (it was told not to commit; shown above instead); CI and branch protection (below); the frontend in a real browser, so hydration, the theme toggle and the sidebar's loading state are unchecked beyond lint, types and build; an interactive Ctrl-C (covered above by signalling the group, which is not quite the same thing); `--reload` on file edits; `make setup` from a clean checkout with no `.venv` or `node_modules` (CI does exactly that, below).

**First push, CI and branch protection.** `main` (the base commit, CI skipped by its message) and `phase-0-scaffold` were pushed with the owner's go-ahead, and pull request #1 opened. The first CI run, on the pull request, from a clean checkout:

```
$ gh run view 44366655242 --json conclusion,jobs --jq '.conclusion, (.jobs[] | "\(.name): \(.conclusion)")'
success
secrets: success
check: success
```

The `check` job's steps: checkout, setup-uv, setup-node, `make setup`, `make check`, all passed, 47 seconds. This also covers what the verifier could not: `make setup` with no `.venv` and no `node_modules`.

Branch protection, GitHub's refusal:

```
$ gh api -X PUT repos/nkanyi-so/article-agent/branches/main/protection --input protection.json
{"message":"Upgrade to GitHub Pro or make this repository public to enable this feature.","documentation_url":"https://docs.github.com/rest/branches/branch-protection#update-branch-protection","status":"403"}
```

The owner had already decided this case: do not pay, carry the item to Phase 9. The Phase 9 step now says so. What was asked for, for when it can be set: required checks `check` and `secrets`, no force-push, no deletion, applied to administrators too.

**Gate: passed, 2026-11-18.** `make check` exits 0 with passing tests on both sides; the pre-commit hook refused a failing commit; CI is green on the first run; branch protection was refused and the refusal is pasted, with the owner's decision. One step stays open and is not part of the gate: the allow-list lines in `.claude/settings.json`, which only the owner can add.

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
- [ ] Ask the owner, then make the repository public. Turn on branch protection on `main` (no force-push, the `check` and `secrets` jobs must pass) and show it is on: carried from Phase 0, where GitHub refused it on the private repository.
- [ ] Walkthrough video (owner).

**Gate:** the spec's "Done when", item by item, each with its evidence.

**Log:**
