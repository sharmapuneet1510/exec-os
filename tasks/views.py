import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from .model import Priority, Status, Task

_DEFAULT_DIR = Path.home() / ".commanddesk" / "views"


@dataclass
class TaskFilter:
    status: Optional[Status] = None
    priority: Optional[Priority] = None
    project_id: Optional[str] = None
    search_text: Optional[str] = None
    overdue_only: bool = False
    due_before: Optional[date] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "priority": self.priority,
            "project_id": self.project_id,
            "search_text": self.search_text,
            "overdue_only": self.overdue_only,
            "due_before": self.due_before.isoformat() if self.due_before else None,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TaskFilter":
        db = d.get("due_before")
        return cls(
            status=d.get("status"),
            priority=d.get("priority"),
            project_id=d.get("project_id"),
            search_text=d.get("search_text"),
            overdue_only=d.get("overdue_only", False),
            due_before=date.fromisoformat(db) if db else None,
            tags=list(d.get("tags", [])),
        )


@dataclass
class SavedView:
    name: str
    task_filter: TaskFilter
    view_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict:
        return {"view_id": self.view_id, "name": self.name, "filter": self.task_filter.to_dict()}

    @classmethod
    def from_dict(cls, d: dict) -> "SavedView":
        return cls(
            view_id=d["view_id"],
            name=d["name"],
            task_filter=TaskFilter.from_dict(d["filter"]),
        )


def apply_filter(tasks: List[Task], f: TaskFilter, as_of: Optional[date] = None) -> List[Task]:
    result = tasks
    if f.status:
        result = [t for t in result if t.status == f.status]
    if f.priority:
        result = [t for t in result if t.priority == f.priority]
    if f.project_id:
        result = [t for t in result if t.project_id == f.project_id]
    if f.search_text:
        q = f.search_text.lower()
        result = [t for t in result if q in t.title.lower() or q in t.description.lower()]
    if f.overdue_only and as_of:
        result = [t for t in result if t.due_date and t.due_date < as_of and t.status not in ("done", "cancelled")]
    if f.due_before:
        result = [t for t in result if t.due_date and t.due_date < f.due_before]
    if f.tags:
        result = [t for t in result if any(tag in t.tags for tag in f.tags)]
    return result


class SavedViewStore:
    def __init__(self, store_dir: Path = _DEFAULT_DIR):
        self._dir = Path(store_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, view_id: str) -> Path:
        return self._dir / f"{view_id}.json"

    def save(self, view: SavedView) -> None:
        self._path(view.view_id).write_text(json.dumps(view.to_dict(), indent=2))

    def load(self, view_id: str) -> Optional[SavedView]:
        p = self._path(view_id)
        return SavedView.from_dict(json.loads(p.read_text())) if p.exists() else None

    def delete(self, view_id: str) -> bool:
        p = self._path(view_id)
        if p.exists():
            p.unlink()
            return True
        return False

    def all(self) -> List[SavedView]:
        views = []
        for p in sorted(self._dir.glob("*.json")):
            try:
                views.append(SavedView.from_dict(json.loads(p.read_text())))
            except (json.JSONDecodeError, KeyError):
                pass
        return views


class TaskViewService:
    def __init__(self, task_service, view_store: SavedViewStore = None):
        self._tasks = task_service
        self._views = view_store or SavedViewStore()

    def search(self, f: TaskFilter, as_of: Optional[date] = None) -> List[Task]:
        return apply_filter(self._tasks.list_all(), f, as_of)

    def save_view(self, name: str, f: TaskFilter) -> SavedView:
        if not name or not name.strip():
            raise ValueError("view name must not be empty")
        view = SavedView(name=name.strip(), task_filter=f)
        self._views.save(view)
        return view

    def get_view(self, view_id: str) -> Optional[SavedView]:
        return self._views.load(view_id)

    def delete_view(self, view_id: str) -> bool:
        return self._views.delete(view_id)

    def list_views(self) -> List[SavedView]:
        return self._views.all()

    def execute_view(self, view_id: str, as_of: Optional[date] = None) -> List[Task]:
        view = self._views.load(view_id)
        if view is None:
            raise KeyError(f"view {view_id!r} not found")
        return apply_filter(self._tasks.list_all(), view.task_filter, as_of)
