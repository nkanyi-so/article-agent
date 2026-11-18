# Runtime dependencies

One line of reason per direct runtime dependency. Nothing is added without a line here. Versions are what was current on 2026-11-18; the lockfiles hold the truth.

## Backend, base set (what the hosted demo installs)

| Package | Reason |
|---|---|
| `fastapi` | HTTP routes, the typed event stream and the OpenAPI schema the frontend types are generated from. |
| `pydantic` | One set of models for requests, responses, stage records and recordings; validates model output before use. |
| `pydantic-settings` | Settings from the environment, with env-file loading that can be switched off under test. |
| `uvicorn` | Runs the app locally. |

## Backend, `live` group (never installed on the hosted demo)

| Package | Reason |
|---|---|
| `anthropic` | The official SDK, imported by the live model client only. |

## Frontend

| Package | Reason |
|---|---|
| `next`, `react`, `react-dom` | The app, ported from the old project. |

## Considered and not added

| Package | Why not |
|---|---|
| An agent framework | A fixed five-stage pipeline does not need one (`0001`). |
| `sqlmodel`, `sqlalchemy`, `aiosqlite` | Four tables through the standard library (`0007`). |
| `slowapi`, `limits`, `fastapi-limiter` | The rate limit and the daily budget are one small counter over the database already in use; none of the three has released in five months. |
| `httpx` at run time | No outbound HTTP besides the SDK's own. It is a test dependency only. |
| A sentence-splitting or NLP library | A rule-based splitter with tests is enough for `Speaker: text` transcripts and adds nothing to the hosted bundle. |
| `@hey-api/openapi-ts` | Pre-1.0, frequent breaking changes, generates a client that is not needed (`0008`). |

Development-only tools (tailwindcss for the base stylesheet, ruff, mypy, pytest, pytest-asyncio, pytest-socket, httpx for the test client, eslint, typescript, vitest, openapi-typescript) are listed in `0006`, `0008` and `0011`.
