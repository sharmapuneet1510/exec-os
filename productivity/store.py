import json
from datetime import date
from pathlib import Path
from typing import List, Optional

from .model import DailyMetric

_DEFAULT_DIR = Path.home() / ".commanddesk" / "metrics"


class JSONMetricsStore:
    def __init__(self, store_dir: Path = _DEFAULT_DIR):
        self._dir = store_dir

    def _path(self, d: date) -> Path:
        return self._dir / f"{d.isoformat()}.json"

    def save(self, metric: DailyMetric) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._path(metric.metric_date), "w", encoding="utf-8") as f:
            json.dump(metric.to_dict(), f, indent=2)

    def load(self, d: date) -> Optional[DailyMetric]:
        p = self._path(d)
        if not p.exists():
            return None
        with open(p, "r", encoding="utf-8") as f:
            return DailyMetric.from_dict(json.load(f))

    def range(self, start: date, end: date) -> List[DailyMetric]:
        results = []
        for p in self._dir.glob("????-??-??.json"):
            d = date.fromisoformat(p.stem)
            if start <= d <= end:
                with open(p, "r", encoding="utf-8") as f:
                    results.append(DailyMetric.from_dict(json.load(f)))
        return sorted(results, key=lambda m: m.metric_date)
