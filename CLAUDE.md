# article-agent

A public portfolio piece: it turns a meeting or interview transcript into a short article in which every sentence points at the transcript sentences that support it, with a stage-by-stage trace that can be re-run from any stage and an eval score. The reader is an engineer or hiring manager judging whether the author can build a language-model feature that survives production. It is a rebuild on synthetic data. The one claim it has to prove: the model added nothing the speakers did not say, and you can check that.

**Where it actually is:** see the status line at the top of `docs/PLAN.md`. `frontend/` is ported from the old project and still contains its name-lookup UI until Phase 7. `reference/` is old code to read, not to run.

Source of truth, in this order: `docs/SPEC.md` (what), `docs/ARCHITECTURE.md` (how), `docs/PLAN.md` (phases, gates, progress log), `docs/decisions/` (why). If code and docs disagree, stop and say so. Files in `docs/profiles/` (`llm-app`, `portfolio-piece`) are rules for this project too.

## Commands

The `make` targets are created in Phase 0; until then they do not exist.

- `make setup` install backend and frontend dependencies, enable the pre-commit hook (`git config core.hooksPath .githooks`), warn if gitleaks is missing
- `make dev` run backend (demo mode) and frontend locally
- `make check` backend: ruff format check, ruff lint, mypy, pytest, fixture-mode evals. Frontend: eslint, `tsc --noEmit`, vitest, build, generated-types freshness. Must exit 0 before any commit.
- `make format FILE=<path>` format one file. The edit hook calls this; without the target nothing is formatted on edit.

Never run without being asked, every time, with a cost estimate first:

- anything that builds the live model client: the spike scripts in `spikes/`, the recording command, the eval harness in live mode, the backend started with `APP_MODE=live`
- any deploy, and any change to GitHub or Vercel settings
- `git push`, and making the repository public

## Architecture rules

1. No real people and no real companies in seeds, fixtures, tests, eval cases, recordings or UI placeholders. Fictional names and `example.com` only.
2. A unit of the draft that fails the ground check is removed and recorded with its reason. It is never given another citation, reworded, or kept with a warning.
3. Every model call goes through `ModelClient`. Only the live client module imports `anthropic`. Tests, CI, `make check` and demo mode build the fixture client only, and a fixture miss is an error, never a fallback to a live call.
4. Tests never read `.env` and never open a socket. Importing the app needs no key. A test that needs either is wrong.
5. Transcript text reaches a model only as a document block or delimited data, never spliced into instructions. Model output is validated in code before it is used or stored.
6. Every route that can start a model call depends on the rate limit and the daily budget. Demo mode refuses pasted text.
7. Every event stream ends with `run_completed` or `run_failed`. Frontend API types are generated: change the Pydantic model and regenerate, never edit the generated file.

## How phases are built

With `/next-phase`, which holds the working loop. If you are working on a phase without it, read `.claude/skills/next-phase/SKILL.md` first and follow it. The human merges pull requests; you do not. From Phase 2, a merge to `main` deploys.

## Guardrails

- Never commit secrets. `.env` is ignored; only `.env.example` is tracked.
- No commit without the owner's approval.
- No new direct runtime dependency without one line of reason in `docs/decisions/dependencies.md`.
- Never weaken a test, a check, a type check or an eval threshold to make a gate pass. Say what is failing instead.
- Never call a live or paid service in tests or CI. Use a fake.
- Changes to `.claude/settings.json`, `.claude/hooks/`, `.githooks/` and CI must not weaken a check. You will be asked to confirm each one.
- If a library's current API contradicts these docs, follow the library and note it in the phase log.
- If a gate cannot pass or the spec turns out wrong, stop and say so. Do not work around it.
- Log harness friction in `docs/HARNESS_NOTES.md` as it happens.

## Style

- Commits: Conventional Commits (`type(scope): summary`). One branch and one pull request per phase.
- Python 3.14: type hints throughout, `async` handlers by default, Pydantic for every request, response and stage model. ruff for format and lint, mypy strict.
- TypeScript: strict mode; explicit types on public API surfaces. ESLint with the Next config. Before writing frontend code, read `frontend/AGENTS.md` and the Next.js guide it points to under `frontend/node_modules/next/dist/docs/`.
- Small functions, plain names. Comments say why, not what.
