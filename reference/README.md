# reference/

Code carried over from the old project **to read, not to run**. Nothing here is imported by the new backend, and none of it runs as it stands: the modules import `app.schemas` and `app.clients` from the old backend, and the tests depend on fixtures that were left behind on purpose (they were built around real people).

Port ideas from here by rewriting them test-first in the new backend. Delete this folder when the eval layer exists in the new code.

## legacy-backend/evals/

The part of the old backend the audit graded keep.

| File | What is worth taking |
|---|---|
| `base.py` | The report builder: weighted mean renormalised over the verdicts that are present, `passed = all verdicts passed`, `degraded` and caveats rolled up. |
| `groundedness.py` | The pattern of wrapping a model judge in code: hard-fail a claim that cites a source that does not exist **before** calling the judge, and clamp what the judge returns to the IDs it was given, so the judge can never lift a claim that failed a code check. |
| `angle_support.py` | Same pattern for "is the chosen angle backed by its sources". |
| `stage_validity.py` | A list of structural checks over a stored run, scored as passed / total, pass mark 1.0. |
| `schemas.py` | `EvalVerdict` and `EvalReport` shapes. The frontend's eval cards render these. |
| `judge.py` | The two judge prompts. Known defects: the judge was the same model as the writer, and untrusted source text was interpolated bare into the prompt. |

Left out: `entity_resolution.py` (scores a person lookup, which no longer exists), `harness.py` (no thresholds, always exited 0, defaulted to a paid call), `samples.py` (real people).

## legacy-backend/errors.py

A small typed error hierarchy: each error carries `code`, `http_status` and `retryable`, and the route layer maps them uniformly. The Apollo and Exa error types go; the shape stays.

## legacy-backend/tests/

Four eval test files, for the cases they cover (hard-fail lowers the score, no article scores zero, the judge marks a claim unsupported, report weighting). They reference fixtures named `sample_run_completed`, `sample_run_degraded` and `sample_run_failed` that are **not** here. Rewrite them against fictional transcript runs.
