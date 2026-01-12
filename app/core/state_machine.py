from __future__ import annotations

from dataclasses import dataclass
from app.db.models import TaskStatus


@dataclass(frozen=True)
class Transition:
    from_status: TaskStatus
    to_status: TaskStatus


ALLOWED: set[Transition] = {
    Transition(TaskStatus.PENDING, TaskStatus.QUEUED),
    Transition(TaskStatus.QUEUED, TaskStatus.RUNNING),
    Transition(TaskStatus.RUNNING, TaskStatus.COMPLETED),
    Transition(TaskStatus.RUNNING, TaskStatus.FAILED),
    Transition(TaskStatus.RUNNING, TaskStatus.QUEUED),  # retry
    Transition(TaskStatus.PENDING, TaskStatus.CANCELED),
    Transition(TaskStatus.QUEUED, TaskStatus.CANCELED),
    Transition(TaskStatus.RUNNING, TaskStatus.CANCELED),
}


def can_transition(from_status: TaskStatus, to_status: TaskStatus) -> bool:
    return Transition(from_status, to_status) in ALLOWED