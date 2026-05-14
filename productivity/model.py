from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class DailyMetric:
    metric_date: date
    planned: int = 0
    completed: int = 0
    overdue: int = 0

    @property
    def completion_rate(self) -> float:
        return (self.completed / self.planned) if self.planned > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "metric_date": self.metric_date.isoformat(),
            "planned": self.planned,
            "completed": self.completed,
            "overdue": self.overdue,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DailyMetric":
        return cls(
            metric_date=date.fromisoformat(d["metric_date"]),
            planned=int(d.get("planned", 0)),
            completed=int(d.get("completed", 0)),
            overdue=int(d.get("overdue", 0)),
        )


@dataclass
class ProductivityReport:
    start_date: date
    end_date: date
    metrics: List[DailyMetric] = field(default_factory=list)

    @property
    def avg_completion_rate(self) -> float:
        rates = [m.completion_rate for m in self.metrics if m.planned > 0]
        return sum(rates) / len(rates) if rates else 0.0

    @property
    def total_planned(self) -> int:
        return sum(m.planned for m in self.metrics)

    @property
    def total_completed(self) -> int:
        return sum(m.completed for m in self.metrics)

    @property
    def total_overdue(self) -> int:
        return sum(m.overdue for m in self.metrics)

    @property
    def overdue_trend(self) -> List[int]:
        """Overdue counts in date order for charting."""
        return [m.overdue for m in sorted(self.metrics, key=lambda m: m.metric_date)]
