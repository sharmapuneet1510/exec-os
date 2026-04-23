import logging
from datetime import datetime, timezone
from typing import Optional

from .model import DelayThreshold, EscalationRecord, Priority, Visibility, boost_priority
from .store import JSONEscalationStore

logger = logging.getLogger(__name__)


class EscalationService:
    """
    Detects tasks stuck in a delayed state beyond the threshold and escalates them:
      - Raises visibility to HIGH (moves to top of board)
      - Optionally boosts priority by one level
      - Notifies the assignee
    """

    def __init__(
        self,
        store: JSONEscalationStore,
        threshold: Optional[DelayThreshold] = None,
    ):
        self._store = store
        self._threshold = threshold or DelayThreshold()

    def evaluate(self, task_id: str, delayed_since: datetime, current_priority: Priority) -> bool:
        """
        Returns True if the task has been delayed long enough to warrant escalation.
        Does NOT escalate — call escalate() to act.
        """
        days = (datetime.now(timezone.utc) - delayed_since).days
        return days >= self._threshold.days_delayed

    def escalate(
        self,
        task_id: str,
        delayed_since: datetime,
        current_priority: Priority,
    ) -> EscalationRecord:
        """
        Escalate a delayed task: raise visibility, optionally boost priority.
        Idempotent — re-escalating an already-escalated task updates days_delayed only.
        """
        existing = self._store.load(task_id)
        days = (datetime.now(timezone.utc) - delayed_since).days

        if existing:
            existing.days_delayed = days
            self._store.save(existing)
            logger.info("Task %s already escalated (day %d)", task_id, days)
            return existing

        new_priority = boost_priority(current_priority) if self._threshold.boost_priority else current_priority

        record = EscalationRecord(
            task_id=task_id,
            delayed_since=delayed_since,
            days_delayed=days,
            original_priority=current_priority,
            current_priority=new_priority,
            visibility_level=self._threshold.escalate_visibility_to,
            priority_boosted=new_priority != current_priority,
        )
        self._store.save(record)
        logger.info(
            "Escalated task %s: visibility=%s priority %s→%s",
            task_id, record.visibility_level, current_priority, new_priority,
        )
        return record

    def notify(self, record: EscalationRecord, assignee: Optional[str] = None) -> None:
        """
        Dispatch an escalation alert. Marks notified_at on the record.
        Concrete delivery (desktop/email) is handled by the notification engine.
        """
        if record.notified_at:
            logger.debug("Task %s already notified at %s", record.task_id, record.notified_at)
            return

        msg = (
            f"Task {record.task_id} has been delayed for {record.days_delayed} day(s). "
            f"Visibility raised to {record.visibility_level}."
        )
        if record.priority_boosted:
            msg += f" Priority boosted: {record.original_priority} → {record.current_priority}."

        logger.warning("ESCALATION ALERT%s: %s", f" for {assignee}" if assignee else "", msg)

        record.notified_at = datetime.now(timezone.utc)
        self._store.save(record)

    def resolve(self, task_id: str) -> None:
        """Remove escalation record when the task is no longer delayed."""
        self._store.delete(task_id)
        logger.info("Escalation resolved for task %s", task_id)
