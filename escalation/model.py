from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional

Priority = Literal["low", "medium", "high", "critical"]
Visibility = Literal["normal", "elevated", "high"]

PRIORITY_ORDER: list[Priority] = ["low", "medium", "high", "critical"]


def boost_priority(current: Priority) -> Priority:
    """Return the next priority level up, capped at critical."""
    idx = PRIORITY_ORDER.index(current)
    return PRIORITY_ORDER[min(idx + 1, len(PRIORITY_ORDER) - 1)]


@dataclass
class DelayThreshold:
    days_delayed: int = 7
    escalate_visibility_to: Visibility = "high"
    boost_priority: bool = True


@dataclass
class EscalationRecord:
    task_id: str
    delayed_since: datetime
    days_delayed: int
    original_priority: Priority
    current_priority: Priority
    visibility_level: Visibility = "normal"
    priority_boosted: bool = False
    notified_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "delayed_since": self.delayed_since.isoformat(),
            "days_delayed": self.days_delayed,
            "original_priority": self.original_priority,
            "current_priority": self.current_priority,
            "visibility_level": self.visibility_level,
            "priority_boosted": self.priority_boosted,
            "notified_at": self.notified_at.isoformat() if self.notified_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EscalationRecord":
        return cls(
            task_id=data["task_id"],
            delayed_since=datetime.fromisoformat(data["delayed_since"]),
            days_delayed=int(data["days_delayed"]),
            original_priority=data["original_priority"],
            current_priority=data["current_priority"],
            visibility_level=data.get("visibility_level", "normal"),
            priority_boosted=bool(data.get("priority_boosted", False)),
            notified_at=datetime.fromisoformat(data["notified_at"]) if data.get("notified_at") else None,
        )
