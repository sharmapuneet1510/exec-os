from datetime import date
from typing import List, Optional
from .model import Priority, Status, Task
from .store import JSONTaskStore


class TaskService:
    def __init__(self, store: JSONTaskStore = None):
        self._store = store or JSONTaskStore()

    def create(
        self,
        title: str,
        description: str = "",
        due_date: Optional[date] = None,
        priority: Priority = "medium",
        project_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Task:
        if not title or not title.strip():
            raise ValueError("title must not be empty")
        task = Task(
            title=title.strip(),
            description=description,
            due_date=due_date,
            priority=priority,
            project_id=project_id,
            tags=tags or [],
        )
        self._store.save(task)
        return task

    def get(self, task_id: str) -> Optional[Task]:
        return self._store.load(task_id)

    def update(self, task_id: str, **kwargs) -> Task:
        task = self._store.load(task_id)
        if task is None:
            raise KeyError(f"task {task_id!r} not found")
        allowed = {"title", "description", "due_date", "reminder_date", "priority", "status", "project_id", "tags"}
        for k, v in kwargs.items():
            if k not in allowed:
                raise ValueError(f"unknown field {k!r}")
            if k == "title":
                if not v or not str(v).strip():
                    raise ValueError("title must not be empty")
                v = v.strip()
            setattr(task, k, v)
        self._store.save(task)
        return task

    def delete(self, task_id: str) -> bool:
        return self._store.delete(task_id)

    def list_all(self) -> List[Task]:
        return self._store.all()

    def list_by_status(self, status: Status) -> List[Task]:
        return [t for t in self._store.all() if t.status == status]

    def list_by_project(self, project_id: str) -> List[Task]:
        return [t for t in self._store.all() if t.project_id == project_id]
