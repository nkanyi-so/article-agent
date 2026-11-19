# Architecture: article-agent

Written by the intake on 2026-11-18. Status: proposed. Nothing here is built yet; `frontend/` is ported code from the old project. (`reference/`, the old eval code kept to read, was deleted in Phase 6 when the new evals replaced it.)

## Shape

```
frontend (Next.js)  ──HTTP + event stream──►  backend (FastAPI)
                                                │
                                                ├─ pipeline: ingest → extract → draft → ground → evaluate
                                                │            code      model     model    code     code + model
                                                ├─ ModelClient ── live (Anthropic)   | fixture (recordings)
                                                ├─ Store ──────── SQLite
                                                └─ guards ─────── rate limit, daily budget
```

A straight pipeline of plain async functions, one per stage. No agent framework (`decisions/0001`).

**The runner** takes a transcript (or a parent run and a stage to restart from), calls each stage in order, writes a stage record before and after each one, and yields events. It is the only place that knows the stage order. It always ends with a terminal event, including on timeout, cancellation and unexpected exceptions.

**Boundaries. Each outside system sits behind one interface:**

| Outside system | Interface | Implementations |
|---|---|---|
| The language model | `ModelClient.complete(request) -> response` | `LiveModelClient` (the only module that imports `anthropic`), `FixtureModelClient` (replays recordings, fails loudly on a miss) |
| The database | `Store` | SQLite through the standard library |
| The clock and ids | passed in | real, or fixed in tests |

`ModelRequest` carries the model id, system text, content blocks (including the citable document), an optional output schema, `max_tokens` and effort. `ModelResponse` carries the content blocks with their citations, the parsed object when a schema was given, the stop reason, the model that served the request, usage and latency. Both are Pydantic models, so a recording is just the two serialised.

**Recordings.** A recording is the raw request and response of one live call, stored in `backend/recordings/` under the SHA-256 of the canonical request. The fixture client rebuilds nothing: the pipeline builds the real request, the hash is looked up, and a prompt edit therefore misses loudly instead of replaying a stale answer.

**Stages**

| Stage | Kind | Input | Output |
|---|---|---|---|
| `ingest` | code | transcript text, title | segments: `index`, `turn`, `speaker`, `line`, `text`; or a refusal |
| `extract` | model, structured output | segments as delimited data | points (text, segment indexes, kind), corrections (superseded index, by index), disagreements, angle |
| `draft` | model, citations, no schema | custom-content document with one text block per segment, plus the extract result as instructions | the raw response blocks |
| `ground` | code | draft blocks, segments, corrections | claims, one per kept sentence (text, citations, segment indexes, paragraph, any name kept by the first-name rule, and the question each cited answer replied to, added by code as context); removed sentences with reasons; the headline with its supporting sentences, or the fallback title with the headline's failure and its reason |
| `evaluate` | code, then model with structured output | the stored run | an eval report: code verdicts and the judge's per-claim verdicts |

Segment `index` is the block index in the citable document, so a citation's `start_block_index` and `end_block_index` (exclusive) map straight onto segments with no lookup table.

**HTTP surface**

| Route | What |
|---|---|
| `GET /health` | mode, version, store reachable |
| `GET /api/config` | mode, whether paste is enabled, the seeded transcripts, limits |
| `GET /api/seeds/{id}` | a seeded transcript's text |
| `POST /api/runs/stream` | start a run from `{seed_id}` or, in live mode, `{transcript, title}`; responds with the event stream |
| `POST /api/runs/{id}/replay/stream` | re-run from `{from_stage}`; a new run linked to its parent |
| `GET /api/runs`, `GET /api/runs/{id}` | stored runs |

Events are one named discriminated union (`run_started`, `stage_started`, `stage_completed`, `run_completed`, `run_failed`) with the tag in the JSON body, sent as data-only events so the union is documented in the schema.

**Modes.** `APP_MODE=demo` (default) builds the fixture client and refuses pasted text. `APP_MODE=live` builds the live client and needs `ANTHROPIC_API_KEY` and the `live` dependency group. The mode is chosen once, in the app factory.

**Settings** (environment variables, all with defaults that are right for local use):

| Variable | Default | What it does |
|---|---|---|
| `APP_MODE` | `demo` | `demo` or `live`. |
| `ANTHROPIC_API_KEY` | none | Needed in live mode only. |
| `APP_CORS_ORIGINS` | `http://localhost:3000` | Comma-separated origins allowed to call the API. A wildcard is refused. |
| `APP_DATABASE_PATH` | a file in the system's scratch folder | Where the SQLite file lives. |
| `APP_RUNS_PER_MINUTE` | 10 | Runs one address may start in a minute. |
| `APP_DAILY_BUDGET_USD` | 2.0 | Cap on what live calls may cost in a UTC day. |
| `APP_MAX_BODY_BYTES` | 262144 | Largest request body. |
| `APP_MAX_STORED_RUNS` | 200 | Runs kept besides the seeded ones. |
| `APP_TRUST_PROXY` | off | Take the caller's address from the header the platform sets (`x-real-ip`, else the right-most `x-forwarded-for` entry). Off by default, because anywhere else that header is the caller's to choose. |
| `APP_REPLAY_LATENCY` | 0 | In demo mode, wait this fraction of the time each recorded call really took, so a run can be watched. `make dev` sets 0.25. |

## Data model

SQLite, four tables.

