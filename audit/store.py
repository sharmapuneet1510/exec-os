import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .model import AuditEvent, EventType

_DEFAULT_LOG = Path.home() / ".commanddesk" / "audit_log.jsonl"


class JSONAuditStore:
    """Append-only JSONL audit log. One JSON object per line."""

    def __init__(self, log_path: Path = _DEFAULT_LOG):
        self._path = log_path

    def append(self, event: AuditEvent) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    def all(self) -> List[AuditEvent]:
        if not self._path.exists():
            return []
        events = []
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(AuditEvent.from_dict(json.loads(line)))
        return events

    def query(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        event_type: Optional[EventType] = None,
        actor: Optional[str] = None,
    ) -> List[AuditEvent]:
        results = self.all()
        if start:
            results = [e for e in results if e.timestamp >= start]
        if end:
            results = [e for e in results if e.timestamp <= end]
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if actor:
            results = [e for e in results if e.actor == actor]
        return results
