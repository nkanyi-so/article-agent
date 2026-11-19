# 0007: SQLite through the standard library; stage records are the one mechanism

**Status:** accepted by the owner on 2026-11-18; built in Phase 5 (see "As built" at the end).

**Context.** The old project persisted nothing and ran its stages inline in one generator, so replay was impossible. Three things are wanted: showing a saved run, re-running from a stage, and a hosted demo that works from recordings.

**Decision.**

- Every stage writes a record with its input and output; every model call writes its raw request and response. Showing a run reads these. Re-running from stage N copies the records before N into a new run and executes N onward from the stored input. The demo's recordings are the same request and response pairs.
- Storage is SQLite, accessed with the standard library's `sqlite3` behind a small `Store` class whose methods run in a worker thread. No ORM, no async driver.
- The rate limit and the daily budget read the same database, so there is no second store and no extra dependency.

**Why not an async driver or an ORM.** Every async SQLite option is a thread underneath; SQLAlchemy's documentation says of `aiosqlite`, "It does not actually use non-blocking IO" (https://docs.sqlalchemy.org/en/20/dialects/sqlite.html). FastAPI's own SQL tutorial uses a synchronous engine. Four tables with JSON columns validated by Pydantic do not need a mapping layer.

**Consequence.**

- Zero storage dependencies and nothing to run locally.
- On the proposed host the filesystem is scratch space per instance (`0009`): seeded runs are rebuilt at startup by running the pipeline, and a run a visitor starts lasts as long as that instance. The UI says so. Locally, and on any host with a disk, runs persist.
- Revisit if runs must be durable on the hosted site: that is the Fly.io fallback in `0009`, or a hosted database, each of which adds something that can lapse.

**As built in Phase 5.**

- Each store call opens its own connection. The streaming code and the seeding call the store through a worker thread; the reading routes are plain functions, which the framework runs in a worker thread. Nothing waits on the database on the event loop.
- The guard is one transaction that takes the write lock first (`Store.admit_run`): it counts the address's recent starts, reads the day's live cost, and records the start. Requests that arrive together are therefore decided one after another. An earlier version checked and recorded in separate steps, and ten parallel requests all passed a limit of two.
- The daily budget also holds a worst-case amount for each live run still going, so runs started together cannot all read the same recorded total.
- After every event of a run its whole state is written again (status, stage records, model calls). Simple and correct; a run has at most four stages and two calls.
- Seeded runs are created on first use, not at start-up (see the architecture).
- Runs besides the seeded ones are pruned to the newest 200; rate events older than a day are deleted.
- The hosted demo's address handling is not settled: with `APP_TRUST_PROXY` off, what the app sees as the caller's address on Vercel has not been checked, and may be one shared address, in which case every visitor shares one allowance of ten runs a minute. Turning it on is a Vercel setting, so it waits for the owner (Phase 8 at the latest).