- `runs`: `id`, `created_at`, `mode`, `source` (seed, paste, replay), `title`, `seed_id`, `parent_run_id`, `replay_from_stage`, `status` (running, completed, failed), `error`, `pinned`.
- `stage_records`: `run_id`, `seq`, `name`, `status`, `started_at`, `duration_ms`, `input`, `output`, `error`, `copied_from_run_id`. Input and output are JSON, validated by the stage's Pydantic model on the way in and out.
- `model_calls`: `id`, `run_id`, `stage`, `request_key`, `source` (live, fixture), `model_requested`, `model_served`, `request`, `response`, `stop_reason`, token counts, `cost_usd`, `latency_ms`, `attempts`. Also `created_at`, which is what "today" means for the daily budget, and `error`: a call that was billed but whose response could not be used is stored with its cost, its error code and no response.
- `rate_events`: one row per run started, with the caller's address and the time. The rate limit reads it. The daily budget reads `model_calls`: the cost of live calls since midnight UTC, plus a worst-case amount held for each live run still going.

The transcript is the input of the `ingest` record. The article is derived from the `ground` record; it is not stored twice.

Seeded runs are created once per process, on the first request to an `/api` route, by running the real pipeline with the fixture client, under stable ids (`seed-<id>`), so their links always resolve. Not at start-up, so that `/health` answers at once on a cold start. A run still marked running when the process starts was cut off by the last one stopping, and is closed as failed with the error `interrupted`.

Runs other than the seeded ones are pruned to the newest `APP_MAX_STORED_RUNS` (200), so starting runs cannot fill the hosted demo's scratch disk.

## Stack and why

| Choice | Record |
|---|---|
| Plain staged pipeline, angle folded into extract | `decisions/0001-pipeline-and-stages.md` |
| Citations API with one block per sentence for the draft | `decisions/0002-citations-for-the-draft.md` |
| Remove and record, never patch | `decisions/0003-ground-check.md` |
| One model interface, recordings keyed by request hash, SDK as an optional group | `decisions/0004-model-seam-and-recordings.md` |
| Writer and judge models, effort, no sampling settings | `decisions/0005-models.md` |
| Python 3.14, FastAPI, Pydantic, uv, ruff, mypy, pytest | `decisions/0006-backend-stack.md` |
| SQLite through the standard library | `decisions/0007-storage.md` |
| Frontend types generated from the OpenAPI schema | `decisions/0008-generated-types.md` |
| Hosting on Vercel Hobby, demo mode | `decisions/0009-hosting.md` |
| Eval plan and starting thresholds | `decisions/0010-evals.md` |
| Keep the Next.js shell, cut the showcase page, add a test runner | `decisions/0011-frontend.md` |
| Each runtime dependency, one line of reason | `decisions/dependencies.md` |

## Security

The reviewer's checklist in security mode.

- **Auth and exposure.** There are no accounts. Nothing stored is personal: demo runs come only from seeded fictional transcripts. Pasted transcripts exist only in live mode on the owner's machine. CORS allows the frontend's origin only.
- **Spend.** The hosted deployment cannot spend: demo mode, no key, the `anthropic` package not installed. Check the deployed dependency set, not just the setting. In live mode every route that can start a model call depends on the rate limit and the daily budget; a test fails if a new run-starting route lacks them.
- **Secrets.** No key in the repository, the history, logs, error bodies or recordings. Recordings are scanned by the secret scan like any file. `.env` is never read by tests.
- **Untrusted input.** Transcript text reaches a model only inside the citable document or delimited data tags, never spliced into instructions. Size limits are enforced before any model call. Model output is parsed and validated before use; segment indexes from the model are range-checked. The injection case with its canary is in the eval set.
- **Model output in the browser.** Article text and transcript text are rendered as text, never as HTML.
- **Errors.** Clients get a code, a safe message and a request id. No upstream body, stack trace or exception text.
- **Synthetic data.** No real person or company in seeds, fixtures, tests, eval cases, recordings or UI placeholders. `example.com` for any URL. This holds for the git history.
- **Dependencies.** Each runtime dependency has its line in `decisions/dependencies.md`. Lockfiles are committed.
- **Abuse.** Request body size capped. The demo's run-starting routes are rate limited per address to protect compute even though they cannot spend.

## Testing

- `make check` is the one gate: backend format, lint, types, tests and fixture-mode evals; frontend lint, types, tests, build and the generated-types freshness check.
- Tests run with env-file loading off and sockets blocked. A test that needs a key or the network is wrong.
- Core logic is written test-first: the sentence splitter, the ground check, the fixture key, the refusal rules, the runner's terminal-event guarantee, the guards.
- The ground check is tested against real recorded responses and against hand-altered ones (a wrong number, an uncited sentence, a misquote), so it is shown to fail.
- A test asserts that only the live client module imports `anthropic`.
- Frontend tests cover the stream parser (including a stream that closes without a terminal event) and claim-to-segment rendering.

## Deployment

Proposed, and proven in Phase 2 before anything depends on it (`decisions/0009`).

- Two Vercel projects on the Hobby plan from one repository: `frontend/` (Next.js) and `backend/` (FastAPI on the Python runtime), demo mode.
- The backend installs only the base dependency set. Its database is a scratch file created at start and seeded by running the pipeline; runs a visitor starts live as long as that instance does, and the UI says so. Seeded runs always resolve.
- **A merge to `main` deploys both projects once they are connected.** Every deploy, and every change to GitHub or Vercel settings, asks the owner first.
- Fallback if Phase 2 shows the stream is buffered or the runtime does not fit: a small always-on container with a disk on Fly.io, about $2.35 a month, decided by a new record before any switch.
