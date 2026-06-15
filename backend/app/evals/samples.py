"""Fixed sample set for the eval harness.

Fixture mode scores these against committed JSON fixture files.
Live mode runs the full pipeline per FormRequest then scores.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.schemas import FormRequest, Run

# Canonical five-sample set covering key identity/coverage shapes.
SAMPLE_INPUTS: list[FormRequest] = [
    # 1. Famous exec with company — full signals available
    FormRequest(name="Sam Altman", company="OpenAI"),
    # 2. Name only — no company context
    FormRequest(name="Jensen Huang"),
    # 3. LinkedIn URL only — name derived from slug
    FormRequest(linkedin_url="https://www.linkedin.com/in/satya-nadella"),
    # 4. Common name — may return ambiguous Apollo result
    FormRequest(name="John Smith", company="Microsoft"),
    # 5. Obscure / likely-unknown name — expected to fail at research (no Exa hits)
    FormRequest(name="zxqvmnobscure7734person"),
]

_FIXTURE_DIR = Path(__file__).parent.parent.parent / "tests" / "fixtures"

# Map from FormRequest repr to fixture filename.
# Add entries here as new fixtures are committed.
_FIXTURE_MAP: dict[str, str] = {
    "Sam Altman / OpenAI": "sample_run_completed.json",
    "Sam Altman / OpenAI (degraded)": "sample_run_degraded.json",
    "zxqvmnobscure7734person": "sample_run_failed.json",
}

# Ordered list used by the harness in fixture mode.
FIXTURE_FILES: list[Path] = [
    _FIXTURE_DIR / "sample_run_completed.json",
    _FIXTURE_DIR / "sample_run_degraded.json",
    _FIXTURE_DIR / "sample_run_failed.json",
]


def load_fixture_run(path: Path) -> Run:
    from app.evals.schemas import EvalReport  # noqa: F401 — ensures Run.model_rebuild

    Run.model_rebuild()
    data = json.loads(path.read_text())
    return Run.model_validate(data)
