# Plan: article-agent

This file is the single record of progress. Each phase lands as its own branch and pull request; the description links to the phase log here. A gate is ticked only when its evidence (the commands run and their real output) is written in the phase log. Never start a phase before the previous gate is ticked.

**Status:** blueprint approved by the owner on 2026-11-18 and committed as the base for the phase pull requests. Phase 0 was merged on 2026-11-18 (pull request #1). Phase 1 was merged on 2026-11-18 (pull request #2), and the owner decided the three points it raised (the unit is the sentence; the name rule stays strict; the model's headline is checked against the kept body), so Phase 3 is no longer blocked. Phase 2 (the walking skeleton on Vercel) is done on `phase-2-walking-skeleton` and waits for the owner's review of its pull request; one owner step is open (give Vercel's GitHub app access to the repository). Phase 3 is next.

**Owner's decisions at approval (2026-11-18).** Hosting: Vercel Hobby for both projects, Fly.io as the fallback if Phase 2 shows the stream buffering (`decisions/0009`). Branch protection: do not pay; if GitHub refuses on the private repository, the item is carried to Phase 9. The separate Anthropic workspace recommended below is skipped: the owner reuses an existing API key and adds it to `.env` personally, so the spend stops in each paid step are the only guard. After the Phase 1 spike, the real cost per run and per eval run, and the cheapest model setup that does not weaken the eval, are reported before any larger paid step. All other intake calls and assumptions are accepted.

**Steps that spend money or act outside this machine.** Each asks the owner first, every time, with an estimate. Estimates are rough until Phase 1 measures real token counts.

| Phase | Step | Estimate |
|---|---|---|
| 0 | First push to GitHub; branch protection setting | free |
| 1 | Citations spike, about 16 model calls | about $1, stop at $3. **Actual: $0.55, 25 billed calls** (18 in the spike, 7 re-run after a name change). |
| 2 | Connect two Vercel projects; first deploys | free |
| 4 | Record the three seeded transcripts, and try the draft prompt change from `0012` | about $0.30 (measured: about 4 cents a transcript for extract and draft; a few repeats for the prompt change). Stop at $1. |
| 6 | Record the remaining eval cases; first judged live run | about $1 (measured: about 7 cents a full run, about 60 cents an eval run). Stop at $3. |
| 6 | Second judged run after the first real failure is fixed | about $1. Stop at $3. |
| 8 | Production deploy of the demo | free |
| 9 | Make the repository public | free |

Whole project: about $3 to $4 on the measured figures (was about $15 before Phase 1 measured them); $0.55 spent so far. Recommended guard, an owner action before Phase 1: a separate Anthropic workspace for this project with a monthly spend limit of $25, and a key from that workspace only.

**What a merge to `main` does.** Today, nothing: the two Vercel projects exist and are deployed from the command line, but they are not yet connected to the repository (the owner has to give Vercel's GitHub app access to it). Once connected, a merge to `main` deploys the frontend and the backend to Vercel.

---

## Phase 0: scaffold and process layer

- [x] `backend/`: uv project on Python 3.14, FastAPI app factory with `GET /health` only, ruff, mypy (strict), pytest. The `anthropic` package sits in an optional `live` dependency group and is not in the base set.
- [x] Tests cannot read `.env` or open a socket: env-file loading is off under pytest and sockets are blocked. One test proves each (a socket attempt fails; a planted `.env` value is not seen).
- [x] `frontend/`: Node pinned to 24 (`.nvmrc`, `engines`); upgrade Next.js 16.2.9 to the current 16.4 patch, after reading the bundled guide per `frontend/AGENTS.md`; if the upgrade breaks the build, stay on 16.2.9 and log why. Fix the three lint errors and the stale directive (fix, not quarantine). Delete `src/app/design-system/`. Add Vitest with one passing test.
- [x] `Makefile` with `setup` (installs both sides, runs `git config core.hooksPath .githooks`, warns if gitleaks is missing), `dev`, `check`, `format FILE=`.
- [x] Harness layer adapted to this stack (the allow-list lines were skipped by the owner's decision on 2026-11-18, not done): allow list in `.claude/settings.json`, `protected-paths.txt` (the generated types file, `backend/recordings/`), CI setup steps for uv and Node with actions pinned by commit. List every change in the log.
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

### 2026-11-18, after the owner's review

- Pull request #1 merged by squash at the owner's instruction (`a99fe70`).
- **The real-names search is done, by the owner:** the names from the old repository's fixtures were searched across this folder and none appear. That closes the part of the synthetic-data step the agent could not run.
- **The allow-list lines are skipped for now** by the owner's decision. The harness box is ticked on that basis; the note stays in `docs/HARNESS_NOTES.md`.
- From here on the reviewer and the verifier run one after the other, never at the same time in the same folder, since that overlap is the likely cause of the one unexplained build failure.

---

## Phase 1: citations spike (paid)

Nobody has seen how citations behave on a transcript with thinking on. This phase finds out before the design depends on it. Throwaway code in `spikes/`, not application code.

- [x] Write the first seeded transcript (fictional company, about 60 turns) and a short second one in which a speaker corrects a figure. Owner reads both before any call.
- [x] Ask the owner, with the estimate. Then run about 16 calls: `claude-sonnet-5-5` and `claude-opus-5-5`, two effort levels each, one block per sentence against one block per turn, both transcripts, two repeats of the main variant.
- [x] One request with citations and an output schema together, to confirm the documented 400 (not billed).
- [x] Measure and record: whether citations and adaptive thinking combine at all; the share of text blocks that come back uncited; how many sentences one cited block holds; whether a headline line gets cited; what the model does with the corrected figure; whether cited spans are tight enough for the number and name check; tokens, cost and latency per call.
- [x] Save every raw request and response. They become the first test fixtures.
- [x] Write the findings as a decision record. If they contradict `decisions/0002`, `0003` or `0005`, stop: the records and the spec change first, with the owner's approval.

**Gate:** the findings record exists with real numbers and the saved responses it rests on; total spend is stated from the API's usage figures; each design assumption in `0002`, `0003` and `0005` is marked confirmed or changed.

**Log:**

### 2026-11-18, Phase 1 on `phase-1-citations-spike`

**Transcripts.** `spikes/transcripts/01-korvath-greenhouses.txt` (63 turns, 832 words) and `02-hartwell-lane-correction.txt` (18 turns, 265 words, timestamps, a figure corrected from 4,800 to 4,300). A web search for each invented company name found no business of that name. The owner read and approved both as written before any call.

**Go-ahead.** The owner approved the paid spike: about 16 calls, about $1, hard stop at $3, key added to `.env` by the owner. Refusals: follow `0005`, no fallback model.

**What ran.** `spikes/citations_spike.py`, from `backend/` with the `live` group: 15 draft calls, 2 extract calls, 1 judge call, and 1 unbilled request that must fail. That is 18 billed calls, two more than "about 16": the extract and judge calls were added so the cost of a whole run is measured, which the owner asked for. The script sends nothing without `--yes-spend`, checks the running total before each call, and skips any call whose result is already saved. Afterwards `uv sync --locked` removed the SDK from the backend environment again.

**Library note.** Current Anthropic guidance is to enable a server-side fallback model for declined requests. The spike follows `0005` instead (no fallback), by the owner's decision.

**Findings:** `docs/decisions/0012-citations-spike-findings.md`. In short: citations and thinking combine; pointers are always valid and tight; a cited block is part of a sentence, so the unit of the ground check has to be the sentence; the headline is never cited; the corrected figure was reported correctly in all six drafts; Sonnet is the right writer; one run costs about 7 cents.

**The record proposes changes to `0003` and the spec** (the unit, what a name may be checked against, the headline). Per this phase's last step, those records are **not edited**: the proposals wait for the owner, and Phase 3 does not start until they are decided.

**Gate evidence.**

Spend, from the API's usage figures, summed over the saved results:

```
$ cd backend && uv run --locked --group live python ../spikes/citations_spike.py draft --yes-spend
...
ok    draft/t2-turn-opus-medium: stop=end_turn model=claude-opus-5-5 in=1890 out=1184 $0.0312 11.2s  total=$0.3783
Total spent so far, from the API's usage figures: $0.3783
$ ... extract --yes-spend
ok    extract/t1-sonnet-low: stop=end_turn model=claude-sonnet-5-5 in=3451 out=1041 $0.0173 8.1s  total=$0.3956
ok    extract/t2-sonnet-low: stop=end_turn model=claude-sonnet-5-5 in=1686 out=460 $0.0080 4.4s  total=$0.4036
$ ... judge --yes-spend
ok    judge/t1-opus-medium: stop=end_turn model=claude-opus-5-5 in=2356 out=1171 $0.0328 11.5s  total=$0.4364
Total spent so far, from the API's usage figures: $0.4364
```

The request that must fail:

```
error check400/citations-with-schema: HTTP 400 {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Citations cannot be enabled when output format is set. Please disable citations on uploaded document blocks.'}, ...}
```

The saved responses the record rests on: 19 files under `spikes/results/` (15 draft, 2 extract, 1 judge, 1 error), each holding the raw request, the raw response, the request id, latency and cost. The numbers in the record are reproduced, with no key and no network, by:

```
$ python3 spikes/analyze.py
label | think tok | words | cited | uncited(words) | uncited share | headline cited | ...
t1-sentence-sonnet-medium-a | 0 | 311 | 22 | 10 | 0.167 | False | ...
t1-sentence-opus-medium | 481 | 355 | 21 | 22 | 0.473 | False | ...
...
total $0.4364
```

Each assumption in `0002`, `0003` and `0005` is marked in the record's three tables. One row is neither confirmed nor changed: the three typed model errors in `0005` (refusal, truncation, model mismatch) did not occur in 18 calls, so they are marked unverified and carried to Phase 4. **The gate's wording asks for "confirmed or changed"; whether "unverified, carried forward" is acceptable for that one row is the owner's call when reviewing the pull request.**

**Reviewer** (fresh context, over the staged diff, run alone in the folder). Its verdict: "No blocking findings on security, spend or the architecture rules. Several figures and verdicts in the findings record (0012) are wrong or claim more than the data shows. One bug in the analysis script changes a number that appears in the record." It recomputed all 18 costs from usage (total $0.4364), confirmed the headline, quotation, judge and corrected-figure findings from the saved files, and confirmed no key in any saved file, that the script cannot spend without its flag, and that the SDK is still outside the base set. Findings as reported, all non-blocking, and what I did:

1. *Bug in `analyze.py`: the first word of a sentence is never checked as a name.* Two wrongly kept sentences; "Opus medium, per sentence, t2" should read fail names 4, kept 7. **Fixed:** the first word is now checked unless it is on a short list of ordinary sentence openers; the analysis was rerun and the record's table and "worst draft kept" updated. The Sonnet rows the conclusions rest on did not change, except the per-turn row (21 kept, 87%, was 22 and 91%).
2. *The record says the rules of `0003` were "applied as written"; only rule 1 and a rough rule 2 were.* **Fixed:** the record and the script now say exactly which rules the table applies.
3. *Wrong or too-narrow figures:* cited text "13 to 17 words" (it is 10 to 19); "two shared a headline" (all three did); the Opus comparison held only at `medium`; "0 cited blocks with more than one sentence" hid 4 Opus drafts with one such block. **Fixed,** each with the full range, and the Opus `low` and per-turn drafts are now in the table.
4. *The thinking verdicts claim more than the data shows:* seen only on Opus at `medium`, never on the writer. **Fixed:** both rows and finding 1 narrowed.
5. *The verdict on one block per sentence keeps the decision but swaps its reason for an untested one.* **Fixed:** the row now says the stated reason was not borne out on short turns and is untested on long ones. My claim that per turn cannot tell a correction from its figure was wrong and is removed.
6. *Missing from the `0003` table: "the fix is a better draft prompt, not a looser rule", which recommendation 2(b) departs from.* **Fixed:** the row is added, option (b) is labelled a departure, and the recommendation is now (a) with (c) measured in Phase 4. Four smaller missing rows added.
7. *The status line and the conclusion disagree about `0002`.* **Fixed.**
8. *The gate says "confirmed or changed"; the record adds a third label.* **Not mine to settle:** raised for the owner above.
9. *A Phase 0 box is ticked for work that was skipped.* **Fixed:** the step text now says so.
10. *The spike script can undercount spend on a timeout, and a retry can bill twice.* **Fixed:** no retries, and any other failure is recorded at the worst-case cost so the stop counts it. It did not happen in this run.
11. *A depot's name in transcript 2 is also a real software company's name; used here as a depot's name, low risk.* **Left as is and raised for the owner:** the owner approved the transcript as written, and renaming it now would mean the 6 saved transcript 2 responses no longer match their transcript (re-running them costs about 12 cents).

**Verifier** (run after the reviewer had finished, alone in the folder; no live call, no `.env`).

| # | What it did | Expected | What happened | Result |
|---|---|---|---|---|
| 1 | `make check` | Exit 0, no spike or live access | `EXIT 0`; the output never mentions spikes or the SDK | pass |
| 2a | `python3 spikes/analyze.py` | Runs clean, `summary.json` byte-identical | Exit 0; `shasum` `cab46683c977...` before and after | pass |
| 2b | First table of `0012` against the printed rows | Numbers match | Sonnet medium, t1: thinking 0, 0, 0; words 311, 331, 325; cited blocks 22, 23, 22; uncited share 0.167, 0.051, 0.157; cost $0.0207, $0.0211, $0.0210. Headline cited: False in all 15. Opus and transcript 2 columns also match | pass |
| 2c | Sentence-level table, every row | Match | Sonnet medium, t1: 22/23/22 sentences, 18/20/19 kept, 80%/86%/87%. Opus medium, t2: 12 sentences, 4 name fails, 7 kept, 60%. All other rows match | pass |
| 2d | Total printed by the analysis | $0.4364 | `total $0.4364` | pass |
| 3 | Its own sum of `cost_usd` over `spikes/results/*/*.json`, and a file count | $0.4364; 15, 2, 1, 1 | 0.43644 (draft 0.3783, extract 0.0253, judge 0.0328, check400 0); 15 draft, 2 extract, 1 judge, 1 error | pass |
| 4a | `cd backend && uv run --locked python ../spikes/citations_spike.py plan` | Lists calls, sends nothing | Listed 18 calls, sent nothing | pass |
| 4b | The same script with `draft` and no spend flag | Nothing sent, no file changes | Exit 0; checksum of every file under `spikes/results/` unchanged | pass |
| 4c | Does the output show that saved calls would be skipped | Skips shown | **Not shown:** the dry run printed "would send" for calls that already have a result. The skip exists only on the spend path, which it was forbidden to run, so it confirmed the skip by reading the code | **fail (minor)** |
| 4d | `cd backend && uv run --locked python -c "import anthropic"` | Fails | `ModuleNotFoundError: No module named 'anthropic'` | pass |
| 5a | Read `draft/t1-sentence-sonnet-medium-b.json` | Headline not in a cited block | The headline block has no citations | pass |
| 5b | Read `draft/t2-sentence-sonnet-medium.json` and `draft/t2-turn-opus-medium.json` | 4,300 as the fact, 4,800 only as the earlier figure or forecast | Holds in both | pass |
| 6 | `spikes/results/check400/citations-with-schema.json` | HTTP 400 with the quoted message | `status: 400`, the message as quoted, `cost_usd 0.0` | pass |
| 7 | `git status --short` and the checksum, before and after | Unchanged | Identical | pass |

Its one finding (4c): the dry run overstated what would be sent. **Fixed:** the listing now marks a call that already has a result as saved and says how many would actually be sent, and `plan` lists the judge call too:

```
$ cd backend && uv run --locked python ../spikes/citations_spike.py plan | tail -3
saved      extract/t2-sonnet-low: already has a result, would be skipped
saved      judge/t1-opus-medium: already has a result, would be skipped
19 calls listed, 0 would be sent. Spent so far: $0.4364. Pass --yes-spend to send.
```

It also noted that the gate-evidence block above shows commands with their output abbreviated by `...`; that is deliberate, and the full figures are in the saved files.

What the verifier could not exercise: anything on the live path (the skip, the spend stop, writing results), since it may not spend; whether the saved responses are genuine API output (each carries its request id); the findings that need a reader, namely the 10 exact quotations, the bracket edits and the judge's four verdicts (the reviewer recounted those); and the three typed model errors, which never occurred.

**Gate: passed, 2026-11-18, with one point for the owner.** The findings record exists with real numbers and the saved responses it rests on; total spend is stated from the API's usage figures ($0.44); every assumption in `0002`, `0003` and `0005` is marked. The point for the owner is the one row marked unverified instead of confirmed or changed (above).

### 2026-11-18, after the owner's review of Phase 1

- Pull request #2 merged by squash at the owner's instruction (`1cee60f`).
- **The owner's decisions** on the points `0012` raised are recorded at the end of `0012`. `decisions/0003` and `docs/SPEC.md` are edited to match: the unit is the sentence; rule 2 stays strict, with the prompt change tried in Phase 4; the model writes the headline and it is checked against the kept body, falling back to the transcript's title with the failure in the trace.
- **The headline rule, assessed before writing it in.** It is sound and practical, and weaker than a sentence's check: a headline has no citation of its own, so code derives its support from the body. It stops a headline introducing a number, date or name the grounded body lacks; it cannot stop grounded facts being combined into something nobody said. The judge (J1) and the correction case (E6) are extended to the headline to cover that, and the spec says which line is checked this way.
- **The depot's name in transcript 2** was changed to an invented one (a web search found no use of the new name) and the seven calls that used transcript 2 were re-run: $0.12, total Phase 1 spend $0.55. The findings did not change in kind; the transcript 2 figures in `0012` are updated, and its rule 4 row now says the rule was not exercised by a real response. The SDK was removed from the backend environment again afterwards.
- **The gate's wording:** the owner accepted "unverified, carried to Phase 4" for the three typed model errors.
- The cost table at the top of this file now carries the measured figures.

---

## Phase 2: walking skeleton on the host

Proves the host before anything is built on it. No pipeline yet.

- [x] A dummy event stream route that emits five typed events over about ten seconds and ends with a terminal event.
- [ ] Ask the owner, then connect two Vercel projects to the repository (`frontend/`, `backend/`) and deploy. Point the old paused frontend project at the new repository or create a new one: owner's choice at that moment. *Deployed, to two new projects. Not yet connected to the repository: Vercel's GitHub app has no access to it, which only the owner can grant (see the log).*
- [x] Show on the deployed backend: the stream arrives event by event, not in one lump; the cold start time; the `anthropic` package is absent from the deployed dependency set; a scratch SQLite file can be created and read.
- [x] Frontend calls the deployed `/health` across origins with CORS limited to its own origin.

**Gate:** timestamps from a real request to the deployed stream show events arriving spread over time; cold start measured; the deployed dependency list pasted without `anthropic`. If the stream is buffered or the runtime does not fit, stop and write the hosting record's replacement (the Fly.io fallback, about $2.35 a month) for approval.

**Log:**

### 2026-11-18, Phase 2 on `phase-2-walking-skeleton`

**What was built.** Backend: `GET /skeleton/stream` sends five typed events two seconds apart and then a terminal one, as data-only events with the tag in the JSON body, the union one named schema (`SkeletonEvent`); a failure part-way still ends in `run_failed` with a code and no exception text, and the reason is logged on the server. `GET /skeleton/runtime` reports the Python version, the instance's uptime, whether the `anthropic` package can be found, every installed package, and the result of creating, writing and reading back a SQLite file in the scratch folder. CORS is limited to the origins in `APP_CORS_ORIGINS`; a wildcard or a malformed origin is refused when the settings load. Frontend: the top bar shows whether the browser can reach the backend's `/health` and in which mode, a call that only succeeds if CORS allows the page's origin.

**The skeleton routes are off by default** (`APP_SKELETON_ROUTES`), because they are public, unmetered, and one lists what is installed. They are switched on for the hosted backend so this gate can be checked. Phase 5 deletes them (step added there), and Phase 8's gate now requires that none answers.

**Deployment, with the owner's go-ahead.** Two new projects on Vercel Hobby, in the owner's personal scope:

| | Project | Address | Root | Settings |
|---|---|---|---|---|
| Backend | `article-agent-api` | https://article-agent-api.vercel.app | `backend/` | framework `fastapi`, Python 3.14 from `.python-version`, region `iad1`, `APP_MODE=demo`, `APP_CORS_ORIGINS=https://article-agent-web.vercel.app`, `APP_SKELETON_ROUTES=1` |
| Frontend | `article-agent-web` | https://article-agent-web.vercel.app | `frontend/` | framework `nextjs`, Node 24.x, `NEXT_PUBLIC_API_URL=https://article-agent-api.vercel.app` |

- **New projects, not the old one.** The plan left "point the old paused frontend project at this repository, or create a new one" to the owner at that moment; the owner asked for the phase to run without waiting, so the choice that changes nothing existing was taken. The old `article-agent` project is untouched. Renaming or repointing later is a settings change.
- **Deployed from this machine with the Vercel CLI, not from GitHub.** `vercel git connect` failed for both projects: "Failed to connect nkanyi-so/article-agent to project ... make sure ... you have access to the repository if it's private." Vercel's GitHub app has not been given access to this private repository, and granting it is a GitHub setting only the owner can change. **Until that is done, a merge to `main` deploys nothing**; the line at the top of this file says what is true today. Each project's root folder is already set, so once access is granted, `vercel git connect` (or the dashboard) finishes the job.
- **A project made from the command line has no framework set**, so the first deploy of each built nothing and served 404. `backend/vercel.json` and `frontend/vercel.json` now name the framework.
- Nothing here costs money: both projects are on Hobby.

**Gate evidence.** All from the deployed backend, after the final deploy.

```
$ date -u; curl -sN https://article-agent-api.vercel.app/skeleton/stream   (each line stamped with its arrival time on this machine)
2026-11-18T19:55:55Z
+ 0.65s  data: {"seq":0,"at":"2026-11-18T19:55:55.909+00:00","type":"run_started"}
+ 2.64s  data: {"seq":1,"at":"2026-11-18T19:55:57.911+00:00","type":"stage_started","stage":"first"}
+ 4.64s  data: {"seq":2,"at":"2026-11-18T19:55:59.912+00:00","type":"stage_completed","stage":"first"}
+ 6.72s  data: {"seq":3,"at":"2026-11-18T19:56:01.914+00:00","type":"stage_started","stage":"second"}
+ 8.66s  data: {"seq":4,"at":"2026-11-18T19:56:03.915+00:00","type":"stage_completed","stage":"second"}
+10.65s  data: {"seq":5,"at":"2026-11-18T19:56:05.916+00:00","type":"run_completed"}

$ curl -s https://article-agent-api.vercel.app/health
{"status":"ok","mode":"demo","version":"0.1.0"}

$ curl -s https://article-agent-api.vercel.app/skeleton/runtime
python 3.14.10 | uptime_s 33.937 | anthropic_installed False | scratch_sqlite {'ok': True, 'rows_read': 1}
28 distributions: annotated-doc==0.0.7, annotated-types==0.8.0, anyio==4.16.0, awslambdaric==4.2.2, boto3==1.42.97, botocore==1.42.97, click==8.5.1, fastapi==0.164.0, h11==0.16.0, idna==3.20, jmespath==1.1.0, opentelemetry-api==1.45.2, pip==26.2.2, pydantic==2.14.3, pydantic-settings==2.16.3, pydantic_core==2.50.4, python-dateutil==2.9.0.post0, python-dotenv==1.2.4, s3transfer==0.16.0, simplejson==4.2.0, six==1.17.0, snapshot-restore-py==1.0.0, starlette==1.10.0, typing-inspection==0.4.5, typing_extensions==4.16.0, urllib3==2.8.0, uvicorn==0.54.0, vercel-runtime==0.25.0

$ curl -s -D - -o /dev/null -H 'Origin: https://article-agent-web.vercel.app' https://article-agent-api.vercel.app/health | grep -i -E '^HTTP|access-control'
HTTP/2 200 
access-control-allow-origin: https://article-agent-web.vercel.app
$ the same with Origin: https://elsewhere.example.com
HTTP/2 200 
```

- **The stream arrives event by event:** six events, each reaching this machine about two seconds after the one before, matching the server's own `at` times. It is not buffered.
- **The deployed dependency set has no `anthropic`** and no development tools either: 28 packages, which are the base set (`fastapi`, `pydantic`, `pydantic-settings`, `uvicorn`), their dependencies, and what Vercel's Python runtime adds (`vercel-runtime`, `awslambdaric`, `boto3` and its dependencies, `opentelemetry-api`, `pip`). Vercel's build log says "Installing required dependencies from uv.lock" with uv 0.13.5; it installed neither the `dev` nor the `live` group. That is observed behaviour, not something this repository configures, so Phase 8's gate checks the list again.
- **A scratch SQLite file can be created, written and read back** on the host.
- **CORS:** the frontend's origin gets `access-control-allow-origin`; another origin gets none, so a browser would block it.
- **In a real browser:** headless Chrome loading https://article-agent-web.vercel.app shows `API demo · 0.1.0` in the top bar, so the cross-origin call from the deployed page succeeds.
- **With the switch off the skeleton routes do not exist on the host:** one deploy went out before the switch was set, and `/skeleton/runtime` answered 404 while `/health` answered 200.

**Cold start.** A request straight after a deploy is not cold: the platform had already started an instance (its uptime was 12 s at the first request). So the backend was left with no traffic from 19:56:25Z, and one request was timed at 20:14:57Z, 18.5 minutes later:

```
first request: status=200 connect=0.022267s tls=0.096286s first_byte=1.565094s total=1.565666s
instance uptime at that request: 0.214 s
warm request: first_byte=0.374555s total=0.374930s
warm request: first_byte=0.466571s total=0.467027s
warm request: first_byte=0.367900s total=0.368227s
```

The instance was 0.2 seconds old when it answered, so this was a cold start. **A cold request took 1.57 s to the first byte against 0.37 to 0.47 s warm: a cold start costs about 1.1 to 1.2 seconds**, measured once, from the owner's machine to the `iad1` region, with only `/health`-sized work to import. It will grow when the app seeds its runs at startup (Phase 5), so Phase 8 measures it again.

A second reading, taken at 20:48:09Z after about 30 minutes with no traffic (the verifier's last request was at about 20:18Z), agrees:

```
first request: status=200 connect=0.020799s tls=0.084394s first_byte=1.843143s total=1.845346s
instance uptime at that request: 0.206 s
warm request: first_byte=0.337298s total=0.337696s
warm request: first_byte=0.360478s total=0.360843s
warm request: first_byte=0.369670s total=0.370087s
```

Two cold starts, 1.57 s and 1.84 s to the first byte, against 0.34 to 0.47 s warm.

**Verdict on the host: Vercel Hobby holds.** The stream is not buffered, the cold start is about a second, the SDK is absent, and the scratch disk works. The Fly.io fallback in `0009` is not needed.

**Reviewer** (fresh context, over the first deploy's code and the decisions commit, run alone and told not to touch the deployed address). Its verdict: "There are no blocking findings for the Phase 2 code." It confirmed for itself that the stream cannot leak exception text, that only `Exception` is caught so a client that has gone is not sent anything, that each test fails without the behaviour it names, that importing the app reads no `.env` under test, and that no check was weakened. Findings as reported, and what I did:

1. *The CORS "never `*`" rule is only a comment:* a host variable set to `*` would allow every origin. **Fixed:** the setting refuses a wildcard, a path or a bare host when it loads, with tests.
2. *The failure path drops the exception instead of keeping it on the server.* **Fixed:** it is logged; the test asserts the reason is in the server log and not in the event.
3. *The skeleton routes are public, unmetered, and the plan never says when they go.* **Fixed:** they are registered only when `APP_SKELETON_ROUTES` is on (default off, tested), a Phase 5 step deletes them, and Phase 8's gate requires that none answers. They are on for the hosted backend for now, so this gate can be checked and re-checked by the owner; switching them off is one setting.
4. *The `dev` group may be installed on the host; check the measured list.* **Checked:** the deployed list has no pytest, mypy, ruff or httpx. No change needed; recorded above as observed behaviour.
5. *`backend/.vercelignore` does not exclude env files.* **Fixed,** and a root `.vercelignore` added for deploys from the repository root.
6. *The frontend silently falls back to localhost in production if the backend's address is unset.* **Fixed:** a build on the host without it fails (`next.config.ts`), and a trailing slash is stripped.
7. *`0012`'s status line contradicts itself after the owner's decisions.* **Fixed.**
8. *The headline rule's "superseded figure" has no definition code can apply,* and the spike shows the obvious one fails. **Fixed in `0003` and the spec:** no number in the headline may appear in the text of a segment extract named as superseded. Blunt on purpose; it can reject a correct headline, which then falls back to the title. Also stated: a headline with no number, date or name is judged against the whole kept body; a fallback title is not scored; the architecture's `ground` row now lists the headline's failure record. **This refines the owner's headline decision to make it checkable; flagged for the owner in the pull request.**
9. *The depot's old name, also a real company's, is still in `main`'s history.* **Recorded** under the Phase 9 history-check step: rewrite `main` or accept it explicitly before the repository goes public.

After these fixes both projects were redeployed, and every figure in the evidence above is from that final deploy.

**Verifier** (run alone, after the cold-start measurement; GET and OPTIONS only against the deployed addresses). A is the deployed backend, F the deployed frontend.

| # | What it did | Expected | What happened | Result |
|---|---|---|---|---|
| 1 | `make check` | Exit 0 | `EXIT=0`; 19 backend tests, 10 frontend tests, build ok | pass |
| 2a | `curl -sN A/skeleton/stream`, lines stamped on arrival | Spread over about 10 s, terminal event last | +0.40, 2.39, 4.39, 6.39, 8.39, 10.39 s; six events ending `run_completed`; `content-type: text/event-stream` | pass |
| 2b | The same again | The same | +0.38, 2.63, 4.38, 6.43, 8.47, 10.42 s | pass |
| 2c | Event format | Data-only, `type` in the JSON | Every event one `data: {...}` line, no `event:` line | pass |
| 3 | `curl -s A/skeleton/runtime` | No `anthropic`, no dev tools, SQLite ok | Python 3.14.10; `anthropic_installed` false; 28 packages, none of `anthropic`, pytest, mypy, ruff, httpx; `scratch_sqlite` ok. List identical to the log's | pass |
| 4 | `curl -s -D - A/health` | 200, demo | `{"status":"ok","mode":"demo","version":"0.1.0"}` | pass |
| 5a | GET with the frontend's origin | Allow-origin for it | `access-control-allow-origin: https://article-agent-web.vercel.app` | pass |
| 5b | GET with `https://elsewhere.example.com` and with `http://localhost:3000` | Header absent | Absent for both | pass |
| 5c | OPTIONS preflight from each | Allowed origin accepted, others refused | Frontend origin: 200 with allow-origin, `GET, POST`; the other two: 400, no allow-origin | pass |
| 5d | Was `*` ever returned | Never | Never | pass |
| 6a | `curl -s F/` | 200, real HTML with the status element | 200, `data-testid="backend-status"` present | pass |
| 6b | The page's script files | Contain the backend's address, not localhost | Backend address 2 times, `localhost:8000` 0 times | pass |
| 6c | Headless Chrome on F | Status shows the backend reached | `API demo · 0.1.0` | pass |
| 7 | Unknown route, wrong method on A | 404, 405 | `{"detail":"Not Found"}`, `{"detail":"Method Not Allowed"}` | pass |
| 8a | `make dev` as documented | Up; skeleton routes 404 by default | `/health` 200 demo; both skeleton routes 404; frontend 200 | pass |
| 8b | Stopped by signalling the process group | Ports free | 0 listeners, no leftover processes | pass |
| 8c | `APP_SKELETON_ROUTES=1 APP_MODE=live make dev` | Stream works; still demo | `/health` demo; stream at +0.02, 2.02, 4.02, 6.02, 8.02, 10.03 s ending `run_completed` | pass |
| 9 | Compared with the evidence above | Agreement | Stream, health, runtime list, CORS and browser text all agree | pass |

No defects found. What it could not exercise: the cold start (needs a long idle wait; its own first requests were warm); deploys from GitHub (not connected); the status element's failure state and any browser other than headless Chrome; the stream's `run_failed` path on the host (covered by a unit test only); the skeleton routes switched off on the host (seen once above, by accident, before the switch was set). It also noted that `make dev` reporting demo under `APP_MODE=live` shows the script forcing demo, not the app refusing live; there is nothing live to construct until Phase 4.

**Gate: passed, 2026-11-18.** Timestamps from real requests to the deployed stream show the events arriving spread over ten seconds (mine and the verifier's two runs); the cold start is measured (1.57 s to first byte after 18.5 minutes idle, about 0.4 s warm); the deployed dependency list is pasted and has no `anthropic`. The stream is not buffered and the runtime fits, so the Fly.io fallback is not needed.

**Open, for the owner, not part of the gate:** give Vercel's GitHub app access to the repository so the two projects can be connected and a merge deploys. That step's box stays unticked until then.

---

## Phase 3: ingest and the ground check

Pure code, test-first. Uses the Phase 1 responses as fixtures.

- [ ] Schemas: segment, claim, citation, removed unit, stage record, typed errors (the old hierarchy's shape, new members).
- [ ] Ingest: turn parser, sentence splitter, segment numbering with speaker and source line, the four code refusals.
- [ ] Ground: draft blocks joined and split into sentences, each with the citations of the blocks it overlaps; the four removal rules; removed sentences recorded with a reason; the fewer-than-three failure; the headline checked against the kept body, with the title as fallback and the failure in the trace (`0003`).
- [ ] Tests on real recorded responses and on hand-altered ones (a wrong number, an uncited sentence, a misquote, a claim resting only on a corrected segment). Each must be removed with the right reason.

**Gate:** `make check` exits 0. The test list shows each removal rule failing a hand-altered response and passing the real one. No module in this phase imports a model client.

**Log:**

---

## Phase 4: model seam, extract, draft, runner

- [ ] `ModelClient` interface and its request and response models; the request hash; `FixtureModelClient` (loud miss); `LiveModelClient` with explicit timeout and retries, cost and latency from usage, typed errors for refusal, truncation and a model mismatch.
- [ ] A test that only the live client module imports `anthropic`, and that demo mode cannot construct it.
- [ ] Extract stage (structured output, validated segment indexes) and draft stage (citable document, no schema). Transcript text only as document blocks or delimited data.
- [ ] Try the draft prompt change from `0012` (ask the model to cite every sentence it drew on, including the one naming the subject) and measure the removal rate with and without it. Asks first, a few cents.
- [ ] The three typed model errors (refusal, truncation, model mismatch) tested against hand-built responses: Phase 1 never saw one.
- [ ] The runner: stage order, stage records in memory, events, the terminal-event guarantee, the run ceiling.
- [ ] Write the other two seeded transcripts. Ask the owner, then record all three with the live client (about $1).
- [ ] A command that runs a seeded transcript end to end in fixture mode and prints the article with its citations and removed units.

**Gate:** `make check` exits 0 with the three seeds running end to end from recordings. Editing one word of a prompt makes the fixture client fail with a miss (show it, then undo). The recording run's spend is stated.

**Log:**

---

## Phase 5: stored runs, replay, API, guards

First working draft.

- [ ] Delete the Phase 2 skeleton: the `/skeleton/*` routes, `app/skeleton.py`'s routes and the `APP_SKELETON_ROUTES` setting, on the host too. A test asserts no `/skeleton` path is in `app.openapi()`. The event shapes move to the real stream.
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

**Gate:** verifier table against the hosted address: page loads with no key, seeded run streams, claim click works, replay works, removed units visible. The deployed backend's dependency list has no `anthropic`. No `/skeleton` route answers on the hosted address.

**Log:**

---

## Phase 9: release

- [ ] README with the seven profile sections; every claim traced to code or to a result file.
- [ ] Reviewer in security mode over the whole repository; fix every blocking finding.
- [ ] History check against the synthetic-data rule and a full-history secret scan. Known already: a depot in the second spike transcript carried a name that is also a real software company's, in commits `74f3425` and `1cee60f` on `main` (replaced in `0effa8c`). Before the repository is made public, either `main` is rewritten to remove it or the owner explicitly accepts it as a depot's name.
- [ ] Ask the owner, then make the repository public. Turn on branch protection on `main` (no force-push, the `check` and `secrets` jobs must pass) and show it is on: carried from Phase 0, where GitHub refused it on the private repository.
- [ ] Walkthrough video (owner).

**Gate:** the spec's "Done when", item by item, each with its evidence.

**Log:**
