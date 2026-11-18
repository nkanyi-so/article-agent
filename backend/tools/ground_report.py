"""Runs the ground check over every recorded draft and prints what it kept and removed.

Free and offline: it reads `tests/fixtures/` only.

    cd backend && uv run --locked python -m tools.ground_report            # the table
    cd backend && uv run --locked python -m tools.ground_report --removed  # and every removal
"""

import sys
from collections import Counter

from app.errors import TooFewGroundedClaims
from app.pipeline.ground import ground
from tests.support import DRAFTS, recorded


def main() -> None:
    show_removed = "--removed" in sys.argv
    print(
        "draft | sentences | kept | no_citation | number | name | misquote | corrected "
        "| words kept | headline"
    )
    for name in DRAFTS:
        rec = recorded(name)
        try:
            result = ground(rec.blocks(), rec.segments, rec.corrections, rec.title)
        except TooFewGroundedClaims as failure:
            result = failure.result
        reasons = Counter(unit.reason for unit in result.removed)
        kept_words = sum(len(claim.text.split()) for claim in result.claims)
        all_words = kept_words + sum(len(unit.text.split()) for unit in result.removed)
        headline: str = result.headline.source
        if result.headline.failure:
            headline += f" ({result.headline.failure}: {', '.join(result.headline.failure_detail)})"
        print(
            f"{name} | {len(result.claims) + len(result.removed)} | {len(result.claims)} "
            f"| {reasons['no_citation']} | {reasons['unsupported_number']} "
            f"| {reasons['unsupported_name']} | {reasons['misquote']} "
            f"| {reasons['rests_on_corrected_segment']} | {kept_words / all_words:.0%} | {headline}"
        )
        if show_removed:
            for unit in result.removed:
                detail = f" {unit.detail}" if unit.detail else ""
                print(f"    - {unit.reason}{detail}: {unit.text}")


if __name__ == "__main__":
    main()
