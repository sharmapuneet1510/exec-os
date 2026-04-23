from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from tasks.model import Task


@dataclass
class ProjectHealth:
    project_id: str
    total_tasks: int = 0
    completed_tasks: int = 0
    overdue_tasks: int = 0
    blocked_tasks: int = 0

    @property
    def completion_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return round(self.completed_tasks / self.total_tasks, 2)

    @property
    def is_at_risk(self) -> bool:
        if self.total_tasks == 0:
            return False
        overdue_pct = self.overdue_tasks / self.total_tasks
        return overdue_pct >= 0.2 or self.blocked_tasks >= 3

    @property
    def health_label(self) -> str:
        if self.is_at_risk:
            return "at_risk"
        if self.completion_rate >= 0.8:
            return "healthy"
        if self.completion_rate >= 0.5:
            return "moderate"
        return "poor"

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "overdue_tasks": self.overdue_tasks,
            "blocked_tasks": self.blocked_tasks,
            "completion_rate": self.completion_rate,
            "is_at_risk": self.is_at_risk,
            "health_label": self.health_label,
        }


class ProjectHealthService:
    def compute(self, project_id: str, tasks: List[Task], as_of: Optional[date] = None) -> ProjectHealth:
        today = as_of or date.today()
        project_tasks = [t for t in tasks if t.project_id == project_id]
        completed = sum(1 for t in project_tasks if t.status == "done")
        overdue = sum(
            1 for t in project_tasks
            if t.due_date and t.due_date < today and t.status not in ("done", "cancelled")
        )
        blocked = sum(1 for t in project_tasks if t.status == "in_progress" and t.priority == "critical")
        return ProjectHealth(
            project_id=project_id,
            total_tasks=len(project_tasks),
            completed_tasks=completed,
            overdue_tasks=overdue,
            blocked_tasks=blocked,
        )

    def compute_all(self, project_ids: List[str], tasks: List[Task], as_of: Optional[date] = None) -> List[ProjectHealth]:
        return [self.compute(pid, tasks, as_of) for pid in project_ids]
