"""The events a run emits. One named union; every stream of them ends with a terminal event."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, RootModel

from app.schemas import StageName


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


class _Event(BaseModel):
    seq: int = Field(ge=0)
    at: str = Field(default_factory=_now, description="Server time when the event was produced.")
    run_id: str


class RunStarted(_Event):
    type: Literal["run_started"] = "run_started"


class StageStarted(_Event):
    type: Literal["stage_started"] = "stage_started"
    stage: StageName


class StageCompleted(_Event):
    type: Literal["stage_completed"] = "stage_completed"
    stage: StageName
    duration_ms: int


class RunCompleted(_Event):
    type: Literal["run_completed"] = "run_completed"


class RunFailed(_Event):
    type: Literal["run_failed"] = "run_failed"
    error: str = Field(description="An error code. Never exception text or an upstream message.")
    stage: StageName | None = None


AnyRunEvent = RunStarted | StageStarted | StageCompleted | RunCompleted | RunFailed
TERMINAL = (RunCompleted, RunFailed)


class RunEvent(RootModel[Annotated[AnyRunEvent, Field(discriminator="type")]]):
    """One event of a run's stream."""
