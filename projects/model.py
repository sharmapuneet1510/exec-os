from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Optional
from uuid import uuid4

ProjectStatus = Literal["active", "on_hold", "completed", "archived"]


@dataclass
class Project:
    name: str
    project_id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    status: ProjectStatus = "active"
    owner: Optional[str] = None
    due_date: Optional[date] = None
    tags: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "owner": self.owner,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        due = d.get("due_date")
        return cls(
            project_id=d["project_id"],
            name=d["name"],
            description=d.get("description", ""),
            status=d.get("status", "active"),
            owner=d.get("owner"),
            due_date=date.fromisoformat(due) if due else None,
            tags=list(d.get("tags", [])),
        )
