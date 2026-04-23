import json
from datetime import date
from pathlib import Path
from typing import List, Optional

from .model import DailyPlan

_DEFAULT_PLANS_DIR = Path.home() / ".commanddesk" / "plans"


class JSONPlanStore:
    """Persists DailyPlan objects as JSON files under a plans directory."""

    def __init__(self, plans_dir: Path = _DEFAULT_PLANS_DIR):
        self._dir = plans_dir

    def _path(self, plan_date: date) -> Path:
        return self._dir / f"{plan_date.isoformat()}.json"

    def load(self, plan_date: date) -> Optional[DailyPlan]:
        p = self._path(plan_date)
        if not p.exists():
            return None
        with open(p, "r", encoding="utf-8") as f:
            return DailyPlan.from_dict(json.load(f))

    def load_or_create(self, plan_date: date) -> DailyPlan:
        return self.load(plan_date) or DailyPlan(plan_date=plan_date)

    def save(self, plan: DailyPlan) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._path(plan.plan_date), "w", encoding="utf-8") as f:
            json.dump(plan.to_dict(), f, indent=2)

    def list_dates(self) -> List[date]:
        if not self._dir.exists():
            return []
        return sorted(
            date.fromisoformat(p.stem)
            for p in self._dir.glob("????-??-??.json")
        )
