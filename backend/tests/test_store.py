"""The store across restarts: what is kept, what is rebuilt, and what is closed."""

from datetime import UTC, datetime
from pathlib import Path

import httpx

from app.main import create_app
from app.settings import Settings
from app.store import RunRow, RunStatus, Store
from tests.test_api import client_for, events_of


def a_run(run_id: str, status: RunStatus = "running") -> RunRow:
    return RunRow(
        id=run_id,
        created_at=datetime.now(UTC),
        mode="demo",
        source="seed",
        title="t",
        status=status,
    )


def test_the_database_has_the_four_tables(tmp_path: Path) -> None:
    import sqlite3
    from contextlib import closing

    Store(tmp_path / "runs.sqlite3")

    with closing(sqlite3.connect(tmp_path / "runs.sqlite3")) as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    assert {"runs", "stage_records", "model_calls", "rate_events"} <= tables


def test_a_run_left_running_by_a_process_that_stopped_is_closed_at_the_next_start(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "runs.sqlite3")
    store.create_run(a_run("cut-off"))
    store.create_run(a_run("finished", status="completed"))

    create_app(Settings(database_path=tmp_path / "runs.sqlite3"))

    cut_off, finished = store.get_run("cut-off"), store.get_run("finished")
    assert cut_off is not None and finished is not None
    assert (cut_off.run.status, cut_off.run.error) == ("failed", "interrupted")
    assert finished.run.status == "completed"


async def test_a_visitors_run_is_kept_across_a_restart_and_the_seeded_runs_are_not_doubled(
    tmp_path: Path,
) -> None:
    settings = Settings(database_path=tmp_path / "runs.sqlite3")

    async with client_for(create_app(settings)) as first:
        events = events_of(
            (await first.post("/api/runs/stream", json={"seed_id": "quillmoor-books"})).text
        )
    async with client_for(create_app(settings)) as second:
        runs = (await second.get("/api/runs")).json()["runs"]
        kept: httpx.Response = await second.get(f"/api/runs/{events[0]['run_id']}")

    assert [r["id"] for r in runs if r["pinned"]] == [
        "seed-korvath-greenhouses",
        "seed-sallowfield-dental",
        "seed-quillmoor-books",
        "seed-korvath-altered",
    ]
    assert len(runs) == 5
    assert kept.status_code == 200 and kept.json()["article"]["claims"]


def test_an_unknown_run_is_none_and_the_store_reports_itself_reachable(tmp_path: Path) -> None:
    store = Store(tmp_path / "runs.sqlite3")

    assert store.get_run("nope") is None
    assert store.reachable() is True
