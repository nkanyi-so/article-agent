"""The store: runs, their stage records, their model calls, and rate events, in SQLite.

Four tables through the standard library (decisions/0007). Each call opens its own
connection, so nothing is shared between requests. On the hosted demo the file lives in
the instance's scratch folder and goes when the instance does; locally it stays.
"""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from app.model.types import ModelRequest, ModelResponse
from app.pipeline.runner import FailedModelCall, ModelCallRecord, RunState
from app.schemas import StageName, StageRecord

# What a live run that is still going is assumed to cost until its calls are recorded: two
# writer calls and one judge call, each at a full max_tokens of output. Reserved against the
# daily budget, so runs started together cannot all read the same recorded total and all be
# let through.
WORST_RUN_USD = (2 * (16_000 * 10.0 + 20_000 * 2.0) + (16_000 * 20.0 + 20_000 * 4.0)) / 1_000_000

Admission = Literal["ok", "rate_limited", "budget_exhausted"]
RunSource = Literal["seed", "paste", "replay"]
RunStatus = Literal["running", "completed", "failed"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    mode TEXT NOT NULL,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    seed_id TEXT,
    parent_run_id TEXT,
    replay_from_stage TEXT,
    status TEXT NOT NULL,
    error TEXT,
    pinned INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS stage_records (
    run_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    duration_ms INTEGER,
    input TEXT,
    output TEXT,
    error TEXT,
    copied_from_run_id TEXT,
    PRIMARY KEY (run_id, seq)
);
CREATE TABLE IF NOT EXISTS model_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    stage TEXT NOT NULL,
    request_key TEXT NOT NULL,
    source TEXT NOT NULL,
    model_requested TEXT NOT NULL,
    model_served TEXT,
    request TEXT,
    response TEXT,
    stop_reason TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd REAL NOT NULL,
    latency_ms INTEGER,
    attempts INTEGER,
    error TEXT
);
CREATE TABLE IF NOT EXISTS rate_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    address TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS rate_events_address_at ON rate_events (address, at);
"""


class RunRow(BaseModel):
    """A run as listed: enough to find it again and to see how it ended."""

    id: str
    created_at: datetime
    mode: Literal["demo", "live"]
    source: RunSource
    title: str
    seed_id: str | None = None
    parent_run_id: str | None = None
    replay_from_stage: StageName | None = None
    status: RunStatus
    error: str | None = None
    pinned: bool = False


class StoredModelCall(BaseModel):
    """A model call as stored. A call that was billed but unusable has an error and no response."""

    stage: StageName
    request_key: str
    source: Literal["live", "fixture"]
    model_requested: str
    model_served: str | None = None
    stop_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float
    latency_ms: int | None = None
    attempts: int | None = None
    error: str | None = None
    request: ModelRequest | None = None
    response: ModelResponse | None = None


class StoredRun(BaseModel):
    run: RunRow
    stages: list[StageRecord]
    model_calls: list[StoredModelCall]


def _dump(value: dict[str, Any] | None) -> str | None:
    return None if value is None else json.dumps(value, ensure_ascii=False)


def _load(value: str | None) -> dict[str, Any] | None:
    return None if value is None else json.loads(value)


class Store:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        # `closing`, because sqlite3's own context manager commits but does not close.
        with closing(sqlite3.connect(self.path, timeout=5.0)) as db:
            db.row_factory = sqlite3.Row
            with db:
                yield db

    def reachable(self) -> bool:
        try:
            with self._connect() as db:
                db.execute("SELECT 1").fetchone()
        except sqlite3.Error:
            return False
        return True

    # ------------------------------------------------------------------ runs

    def create_run(self, run: RunRow) -> None:
        """Writes the run row. Called before the first event, so a reload always finds the run."""
        with self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run.id,
                    run.created_at.isoformat(),
                    run.mode,
                    run.source,
                    run.title,
                    run.seed_id,
                    run.parent_run_id,
                    run.replay_from_stage,
                    run.status,
                    run.error,
                    int(run.pinned),
                ),
            )
            # A seeded run is rebuilt at every start; drop what the last start left.
            db.execute("DELETE FROM stage_records WHERE run_id = ?", (run.id,))
            db.execute("DELETE FROM model_calls WHERE run_id = ?", (run.id,))

    def save_state(self, state: RunState, now: datetime) -> None:
        """Stores everything the run has so far: its status, stage records and model calls."""
        with self._connect() as db:
            db.execute(
                "UPDATE runs SET status = ?, error = ? WHERE id = ?",
                (state.status, state.error, state.run_id),
            )
            db.execute("DELETE FROM stage_records WHERE run_id = ?", (state.run_id,))
            db.executemany(
                "INSERT INTO stage_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        r.run_id,
                        r.seq,
                        r.name,
                        r.status,
                        r.started_at.isoformat(),
                        r.duration_ms,
                        _dump(r.input),
                        _dump(r.output),
                        r.error,
                        r.copied_from_run_id,
                    )
                    for r in state.stages
                ],
            )
            db.execute("DELETE FROM model_calls WHERE run_id = ?", (state.run_id,))
            for call in state.model_calls:
                db.execute(_INSERT_CALL, _call_row(state.run_id, now, call))
            for failed in state.failed_calls:
                db.execute(_INSERT_CALL, _failed_row(state.run_id, now, failed))

    def get_run(self, run_id: str) -> StoredRun | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if row is None:
                return None
            stages = db.execute(
                "SELECT * FROM stage_records WHERE run_id = ? ORDER BY seq", (run_id,)
            ).fetchall()
            calls = db.execute(
                "SELECT * FROM model_calls WHERE run_id = ? ORDER BY id", (run_id,)
            ).fetchall()
        return StoredRun(
            run=_run_row(row),
            stages=[
                StageRecord(
                    run_id=s["run_id"],
                    seq=s["seq"],
                    name=s["name"],
                    status=s["status"],
                    started_at=datetime.fromisoformat(s["started_at"]),
                    duration_ms=s["duration_ms"],
                    input=_load(s["input"]),
                    output=_load(s["output"]),
                    error=s["error"],
                    copied_from_run_id=s["copied_from_run_id"],
                )
                for s in stages
            ],
            model_calls=[
                StoredModelCall(
                    stage=c["stage"],
                    request_key=c["request_key"],
                    source=c["source"],
                    model_requested=c["model_requested"],
                    model_served=c["model_served"],
                    stop_reason=c["stop_reason"],
                    input_tokens=c["input_tokens"],
                    output_tokens=c["output_tokens"],
                    cost_usd=c["cost_usd"],
                    latency_ms=c["latency_ms"],
                    attempts=c["attempts"],
                    error=c["error"],
                    request=ModelRequest.model_validate_json(c["request"])
                    if c["request"]
                    else None,
                    response=(
                        ModelResponse.model_validate_json(c["response"]) if c["response"] else None
                    ),
                )
                for c in calls
            ],
        )

    def list_runs(self, limit: int = 50) -> list[RunRow]:
        """Seeded runs first, in the order they were seeded, then the newest."""
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM runs ORDER BY pinned DESC, "
                "CASE WHEN pinned THEN rowid END, created_at DESC, id LIMIT ?",
                (limit,),
            ).fetchall()
        return [_run_row(row) for row in rows]

    def close_abandoned_runs(self) -> int:
        """A run still "running" when the process starts was cut off by the last one stopping."""
        with self._connect() as db:
            cursor = db.execute(
                "UPDATE runs SET status = 'failed', error = 'interrupted' WHERE status = 'running'"
            )
            return cursor.rowcount

    # ------------------------------------------------------------------ the guards

    def admit_run(
        self,
        address: str,
        at: datetime,
        runs_per_minute: int,
        daily_budget_usd: float,
        reserve_usd: float = 0.0,
    ) -> Admission:
        """Decides whether one more run may start from `address`, and if so records it.

        One transaction that takes the write lock first, so requests arriving together are
        decided one after another: each sees the ones admitted before it.

        `reserve_usd` is what a run that can spend is assumed to cost until its calls are
        recorded. Runs still going each hold that much of the budget, and a new one is let
        in only if there is room for its own. Zero where nothing can be spent.
        """
        minute_ago = (at - timedelta(minutes=1)).isoformat()
        day_start = at.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        with closing(sqlite3.connect(self.path, timeout=5.0, isolation_level=None)) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                starts = db.execute(
                    "SELECT COUNT(*) FROM rate_events WHERE address = ? AND at >= ?",
                    (address, minute_ago),
                ).fetchone()[0]
                if starts >= runs_per_minute:
                    db.execute("COMMIT")
                    return "rate_limited"
                spent = db.execute(
                    "SELECT COALESCE(SUM(cost_usd), 0) FROM model_calls "
                    "WHERE source = 'live' AND created_at >= ?",
                    (day_start,),
                ).fetchone()[0]
                in_flight = db.execute(
                    "SELECT COUNT(*) FROM runs WHERE mode = 'live' AND status = 'running'"
                ).fetchone()[0]
                held = spent + in_flight * reserve_usd
                if held >= daily_budget_usd or (
                    reserve_usd and held + reserve_usd > daily_budget_usd
                ):
                    db.execute("COMMIT")
                    return "budget_exhausted"
                db.execute(
                    "INSERT INTO rate_events (at, address) VALUES (?, ?)", (at.isoformat(), address)
                )
                # Nothing reads a rate event after a day.
                db.execute(
                    "DELETE FROM rate_events WHERE at < ?", ((at - timedelta(days=1)).isoformat(),)
                )
                db.execute("COMMIT")
            except BaseException:
                db.execute("ROLLBACK")
                raise
        return "ok"

    def prune_runs(self, keep: int) -> int:
        """Deletes all but the newest `keep` runs that are not seeded, with their records.

        The cost rows of live calls are kept: the daily budget reads them, and live mode
        runs on a developer's machine, where disk is not the concern.
        """
        with self._connect() as db:
            old = [
                row[0]
                for row in db.execute(
                    "SELECT id FROM runs WHERE pinned = 0 AND status != 'running' "
                    "ORDER BY created_at DESC, rowid DESC LIMIT -1 OFFSET ?",
                    (keep,),
                )
            ]
            for run_id in old:
                db.execute("DELETE FROM runs WHERE id = ?", (run_id,))
                db.execute("DELETE FROM stage_records WHERE run_id = ?", (run_id,))
                db.execute(
                    "DELETE FROM model_calls WHERE run_id = ? AND source != 'live'", (run_id,)
                )
        return len(old)

    def live_cost_since(self, since: datetime) -> float:
        """What live model calls have cost since `since`. Replayed recordings cost nothing."""
        with self._connect() as db:
            row = db.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) FROM model_calls "
                "WHERE source = 'live' AND created_at >= ?",
                (since.isoformat(),),
            ).fetchone()
        return float(row[0])


_INSERT_CALL = (
    "INSERT INTO model_calls (run_id, created_at, stage, request_key, source, model_requested, "
    "model_served, request, response, stop_reason, input_tokens, output_tokens, cost_usd, "
    "latency_ms, attempts, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


def _call_row(run_id: str, now: datetime, call: ModelCallRecord) -> tuple[Any, ...]:
    return (
        run_id,
        now.isoformat(),
        call.stage,
        call.request_key,
        call.source,
        call.model_requested,
        call.model_served,
        call.request.model_dump_json(),
        call.response.model_dump_json(),
        call.stop_reason,
        call.input_tokens,
        call.output_tokens,
        call.cost_usd,
        call.latency_ms,
        call.attempts,
        None,
    )


def _failed_row(run_id: str, now: datetime, call: FailedModelCall) -> tuple[Any, ...]:
    return (
        run_id,
        now.isoformat(),
        call.stage,
        call.request_key,
        call.source,
        call.model_requested,
        None,
        None,
        None,
        None,
        None,
        None,
        call.cost_usd,
        None,
        None,
        call.error,
    )


def _run_row(row: sqlite3.Row) -> RunRow:
    return RunRow(
        id=row["id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        mode=row["mode"],
        source=row["source"],
        title=row["title"],
        seed_id=row["seed_id"],
        parent_run_id=row["parent_run_id"],
        replay_from_stage=row["replay_from_stage"],
        status=row["status"],
        error=row["error"],
        pinned=bool(row["pinned"]),
    )


def utc_now() -> datetime:
    return datetime.now(UTC)
