import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class EventType(str, Enum):
    TASK_CREATED       = "task_created"
    TASK_UPDATED       = "task_updated"
    TASK_COMPLETED     = "task_completed"
    TASK_DELETED       = "task_deleted"
    BACKUP_CREATED     = "backup_created"
    RESTORE_PERFORMED  = "restore_performed"
    SETTINGS_CHANGED   = "settings_changed"
    FOCUS_TOGGLED      = "focus_toggled"
    ESCALATION_RAISED  = "escalation_raised"
    SYSTEM_STARTUP     = "system_startup"
    SYSTEM_SHUTDOWN    = "system_shutdown"


@dataclass
class AuditEvent:
    event_type: EventType
    description: str
    actor: str = "system"
    metadata: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "actor": self.actor,
            "description": self.description,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AuditEvent":
        return cls(
            event_id=d["event_id"],
            timestamp=datetime.fromisoformat(d["timestamp"]),
            event_type=EventType(d["event_type"]),
            actor=d.get("actor", "system"),
            description=d["description"],
            metadata=d.get("metadata", {}),
        )
