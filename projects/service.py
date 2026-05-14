from datetime import date
from typing import List, Optional
from .model import Project, ProjectStatus
from .store import JSONProjectStore


class ProjectService:
    def __init__(self, store: JSONProjectStore = None):
        self._store = store or JSONProjectStore()

    def create(
        self,
        name: str,
        description: str = "",
        status: ProjectStatus = "active",
        owner: Optional[str] = None,
        due_date: Optional[date] = None,
        tags: Optional[List[str]] = None,
    ) -> Project:
        if not name or not name.strip():
            raise ValueError("project name must not be empty")
        project = Project(
            name=name.strip(),
            description=description,
            status=status,
            owner=owner,
            due_date=due_date,
            tags=tags or [],
        )
        self._store.save(project)
        return project

    def get(self, project_id: str) -> Optional[Project]:
        return self._store.load(project_id)

    def update(self, project_id: str, **kwargs) -> Project:
        project = self._store.load(project_id)
        if project is None:
            raise KeyError(f"project {project_id!r} not found")
        allowed = {"name", "description", "status", "owner", "due_date", "tags"}
        for k, v in kwargs.items():
            if k not in allowed:
                raise ValueError(f"unknown field {k!r}")
            if k == "name":
                if not v or not str(v).strip():
                    raise ValueError("project name must not be empty")
                v = v.strip()
            setattr(project, k, v)
        self._store.save(project)
        return project

    def delete(self, project_id: str) -> bool:
        return self._store.delete(project_id)

    def list_all(self) -> List[Project]:
        return self._store.all()

    def list_by_status(self, status: ProjectStatus) -> List[Project]:
        return [p for p in self._store.all() if p.status == status]

    def archive(self, project_id: str) -> Project:
        return self.update(project_id, status="archived")

    def complete(self, project_id: str) -> Project:
        return self.update(project_id, status="completed")
