# Eval harness results

## Mock judge run — 2026-06-15

```
article-agent eval harness  [mode=fixture  judge=mock]

Run            Ground  Entity  Angle  Stage  Overall  Notes
-------------  ------  ------  -----  -----  -------  -----
completed      n/a     ✗~0.50  n/a    ✓1.00  ✗ 0.83   judges skipped (--judge mock); DEGRADED: Apollo 403
degraded       n/a     ✗~0.50  n/a    ✗0.95  ✗ 0.80   judges skipped (--judge mock); DEGRADED: Apollo 403; claim cites exa:FAKE (stage_validity deduct)
failed         n/a     ✗~0.50  n/a    ✓1.00  ✗ 0.83   judges skipped (--judge mock); DEGRADED: Apollo 403
AGGREGATE (3)                                0.82
```

### What these numbers mean

- **Ground / Angle = n/a** — `--judge mock` skips LLM-judge evals. Run with `--judge real` to score groundedness and angle support (requires `ANTHROPIC_API_KEY`; ~$0.10–0.30 per harness run).
- **Entity = ~0.50 / degraded on all three** — Apollo free plan returns HTTP 403 on `people/match`; every run falls back to form-input stub. Entity resolution will score correctly once Apollo is upgraded or a fallback enrichment source is added.
- **Stage = 1.00 on completed and failed** — all structural invariants hold: stage order, status transitions, source-ID consistency, claim/source-map alignment.
- **Stage = 0.95 on degraded** — the `degraded` fixture contains a claim citing `exa:FAKE`, a deliberately non-existent source ID. The `stage_validity` eval correctly deducts for `claim_source_ids_in_sources` failure.

### Next step

Run `--judge real` to add groundedness and angle_support scores:

```bash
cd backend && python -m app.evals.harness --mode fixture --judge real --out table
```
