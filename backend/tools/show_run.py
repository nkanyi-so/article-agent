"""Prints a stored run from the local API in a form a person can read.

For trying the API by hand before the screen for it exists (Phase 7). It only reads,
and only from the local server that `make dev` starts.

    cd backend && uv run --locked python -m tools.show_run                 # list the runs
    cd backend && uv run --locked python -m tools.show_run <run-id>        # one run
    cd backend && uv run --locked python -m tools.show_run <run-id> 3      # claim 3, with its lines
"""

import json
import sys
import urllib.error
import urllib.request
from typing import Any

BASE = "http://localhost:8000"


def get(path: str) -> Any:
    # A fixed local address, never a caller-supplied one.
    try:
        with urllib.request.urlopen(f"{BASE}{path}", timeout=10) as response:  # noqa: S310
            return json.load(response)
    except urllib.error.HTTPError as error:
        body = json.load(error)
        raise SystemExit(
            f"{error.code}: {body['error']['code']} ({body['error']['message']})"
        ) from None
    except urllib.error.URLError:
        raise SystemExit(f"Nothing is answering at {BASE}. Start it with: make dev") from None


def list_runs() -> None:
    for run in get("/api/runs")["runs"]:
        parent = (
            f"  (re-run of {run['parent_run_id']} from {run['replay_from_stage']})"
            if run["parent_run_id"]
            else ""
        )
        seeded = "  [seeded]" if run["pinned"] else ""
        print(f"{run['id']:28} {run['status']:10} {run['title']}{seeded}{parent}")


def show_run(run_id: str) -> None:
    detail = get(f"/api/runs/{run_id}")
    run = detail["run"]
    print(
        f"{run['title']}\nrun {run['id']}: {run['status']}"
        + (f" ({run['error']})" if run["error"] else "")
    )
    if run["parent_run_id"]:
        print(f"re-run of {run['parent_run_id']} from the {run['replay_from_stage']} stage")

    print("\nSTAGES")
    for stage in detail["stages"]:
        copied = (
            f"  copied from {stage['copied_from_run_id']}" if stage["copied_from_run_id"] else ""
        )
        error = f"  error: {stage['error']}" if stage["error"] else ""
        print(f"  {stage['name']:8} {stage['status']:10} {stage['duration_ms']} ms{copied}{error}")

    print("\nMODEL CALLS")
    for call in detail["model_calls"]:
        print(
            f"  {call['stage']:8} {call['source']:8} {call['model_requested']}"
            f"  ${call['cost_usd']:.4f}"
        )
    print(
        f"  total ${detail['cost_usd']:.4f}"
        + (
            "  (replayed from recordings: nothing was spent)"
            if detail["model_calls"]
            and all(c["source"] == "fixture" for c in detail["model_calls"])
            else ""
        )
    )

    article = detail["article"]
    if article is None:
        print("\nNo article: the run did not reach the ground check.")
        return
    headline = article["headline"]
    source = "the model's" if headline["source"] == "model" else "the transcript's title"
    print(f"\nARTICLE\n{headline['text']}\n(headline: {source})")
    paragraph = -1
    for number, claim in enumerate(article["claims"]):
        if claim["paragraph"] != paragraph:
            paragraph = claim["paragraph"]
            print()
        cited = ", ".join(str(i) for i in claim["segment_indexes"])
        asked = ", ".join(str(i) for i in claim["question_segments"])
        question = f"; in answer to {asked}, added by code" if asked else ""
        print(f"  [{number}] {claim['text']}  (cites {cited}{question})")

    print(f"\nREMOVED BY THE GROUND CHECK: {len(article['removed'])}")
    for unit in article["removed"]:
        missing = f", not in what it cites: {', '.join(unit['detail'])}" if unit["detail"] else ""
        print(f"  - {unit['reason']}{missing}\n    {unit['text']}")


def show_claim(run_id: str, number: int) -> None:
    detail = get(f"/api/runs/{run_id}")
    claims = detail["article"]["claims"] if detail["article"] else []
    if not 0 <= number < len(claims):
        raise SystemExit(f"This run has claims 0 to {len(claims) - 1}.")
    claim = claims[number]
    print(f"CLAIM {number}\n  {claim['text']}\n\nTHE TRANSCRIPT LINES IT CITES")
    for index in claim["segment_indexes"]:
        segment = detail["segments"][index]
        print(f"  [{index}] {segment['speaker']}: {segment['text']}")
    if claim["question_segments"]:
        # Not cited by the model. Found by code, and shown to the judge in the same way.
        print("\nTHE QUESTION A CITED LINE WAS ANSWERING (added by code, not evidence)")
        for index in claim["question_segments"]:
            segment = detail["segments"][index]
            print(f"  [{index}] {segment['speaker']}: {segment['text']}")


def main() -> None:
    if len(sys.argv) == 1:
        list_runs()
    elif len(sys.argv) == 2:
        show_run(sys.argv[1])
    elif len(sys.argv) == 3 and sys.argv[2].isdigit():
        show_claim(sys.argv[1], int(sys.argv[2]))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
