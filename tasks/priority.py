from datetime import date, timedelta
from typing import List, Optional
from .model import Priority, Task

PRIORITY_ORDER: List[Priority] = ["low", "medium", "high", "critical"]
_RANK = {p: i for i, p in enumerate(PRIORITY_ORDER)}


def is_overdue(task: Task, as_of: date) -> bool:
    if task.due_date is None or task.status in ("done", "cancelled"):
        return False
    return task.due_date < as_of


def is_due_soon(task: Task, as_of: date, window_days: int = 3) -> bool:
    if task.due_date is None or task.status in ("done", "cancelled"):
        return False
    return as_of <= task.due_date <= as_of + timedelta(days=window_days)


def days_until_due(task: Task, as_of: date) -> Optional[int]:
    if task.due_date is None:
        return None
    return (task.due_date - as_of).days


def compare_priority(a: Priority, b: Priority) -> int:
    return _RANK[a] - _RANK[b]


def boost_priority(priority: Priority) -> Priority:
    idx = _RANK[priority]
    return PRIORITY_ORDER[min(idx + 1, len(PRIORITY_ORDER) - 1)]


def lower_priority(priority: Priority) -> Priority:
    idx = _RANK[priority]
    return PRIORITY_ORDER[max(idx - 1, 0)]


class DueDateService:
    def __init__(self, task_service):
        self._tasks = task_service

    def set_reminder_date(self, task_id: str, reminder_date: Optional[date]) -> Task:
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"task {task_id!r} not found")
        return self._tasks.update(task_id, reminder_date=reminder_date)

    def set_due_date(self, task_id: str, due_date: Optional[date]) -> Task:
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"task {task_id!r} not found")
        return self._tasks.update(task_id, due_date=due_date)

    def set_priority(self, task_id: str, priority: Priority) -> Task:
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"task {task_id!r} not found")
        if priority not in _RANK:
            raise ValueError(f"invalid priority {priority!r}")
        return self._tasks.update(task_id, priority=priority)

    def overdue_tasks(self, as_of: date) -> List[Task]:
        return [t for t in self._tasks.list_all() if is_overdue(t, as_of)]

    def due_soon_tasks(self, as_of: date, window_days: int = 3) -> List[Task]:
        return [t for t in self._tasks.list_all() if is_due_soon(t, as_of, window_days)]

    def sorted_by_priority(self, tasks: Optional[List[Task]] = None) -> List[Task]:
        items = tasks if tasks is not None else self._tasks.list_all()
        return sorted(items, key=lambda t: _RANK[t.priority], reverse=True)
