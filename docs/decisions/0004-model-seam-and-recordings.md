# 0004: one model interface, recordings keyed by request hash, the SDK as an optional group

**Status:** proposed, 2026-11-18

**Context.** The old project had one concrete live client and no seam; every run needed keys before the first stage, and tests were safe only because each mocked by hand. The model client needs a live and a fixture implementation, with tests, CI and `make check` on the fixture one. The hosted demo must run with no key and must not be able to spend.

**Decision.**

- One interface, `ModelClient.complete(request) -> response`, with Pydantic request and response models that carry everything a stage needs, including citation blocks.
- `LiveModelClient` is the only module that imports `anthropic`. A test enforces it.
- `FixtureModelClient` looks up a recording by the SHA-256 of the canonical request (model, system, content blocks, schema, `max_tokens`, effort). A miss raises. It never falls back to a live call.
- A recording stores the raw request and response of one live call. Saved runs keep the same pair per call, so a recording, a saved run and a replay are one format.
- `anthropic` is in an optional `live` dependency group. The base set, which is what the hosted demo installs, does not contain it.
- The mode is chosen once in the app factory. Demo mode cannot construct the live client.

**Why hash the whole request.** Any prompt edit then invalidates the recording visibly instead of replaying an answer to a question that is no longer being asked. The pipeline builds the real request in every mode, so the demo exercises the real prompt-building code.

**Consequence.**

- "The hosted demo cannot spend" is a property of what is installed, checkable from the deployed dependency list, and does not rest on a setting being right.
- Every prompt edit needs a paid re-record (about $1 to $3) before `make check` passes again. This is intended friction; it is also the main thing that will slow prompt iteration during the eval work, where it is done in live mode against the eval set first and recorded once at the end.
- Recordings are committed, so they are covered by the synthetic-data rule and the secret scan.
- Determinism in tests comes from recordings. Sampling settings cannot provide it: `temperature`, `top_p` and `top_k` are rejected under the API version current SDKs send (`0005`).
