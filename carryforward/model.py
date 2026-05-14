from dataclasses import dataclass, field
from datetime import date
from typing import List


@dataclass
class CarryForwardRecord:
    task_id: str
    original_date: date       # date the task was first planned
    carried_date: date        # date it was carried into
    carry_count: int = 1      # how many times this task has been carried forward

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "original_date": self.original_date.isoformat(),
            "carried_date": self.carried_date.isoformat(),
            "carry_count": self.carry_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CarryForwardRecord":
        return cls(
            task_id=data["task_id"],
            original_date=date.fromisoformat(data["original_date"]),
            carried_date=date.fromisoformat(data["carried_date"]),
            carry_count=int(data.get("carry_count", 1)),
        )


@dataclass
class DailyPlan:
    plan_date: date
    task_ids: List[str] = field(default_factory=list)
    completed_task_ids: List[str] = field(default_factory=list)
    carry_forward_records: List[CarryForwardRecord] = field(default_factory=list)

    def is_complete(self, task_id: str) -> bool:
        return task_id in self.completed_task_ids

    def incomplete_task_ids(self) -> List[str]:
        return [t for t in self.task_ids if t not in self.completed_task_ids]

    def carried_task_ids(self) -> List[str]:
        return [r.task_id for r in self.carry_forward_records]

    def to_dict(self) -> dict:
        return {
            "plan_date": self.plan_date.isoformat(),
            "task_ids": self.task_ids,
            "completed_task_ids": self.completed_task_ids,
            "carry_forward_records": [r.to_dict() for r in self.carry_forward_records],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DailyPlan":
        return cls(
            plan_date=date.fromisoformat(data["plan_date"]),
            task_ids=data.get("task_ids", []),
            completed_task_ids=data.get("completed_task_ids", []),
            carry_forward_records=[
                CarryForwardRecord.from_dict(r)
                for r in data.get("carry_forward_records", [])
            ],
        )
