from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional


@dataclass
class TaskSummary:
    task_id: str
    title: str
    due_date: Optional[date] = None
    is_overdue: bool = False
    is_blocked: bool = False
    is_completed: bool = False


@dataclass
class CommitmentSummary:
    commitment_id: str
    title: str
    due_date: date
    is_missed: bool = False


@dataclass
class MilestoneSummary:
    milestone_id: str
    title: str
    due_date: date
    is_overdue: bool = False


@dataclass
class OperationalDashboard:
    as_of_date: date
    total_tasks_today: int = 0
    completed_today: int = 0
    overdue_tasks: List[TaskSummary] = field(default_factory=list)
    blocked_tasks: List[TaskSummary] = field(default_factory=list)
    upcoming_commitments: List[CommitmentSummary] = field(default_factory=list)
    upcoming_milestones: List[MilestoneSummary] = field(default_factory=list)

    @property
    def completion_rate(self) -> float:
        return (self.completed_today / self.total_tasks_today) if self.total_tasks_today > 0 else 0.0

    @property
    def overdue_count(self) -> int:
        return len(self.overdue_tasks)

    @property
    def blocked_count(self) -> int:
        return len(self.blocked_tasks)

    def to_dict(self) -> dict:
        return {
            "as_of_date": self.as_of_date.isoformat(),
            "total_tasks_today": self.total_tasks_today,
            "completed_today": self.completed_today,
            "completion_rate": round(self.completion_rate, 2),
            "overdue_count": self.overdue_count,
            "blocked_count": self.blocked_count,
            "upcoming_commitments": len(self.upcoming_commitments),
            "upcoming_milestones": len(self.upcoming_milestones),
        }


class OperationalDashboardService:
    """
    Builds the operational dashboard from raw task/commitment/milestone lists.
    In production these would be injected from repository services.
    """

    def build(
        self,
        as_of: date,
        all_tasks: List[TaskSummary],
        commitments: Optional[List[CommitmentSummary]] = None,
        milestones: Optional[List[MilestoneSummary]] = None,
        lookahead_days: int = 7,
    ) -> OperationalDashboard:
        today_tasks = [t for t in all_tasks if t.due_date == as_of or (t.due_date and t.due_date <= as_of and not t.is_completed)]
        overdue = [t for t in all_tasks if t.is_overdue and not t.is_completed]
        blocked = [t for t in all_tasks if t.is_blocked and not t.is_completed]
        completed = [t for t in all_tasks if t.is_completed and t.due_date == as_of]

        horizon = as_of + timedelta(days=lookahead_days)
        upcoming_commits = [
            c for c in (commitments or [])
            if as_of <= c.due_date <= horizon
        ]
        upcoming_miles = [
            m for m in (milestones or [])
            if as_of <= m.due_date <= horizon
        ]

        return OperationalDashboard(
            as_of_date=as_of,
            total_tasks_today=len(today_tasks),
            completed_today=len(completed),
            overdue_tasks=overdue,
            blocked_tasks=blocked,
            upcoming_commitments=upcoming_commits,
            upcoming_milestones=upcoming_miles,
        )
