import json
from pathlib import Path
from typing import List, Optional
from .model import Task

_DEFAULT_DIR = Path.home() / ".commanddesk" / "tasks"


class JSONTaskStore:
    def __init__(self, store_dir: Path = _DEFAULT_DIR):
        self._dir = Path(store_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, task_id: str) -> Path:
        return self._dir / f"{task_id}.json"

    def save(self, task: Task) -> None:
        self._path(task.task_id).write_text(json.dumps(task.to_dict(), indent=2))

    def load(self, task_id: str) -> Optional[Task]:
        p = self._path(task_id)
        if not p.exists():
            return None
        return Task.from_dict(json.loads(p.read_text()))

    def delete(self, task_id: str) -> bool:
        p = self._path(task_id)
        if p.exists():
            p.unlink()
            return True
        return False

    def all(self) -> List[Task]:
        tasks = []
        for p in sorted(self._dir.glob("*.json")):
            try:
                tasks.append(Task.from_dict(json.loads(p.read_text())))
            except (json.JSONDecodeError, KeyError):
                pass
        return tasks
