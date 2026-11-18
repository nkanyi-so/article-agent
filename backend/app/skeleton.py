"""Phase 2 walking skeleton: a dummy event stream and a runtime report.

Nothing here is the product. It exists so the host can be proved (does a stream arrive
event by event, how long is a cold start, what is installed, is there a scratch disk)
before the pipeline is built on it. Phase 5 replaces these routes with the real ones;
the event shapes below are the ones the real stream will use.
"""

import asyncio
import importlib.metadata
import importlib.util
import logging
import platform
import sqlite3
import tempfile
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, RootModel

STARTED = time.monotonic()
logger = logging.getLogger(__name__)

Sleep = Callable[[float], Awaitable[None]]


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


class EventBase(BaseModel):
    seq: int
    at: str = Field(default_factory=now, description="Server time when the event was produced.")


class RunStarted(EventBase):
    type: Literal["run_started"] = "run_started"


class StageStarted(EventBase):
    type: Literal["stage_started"] = "stage_started"
    stage: str


class StageCompleted(EventBase):
    type: Literal["stage_completed"] = "stage_completed"
    stage: str


class RunCompleted(EventBase):
    type: Literal["run_completed"] = "run_completed"


class RunFailed(EventBase):
    type: Literal["run_failed"] = "run_failed"
    error: str


AnyEvent = RunStarted | StageStarted | StageCompleted | RunCompleted | RunFailed


class SkeletonEvent(RootModel[Annotated[AnyEvent, Field(discriminator="type")]]):
    """One event of the stream. A named union, so the schema documents every variant."""


async def skeleton_events(delay_s: float, sleep: Sleep = asyncio.sleep) -> AsyncIterator[AnyEvent]:
    """Five events spaced `delay_s` apart, then a terminal one. It always ends with one."""
    seq = 0
    try:
        yield RunStarted(seq=seq)
        for stage in ("first", "second"):
            for event in (StageStarted, StageCompleted):
                await sleep(delay_s)
                seq += 1
                yield event(seq=seq, stage=stage)
        await sleep(delay_s)
        yield RunCompleted(seq=seq + 1)
    except Exception:
        # The reason goes to the server's log. A client gets a code, never exception text.
        logger.exception("skeleton stream failed")
        yield RunFailed(seq=seq + 1, error="internal_error")


class Distribution(BaseModel):
    name: str
    version: str


class ScratchSqlite(BaseModel):
    ok: bool
    rows_read: int


class RuntimeReport(BaseModel):
    python: str
    uptime_s: float
    anthropic_installed: bool
    scratch_sqlite: ScratchSqlite
    distributions: list[Distribution]


def scratch_sqlite() -> ScratchSqlite:
    """Creates a database file in the scratch folder, writes a row and reads it back."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "scratch.sqlite3"
        try:
            # `closing`, because sqlite3's own context manager commits but does not close.
            with closing(sqlite3.connect(path)) as db:
                db.execute("CREATE TABLE probe (value TEXT)")
                db.execute("INSERT INTO probe VALUES ('written')")
                db.commit()
            with closing(sqlite3.connect(path)) as db:
                rows = db.execute("SELECT value FROM probe").fetchall()
        except sqlite3.Error:
            return ScratchSqlite(ok=False, rows_read=0)
    return ScratchSqlite(ok=rows == [("written",)], rows_read=len(rows))


def runtime_report() -> RuntimeReport:
    distributions = sorted(
        (
            Distribution(name=dist.metadata["Name"], version=dist.version)
            for dist in importlib.metadata.distributions()
            if dist.metadata["Name"]
        ),
        key=lambda d: d.name.lower(),
    )
    return RuntimeReport(
        python=platform.python_version(),
        uptime_s=round(time.monotonic() - STARTED, 3),
        anthropic_installed=importlib.util.find_spec("anthropic") is not None,
        scratch_sqlite=scratch_sqlite(),
        distributions=distributions,
    )
