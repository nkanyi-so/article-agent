# 0006: backend stack

**Status:** proposed, 2026-11-18

**Context.** Versions checked on 2026-11-18 on PyPI and the projects' own pages. They will move; principle 6 applies at the start of each phase.

**Decision.**

| Choice | Version seen | Why |
|---|---|---|
| Python 3.14 | 3.14.10 | In bugfix support; 3.12 and 3.13 are security-only. Offered by the host's Python runtime, supported by FastAPI (3.11 to 3.15) and Pydantic, and already on this machine. |
| FastAPI | 0.164.0 | First-class server-sent events since 0.135.0 (`fastapi.sse`), with keep-alive pings every 15 seconds; an event type declared as the route's `AsyncIterable[...]` return type is validated and documented with Pydantic; `app.openapi()` gives the schema with no server; `lifespan` for startup. |
| Pydantic | 2.14.3 | One set of models for requests, responses, stage records and recordings. |
| pydantic-settings | 2.16.3 | Settings from the environment, with env-file loading switched off under test. |
| Uvicorn | 0.54.0 | Local server. |
| uv | 0.13.9 | Lockfile, Python pinning, dependency groups (the `live` group in `0004`). |
| ruff, mypy (strict), pytest, pytest-asyncio | 0.17.5, 2.4.1, 9.2.0, 1.5.0 | Format, lint, types, tests. |
| pytest-socket | 0.8.1 | Blocks every socket in tests, so the no-network rule is enforced below the HTTP client. This matters because the Anthropic SDK now uses its own HTTP package, which common HTTP mocks do not see by default. |

**Known wrinkles, to handle and not rediscover.**

- Events are sent as data-only with the tag inside the JSON. A route that yields `ServerSentEvent` to set an event name is documented as a bare envelope and loses the payload types.
- FastAPI describes the stream with the `itemSchema` keyword, which the type generator ignores (`0008`).
- What FastAPI does when the client disconnects is implementation, not documentation. The runner's terminal-event and cleanup behaviour gets its own test.
- pytest-socket's per-test block can be bypassed by session-scoped fixtures that open sockets first. There are none; keep it that way.
- FastAPI releases almost daily. The lockfile pins it; upgrades are deliberate.

**Consequence.** Nothing exotic, all current. Quart, the owner's usual backend framework, was not chosen because FastAPI's typed event stream and schema output are what make generated frontend types possible.
