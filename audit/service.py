import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .model import AuditEvent, EventType
from .store import JSONAuditStore

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, store: JSONAuditStore):
        self._store = store

    def log(
        self,
        event_type: EventType,
        description: str,
        actor: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_type=event_type,
            description=description,
            actor=actor,
            metadata=metadata or {},
        )
        self._store.append(event)
        logger.info("AUDIT [%s] %s — %s", event_type.value, actor, description)
        return event

    def query(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        event_type: Optional[EventType] = None,
        actor: Optional[str] = None,
    ) -> List[AuditEvent]:
        return self._store.query(start=start, end=end, event_type=event_type, actor=actor)

    def recent(self, n: int = 50) -> List[AuditEvent]:
        all_events = self._store.all()
        return sorted(all_events, key=lambda e: e.timestamp, reverse=True)[:n]
