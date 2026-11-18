"""Reads the saved prompt-trial runs and shows what the ground check did to each.

Free and offline.   cd backend && uv run --locked python -m tools.trial_report [--removed]
"""

import json
import sys
from collections import Counter

from app.errors import TooFewGroundedClaims
from app.model.types import ModelResponse
from app.pipeline.extract import parse_extract
from app.pipeline.ground import ground
from tools.prompt_trial import OUT, transcripts


def main() -> None:
    show_removed = "--removed" in sys.argv
    sources = transcripts()
    totals: dict[str, Counter[str]] = {}
    print(
        "variant | run | sentences | kept | uncited | number | name | other | lead kept | headline"
    )
    for folder in sorted((OUT / "draft").glob("*")):
        variant = folder.name
        total = totals.setdefault(variant, Counter())
        for path in sorted(folder.glob("*.json")):
            saved = json.loads(path.read_text())
            if not saved.get("response"):
                print(f"{variant} | {path.stem} | call failed: {saved.get('error')}")
                total["failed_calls"] += 1
                continue
            name = path.stem.rsplit("-", 1)[0]
            ingested = sources[name]
            extract_saved = json.loads((OUT / "extract" / f"{name}.json").read_text())
            extract = parse_extract(
                ModelResponse.model_validate(extract_saved["response"]), len(ingested.segments)
            )
            response = ModelResponse.model_validate(saved["response"])
            try:
                result = ground(
                    response.blocks, ingested.segments, extract.corrections, ingested.title
                )
            except TooFewGroundedClaims as failure:
                result = failure.result
            reasons = Counter(unit.reason for unit in result.removed)
            sentences = len(result.claims) + len(result.removed)
            # The lead is the first sentence of the body, kept or not.
            first_kept = result.claims[0].paragraph == 0 if result.claims else False
            first_removed = [u for u in result.removed if u.paragraph == 0]
            lead_kept = first_kept and not (
                first_removed
                and response_text(response).find(first_removed[0].text)
                < response_text(response).find(result.claims[0].text)
            )
            other = sentences - len(result.claims) - reasons["no_citation"]
            other -= reasons["unsupported_number"] + reasons["unsupported_name"]
            headline: str = result.headline.source
            if result.headline.failure:
                headline += (
                    f" ({result.headline.failure}: {', '.join(result.headline.failure_detail)})"
                )
            print(
                f"{variant} | {path.stem} | {sentences} | {len(result.claims)} "
                f"| {reasons['no_citation']} | {reasons['unsupported_number']} "
                f"| {reasons['unsupported_name']} | {other} "
                f"| {'yes' if lead_kept else 'NO'} | {headline}"
            )
            total["runs"] += 1
            total["sentences"] += sentences
            total["removed"] += len(result.removed)
            total["lead_kept"] += lead_kept
            total["headline_model"] += result.headline.source == "model"
            total["cost_micro"] += round(response.cost_usd * 1_000_000)
            if show_removed:
                for unit in result.removed:
                    detail = f" {unit.detail}" if unit.detail else ""
                    print(f"    - {unit.reason}{detail}: {unit.text}")
    print()
    for variant, total in totals.items():
        runs = total["runs"] or 1
        print(
            f"{variant}: {total['runs']} runs, {total['sentences']} sentences, "
            f"{total['removed']} removed ({total['removed'] / max(total['sentences'], 1):.1%}), "
            f"lead kept in {total['lead_kept']} of {total['runs']}, "
            f"model headline accepted in {total['headline_model']} of {total['runs']}, "
            f"draft cost ${total['cost_micro'] / 1_000_000 / runs:.4f} a run"
        )


def response_text(response: ModelResponse) -> str:
    return "".join(block.text for block in response.blocks)


if __name__ == "__main__":
    main()
