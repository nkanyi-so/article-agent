# 0008: frontend types generated from the OpenAPI schema

**Status:** proposed, 2026-11-18

**Context.** The ported frontend has two hand-copied type files mirroring a backend that no longer exists, and the old rule was "update them by hand". Checked on 2026-11-18:

- `openapi-typescript` 7.13.0 (npm): supports OpenAPI 3.0 and 3.1, writes one types-only file, and has `--check`, "Check that the generated types are up-to-date" (https://openapi-ts.dev/cli). Its last release was February 2026; its peer dependency is TypeScript 5, which the frontend uses.
- It does not read `itemSchema`, the keyword FastAPI uses to describe a `text/event-stream` response. A pull request adding it has been open since March 2026 (https://github.com/openapi-ts/openapi-typescript/pull/2683).
- `@hey-api/openapi-ts` is at 0.99.0, not yet 1.0, needs Node 22.18 or later, generates a whole client and breaks often.
- The brief's scratch experiment found that a named discriminated union appears in the schema as one named component, and that Pydantic unions come out as TypeScript unions with a required tag. That was one run, not documentation; Phase 5 repeats it.

**Decision.**

- A script writes `openapi.json` from `app.openapi()` with no server and no key.
- `openapi-typescript` generates one file in the frontend. `make check` runs it with `--check`, so drift fails the gate.
- The event union is a named model. The stream's response type comes out as `unknown`; the frontend imports the union from the generated components and applies it where it parses an event.
- The generated file is a protected path. It is never edited by hand.

**Consequence.**

- The hand-copy rule and both hand-written files go.
- Parsing an event is still an unchecked cast at run time. A small runtime guard on the tag, plus a test with a malformed event, covers the part the types cannot.
- The generator is a development dependency only. If it is abandoned, the fallback is generating from Pydantic's JSON Schema, which the brief found weaker (the tag came out optional).
- Revisit when the generator supports `itemSchema`.
