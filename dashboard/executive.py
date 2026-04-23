from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional


@dataclass
class ProjectHealthSummary:
    project_id: str
    name: str
    completion_pct: float = 0.0
    is_at_risk: bool = False
    overdue_count: int = 0


@dataclass
class ReleaseReadiness:
    release_id: str
    name: str
    due_date: date
    readiness_pct: float = 0.0
    is_delayed: bool = False


@dataclass
class CommitmentRisk:
    total: int = 0
    missed: int = 0
    due_soon: int = 0

    @property
    def risk_score(self) -> float:
        if self.total == 0:
            return 0.0
        return round((self.missed + self.due_soon * 0.5) / self.total, 2)


@dataclass
class ExecutiveDashboard:
    as_of_date: date
    project_health: List[ProjectHealthSummary] = field(default_factory=list)
    release_readiness: List[ReleaseReadiness] = field(default_factory=list)
    commitment_risk: CommitmentRisk = field(default_factory=CommitmentRisk)
    total_overdue: int = 0
    total_blocked: int = 0

    @property
    def projects_at_risk(self) -> int:
        return sum(1 for p in self.project_health if p.is_at_risk)

    @property
    def releases_delayed(self) -> int:
        return sum(1 for r in self.release_readiness if r.is_delayed)

    def to_dict(self) -> dict:
        return {
            "as_of_date": self.as_of_date.isoformat(),
            "projects_at_risk": self.projects_at_risk,
            "releases_delayed": self.releases_delayed,
            "commitment_risk_score": self.commitment_risk.risk_score,
            "total_overdue": self.total_overdue,
            "total_blocked": self.total_blocked,
        }


class ExecutiveDashboardService:
    def build(
        self,
        as_of: date,
        project_health: Optional[List[ProjectHealthSummary]] = None,
        release_readiness: Optional[List[ReleaseReadiness]] = None,
        commitment_risk: Optional[CommitmentRisk] = None,
        total_overdue: int = 0,
        total_blocked: int = 0,
    ) -> ExecutiveDashboard:
        return ExecutiveDashboard(
            as_of_date=as_of,
            project_health=project_health or [],
            release_readiness=release_readiness or [],
            commitment_risk=commitment_risk or CommitmentRisk(),
            total_overdue=total_overdue,
            total_blocked=total_blocked,
        )
