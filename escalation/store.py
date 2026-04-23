import json
from pathlib import Path
from typing import Optional

from .model import EscalationRecord

_DEFAULT_DIR = Path.home() / ".commanddesk" / "escalations"


class JSONEscalationStore:
    def __init__(self, store_dir: Path = _DEFAULT_DIR):
        self._dir = store_dir

    def _path(self, task_id: str) -> Path:
        return self._dir / f"{task_id}.json"

    def load(self, task_id: str) -> Optional[EscalationRecord]:
        p = self._path(task_id)
        if not p.exists():
            return None
        with open(p, "r", encoding="utf-8") as f:
            return EscalationRecord.from_dict(json.load(f))

    def save(self, record: EscalationRecord) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._path(record.task_id), "w", encoding="utf-8") as f:
            json.dump(record.to_dict(), f, indent=2)

    def delete(self, task_id: str) -> None:
        p = self._path(task_id)
        if p.exists():
            p.unlink()

    def all(self) -> list[EscalationRecord]:
        if not self._dir.exists():
            return []
        records = []
        for p in self._dir.glob("*.json"):
            with open(p, "r", encoding="utf-8") as f:
                records.append(EscalationRecord.from_dict(json.load(f)))
        return records
