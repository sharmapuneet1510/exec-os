from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Optional
from uuid import uuid4

Priority = Literal["low", "medium", "high", "critical"]
Status = Literal["todo", "in_progress", "done", "cancelled"]


@dataclass
class Task:
    title: str
    task_id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    due_date: Optional[date] = None
    priority: Priority = "medium"
    status: Status = "todo"
    project_id: Optional[str] = None
    reminder_date: Optional[date] = None
    tags: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "reminder_date": self.reminder_date.isoformat() if self.reminder_date else None,
            "priority": self.priority,
            "status": self.status,
            "project_id": self.project_id,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        due = d.get("due_date")
        reminder = d.get("reminder_date")
        return cls(
            task_id=d["task_id"],
            title=d["title"],
            description=d.get("description", ""),
            due_date=date.fromisoformat(due) if due else None,
            reminder_date=date.fromisoformat(reminder) if reminder else None,
            priority=d.get("priority", "medium"),
            status=d.get("status", "todo"),
            project_id=d.get("project_id"),
            tags=list(d.get("tags", [])),
        )
