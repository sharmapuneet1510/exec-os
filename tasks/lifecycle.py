from typing import Dict, FrozenSet, List
from .model import Status

# Valid transitions: from_status -> set of allowed to_status
TRANSITIONS: Dict[Status, FrozenSet[Status]] = {
    "todo":        frozenset({"in_progress", "cancelled"}),
    "in_progress": frozenset({"done", "todo", "cancelled"}),
    "done":        frozenset({"todo"}),          # allow re-open
    "cancelled":   frozenset({"todo"}),          # allow re-open
}


class InvalidTransitionError(Exception):
    pass


def allowed_transitions(status: Status) -> List[Status]:
    return sorted(TRANSITIONS.get(status, frozenset()))


def validate_transition(from_status: Status, to_status: Status) -> None:
    allowed = TRANSITIONS.get(from_status, frozenset())
    if to_status not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition from {from_status!r} to {to_status!r}. "
            f"Allowed: {sorted(allowed)}"
        )


class LifecycleService:
    def __init__(self, task_service):
        self._tasks = task_service

    def transition(self, task_id: str, to_status: Status):
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"task {task_id!r} not found")
        validate_transition(task.status, to_status)
        return self._tasks.update(task_id, status=to_status)

    def allowed_transitions(self, task_id: str) -> List[Status]:
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"task {task_id!r} not found")
        return allowed_transitions(task.status)
