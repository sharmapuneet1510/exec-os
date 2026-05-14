import json
from pathlib import Path
from typing import List, Optional
from .model import Project

_DEFAULT_DIR = Path.home() / ".commanddesk" / "projects"


class JSONProjectStore:
    def __init__(self, store_dir: Path = _DEFAULT_DIR):
        self._dir = Path(store_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, project_id: str) -> Path:
        return self._dir / f"{project_id}.json"

    def save(self, project: Project) -> None:
        self._path(project.project_id).write_text(json.dumps(project.to_dict(), indent=2))

    def load(self, project_id: str) -> Optional[Project]:
        p = self._path(project_id)
        return Project.from_dict(json.loads(p.read_text())) if p.exists() else None

    def delete(self, project_id: str) -> bool:
        p = self._path(project_id)
        if p.exists():
            p.unlink()
            return True
        return False

    def all(self) -> List[Project]:
        projects = []
        for p in sorted(self._dir.glob("*.json")):
            try:
                projects.append(Project.from_dict(json.loads(p.read_text())))
            except (json.JSONDecodeError, KeyError):
                pass
        return projects
