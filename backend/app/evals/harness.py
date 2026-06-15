"""Eval batch harness.

Usage:
    cd backend
    python -m app.evals.harness                  # fixture mode, real judge
    python -m app.evals.harness --mode live       # live pipeline, real judge
    python -m app.evals.harness --judge mock      # fixture mode, mock judge
    python -m app.evals.harness --out json        # JSON output
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from app.evals.samples import FIXTURE_FILES, SAMPLE_INPUTS, load_fixture_run
from app.evals.schemas import EvalReport


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _bar(score: float, width: int = 10) -> str:
    filled = round(score * width)
    return "█" * filled + "░" * (width - filled)


def _fmt_score(score: float, passed: bool) -> str:
    mark = "✓" if passed else "✗"
    return f"{mark} {score:.2f}"


def _print_table(rows: list[dict]) -> None:
    headers = ["Run", "Ground", "Entity", "Angle", "Stage", "Overall", "Notes"]
    col_widths = [max(len(h), max((len(str(r.get(h, ""))) for r in rows), default=0)) for h in headers]

    def _row(cells: list[str]) -> str:
        return "  ".join(c.ljust(w) for c, w in zip(cells, col_widths))

    print()
    print(_row(headers))
    print("  ".join("-" * w for w in col_widths))
    for r in rows:
        cells = [str(r.get(h, "")) for h in headers]
        print(_row(cells))
    print()


def _verdict_cell(report: EvalReport, name: str) -> str:
    v = next((v for v in report.verdicts if v.name == name), None)
    if v is None:
        return "n/a"
    mark = "✓" if v.passed else "✗"
    deg = "~" if v.degraded else ""
    return f"{mark}{deg}{v.score:.2f}"


# ---------------------------------------------------------------------------
# Scoring a single run
# ---------------------------------------------------------------------------


async def score_run(run, *, judge=None, mode: str = "fixture") -> tuple[EvalReport, list[str]]:
    """Run all four evals against a Run and return (report, notes)."""
    from app.evals.base import run_all_evals, run_deterministic_evals
    from app.evals.schemas import EvalReport

    notes: list[str] = []

    if judge is not None:
        report = await run_all_evals(run, judge)
    else:
        report = await run_deterministic_evals(run)
        notes.append("judges skipped (--judge mock)")

    if report.degraded:
        notes.extend(f"DEGRADED: {c}" for c in report.caveats[:3])

    return report, notes


# ---------------------------------------------------------------------------
# Live mode: run the real pipeline
# ---------------------------------------------------------------------------


async def run_live_pipeline(form) -> Any:
    from app.runs import run_form_pipeline
    return await run_form_pipeline(form)


# ---------------------------------------------------------------------------
# Main harness
# ---------------------------------------------------------------------------


async def _main(args: argparse.Namespace) -> None:
    use_real_judge = args.judge == "real"
    mode = args.mode
    out_fmt = args.out

    print(f"\narticle-agent eval harness  [mode={mode}  judge={args.judge}]")
    if mode == "live":
        print("⚠  Live mode: results depend on live API state and are not reproducible.")

    # Build judge client if real
    judge = None
    if use_real_judge:
        from app.clients import ClaudeClient
        from app.evals.judge import JudgeClient

        try:
            claude = ClaudeClient()
            judge = JudgeClient(claude)
        except Exception as exc:
            print(f"ERROR building judge: {exc}", file=sys.stderr)
            sys.exit(1)

    rows: list[dict] = []
    all_reports: list[dict] = []

    if mode == "fixture":
        available = [p for p in FIXTURE_FILES if p.exists()]
        if not available:
            print("No fixture files found. Run the pipeline once and commit fixtures.")
            sys.exit(1)

        for path in available:
            label = path.name.replace("sample_run_", "").replace(".json", "")
            print(f"  scoring {path.name} …")
            try:
                run = load_fixture_run(path)
                report, notes = await score_run(run, judge=judge, mode="fixture")
            except Exception as exc:
                print(f"    ERROR: {exc}", file=sys.stderr)
                continue

            rows.append(_build_row(label, report, notes))
            all_reports.append({"file": path.name, "report": report.model_dump(mode="json"), "notes": notes})

            if out_fmt == "table":
                _print_claim_breakdown(label, report)

    else:
        # Live mode
        for i, form in enumerate(SAMPLE_INPUTS, 1):
            label = form.name or form.linkedin_url or f"input_{i}"
            print(f"  [{i}/{len(SAMPLE_INPUTS)}] running pipeline for '{label}' …")
            try:
                run = await run_live_pipeline(form)
                print(f"    pipeline status: {run.status}")
                report, notes = await score_run(run, judge=judge, mode="live")
            except Exception as exc:
                print(f"    ERROR: {exc}", file=sys.stderr)
                continue

            rows.append(_build_row(label, report, notes))
            all_reports.append({"input": form.model_dump(), "report": report.model_dump(mode="json"), "notes": notes})

            if out_fmt == "table":
                _print_claim_breakdown(label, report)

    # Output
    if out_fmt == "json":
        print(json.dumps(all_reports, indent=2, default=str))
    else:
        if rows:
            # Aggregate row
            scores = [r["_overall"] for r in rows if isinstance(r.get("_overall"), float)]
            if scores:
                avg = sum(scores) / len(scores)
                agg_row = {
                    "Run": f"AGGREGATE ({len(scores)})",
                    "Ground": "",
                    "Entity": "",
                    "Angle": "",
                    "Stage": "",
                    "Overall": f"{avg:.2f}",
                    "Notes": "",
                }
                rows.append(agg_row)

            _print_table(rows)

        print("Done.")


def _build_row(label: str, report: EvalReport, notes: list[str]) -> dict:
    return {
        "Run": label[:30],
        "Ground": _verdict_cell(report, "groundedness"),
        "Entity": _verdict_cell(report, "entity_resolution"),
        "Angle": _verdict_cell(report, "angle_support"),
        "Stage": _verdict_cell(report, "stage_validity"),
        "Overall": f"{'✓' if report.passed else '✗'} {report.overall_score:.2f}",
        "Notes": "; ".join(notes[:2]),
        "_overall": report.overall_score,  # internal for aggregate
    }


def _print_claim_breakdown(label: str, report: EvalReport) -> None:
    ground = next((v for v in report.verdicts if v.name == "groundedness"), None)
    if ground is None or not ground.details.get("claims"):
        return

    print(f"\n  Claim-level groundedness for '{label}':")
    for c in ground.details["claims"]:
        mark = "  ✓" if c["supported"] else "  ✗"
        print(f"    {mark} [{c['claim_index']}] {c['claim_text'][:80]}")
        if not c["supported"]:
            print(f"       {c['reasoning'][:100]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="article-agent eval harness")
    parser.add_argument("--mode", choices=["fixture", "live"], default="fixture")
    parser.add_argument("--judge", choices=["real", "mock"], default="real")
    parser.add_argument("--out", choices=["table", "json"], default="table")
    args = parser.parse_args()
    asyncio.run(_main(args))


if __name__ == "__main__":
    main()
