from __future__ import annotations

from enum import Enum

from ..api.errors import domain_error


class RunStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


_ALLOWED: dict[RunStatus, set[RunStatus]] = {
    RunStatus.CREATED: {RunStatus.QUEUED},
    RunStatus.QUEUED: {RunStatus.RUNNING},
    RunStatus.RUNNING: {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELED},
    RunStatus.FAILED: {RunStatus.QUEUED},
    RunStatus.COMPLETED: set(),
    RunStatus.CANCELED: set(),
}


def ensure_transition(current: str, target: str) -> None:
    cur = RunStatus(current)
    nxt = RunStatus(target)
    if nxt not in _ALLOWED[cur]:
        raise domain_error(
            "INVALID_RUN_TRANSITION",
            f"Run status transition not allowed: {current} -> {target}",
            status_code=409,
        )
