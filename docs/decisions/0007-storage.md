# 0007: SQLite through the standard library; stage records are the one mechanism

**Status:** proposed, 2026-11-18

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
