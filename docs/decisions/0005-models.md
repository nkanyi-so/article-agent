# 0005: writer and judge models, effort, and what is not set

**Status:** accepted on 2026-11-18. The citations spike confirmed the writer, the judge and the effort levels (`0012`); the three typed model errors are unverified until the model seam is built. The first eval run can still change it.

**Context.** Checked on 2026-11-18 against the models overview, pricing, deprecations, thinking and effort pages under https://platform.claude.com/docs/en/ and https://pypi.org/project/anthropic/:

| Model | Input / output per million tokens | Thinking | Default effort |
|---|---|---|---|
| `claude-fable-5-2` | $8 / $40 | always on | high |
| `claude-opus-5-5` | $4 / $20 | always on, cannot be disabled | medium |
| `claude-sonnet-5-5` | $2 / $10 | on by default; `disabled` is rejected | high |
| `claude-haiku-5-5` | from $0.10 / $0.50 | on by default | medium |

- Model ids are pinned snapshots as written; there is no separate alias.
- Python SDK 2.10.0 (17 Nov 2026). From 2.0.0 it sends API version `2026-10-21`, under which `temperature`, `top_p` and `top_k` return a 400.
- Effort is `output_config.effort`; thinking tokens count toward `max_tokens`.
- SDK defaults are a 10 minute timeout and two retries, and a timeout is retried.
- A model can decline: HTTP 200 with `stop_reason: "refusal"`, and with structured output "the output might not match your schema".
- On judging with a different model, the only official wording found is a code comment in the eval guide: "Generally best practice to evaluate with a different model from the one used to generate the evaluated output". The guide's own example uses one model for both. It is good practice, not a documented rule.

**Decision.**

- Writer (extract and draft): `claude-sonnet-5-5`. Judge: `claude-opus-5-5`. This is the original brief's starting proposal; I named it.
- Effort is set explicitly on every call, never left to a default that differs by model. Starting values: `low` for extract, `medium` for draft, `medium` for the judge. The citations spike measures the difference.
- No sampling parameters anywhere.
- Timeout 60 seconds and one retry, set explicitly; a 240 second ceiling on the whole run.
- A refusal, a `max_tokens` stop, and a response whose `model` is not the one requested are each a typed stage error. No server-side fallback to another model: a run whose writer silently changed would make the eval table untrue.
- Prices live in one dated table in code; cost is computed from each response's usage.

**Why different models.** It reduces self-grading; it does not make the judge independent, since both are Claude models. The stronger protection is structural: code checks the judge cannot override, and a calibration set with known negatives (J2).

**Consequence.** About three calls per run; the cost per run is measured in the citations spike. Revisit the writer if the removal rate or coverage is poor at `medium` effort: try higher effort before a larger model, and record what the eval shows.
