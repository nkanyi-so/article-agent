# Profile: LLM application

Add these on top of the base harness when the product calls a language model at run time.

## Rules where they suffice, the model only for judgment

Anything that can be computed, validated or enforced in code is. The model routes, words and judges. It does not do arithmetic, and its output is validated before use. Treat model output as untrusted input.

## Fixture client

The model sits behind one interface with two implementations: live and fixture. Tests, CI and `make check` use the fixture client only. A live run is a separate command that is never in the allow list, so it always asks.

## Evals

- `docs/SPEC.md` ("How we know it works") holds the eval plan: what is checked exactly, what needs a judge, what must be refused, and the numbers that count as passing.
- `make check` runs the evals in fixture mode. The paid, live eval run is its own command and asks first.
- Never loosen an eval or its threshold to make a gate pass.

## Spend

Log cost and latency per call. Anything public has a rate limit and a daily budget cap, and the reviewer checks both.
