from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Literal, Optional

Frequency = Literal["daily", "weekly", "biweekly", "monthly"]


@dataclass
class PostponeRecord:
    from_date: date
    to_date: date
    reason: str = ""

    def to_dict(self) -> dict:
        return {"from_date": self.from_date.isoformat(), "to_date": self.to_date.isoformat(), "reason": self.reason}

    @classmethod
    def from_dict(cls, d: dict) -> "PostponeRecord":
        return cls(
            from_date=date.fromisoformat(d["from_date"]),
            to_date=date.fromisoformat(d["to_date"]),
            reason=d.get("reason", ""),
        )


@dataclass
class RecurrenceRule:
    frequency: Frequency
    interval: int = 1       # e.g. interval=2 with "weekly" = every 2 weeks
    end_date: Optional[date] = None

    def next_occurrence(self, from_date: date) -> Optional[date]:
        if self.frequency == "daily":
            nxt = from_date + timedelta(days=self.interval)
        elif self.frequency == "weekly":
            nxt = from_date + timedelta(weeks=self.interval)
        elif self.frequency == "biweekly":
            nxt = from_date + timedelta(weeks=2 * self.interval)
        elif self.frequency == "monthly":
            month = from_date.month - 1 + self.interval
            year = from_date.year + month // 12
            month = month % 12 + 1
            day = min(from_date.day, _days_in_month(year, month))
            nxt = date(year, month, day)
        else:
            return None
        if self.end_date and nxt > self.end_date:
            return None
        return nxt

    def to_dict(self) -> dict:
        return {
            "frequency": self.frequency,
            "interval": self.interval,
            "end_date": self.end_date.isoformat() if self.end_date else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RecurrenceRule":
        ed = d.get("end_date")
        return cls(
            frequency=d["frequency"],
            interval=d.get("interval", 1),
            end_date=date.fromisoformat(ed) if ed else None,
        )


def _days_in_month(year: int, month: int) -> int:
    import calendar
    return calendar.monthrange(year, month)[1]


class PostponeService:
    def __init__(self, task_service):
        self._tasks = task_service
        self._history: dict = {}     # task_id -> List[PostponeRecord]

    def postpone(self, task_id: str, new_due: date, reason: str = "") -> None:
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"task {task_id!r} not found")
        if task.due_date is None:
            raise ValueError("task has no due date to postpone from")
        record = PostponeRecord(from_date=task.due_date, to_date=new_due, reason=reason)
        self._history.setdefault(task_id, []).append(record)
        self._tasks.update(task_id, due_date=new_due)

    def postpone_count(self, task_id: str) -> int:
        return len(self._history.get(task_id, []))

    def postpone_history(self, task_id: str) -> List[PostponeRecord]:
        return list(self._history.get(task_id, []))

    def is_repeatedly_delayed(self, task_id: str, threshold: int = 2) -> bool:
        return self.postpone_count(task_id) >= threshold

    def repeatedly_delayed_tasks(self, task_ids: List[str], threshold: int = 2) -> List[str]:
        return [tid for tid in task_ids if self.is_repeatedly_delayed(tid, threshold)]
