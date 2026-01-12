from app.core.state_machine import can_transition
from app.db.models import TaskStatus


def test_state_transitions_basic():
    assert can_transition(TaskStatus.PENDING, TaskStatus.QUEUED)
    assert can_transition(TaskStatus.QUEUED, TaskStatus.RUNNING)
    assert can_transition(TaskStatus.RUNNING, TaskStatus.COMPLETED)
    assert can_transition(TaskStatus.RUNNING, TaskStatus.FAILED)