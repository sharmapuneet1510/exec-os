import logging
from datetime import datetime, timezone
from typing import Optional

from .model import FocusMode, FocusState, NotificationLevel, QuietHours, is_non_critical
from .store import JSONFocusStore

logger = logging.getLogger(__name__)


def _parse_hhmm(t: str) -> tuple[int, int]:
    h, m = t.split(":")
    return int(h), int(m)


def _in_quiet_window(now: datetime, start: str, end: str) -> bool:
    """
    Returns True if `now` falls within the quiet window.
    Handles overnight windows (e.g. 22:00 → 08:00).
    """
    sh, sm = _parse_hhmm(start)
    eh, em = _parse_hhmm(end)
    current_minutes = now.hour * 60 + now.minute
    start_minutes = sh * 60 + sm
    end_minutes = eh * 60 + em

    if start_minutes < end_minutes:
        # Same-day window (e.g. 09:00 → 17:00)
        return start_minutes <= current_minutes < end_minutes
    else:
        # Overnight window (e.g. 22:00 → 08:00)
        return current_minutes >= start_minutes or current_minutes < end_minutes


class FocusService:
    """
    Manages focus mode and quiet hours.
    Provides is_suppressed() so the notification engine can gate delivery.
    """

    def __init__(self, store: JSONFocusStore):
        self._store = store
        self._state: FocusState = store.load()

    # ── Focus mode ────────────────────────────────────────────────────────────

    def enable_focus(self, duration_minutes: Optional[int] = None) -> FocusMode:
        self._state.focus_mode = FocusMode(
            enabled=True,
            started_at=datetime.now(timezone.utc),
            duration_minutes=duration_minutes,
        )
        self._store.save(self._state)
        logger.info("Focus mode enabled%s",
                    f" for {duration_minutes} min" if duration_minutes else " indefinitely")
        return self._state.focus_mode

    def disable_focus(self) -> None:
        self._state.focus_mode = FocusMode(enabled=False)
        self._store.save(self._state)
        logger.info("Focus mode disabled")

    def is_focus_active(self) -> bool:
        fm = self._state.focus_mode
        if not fm.enabled:
            return False
        until = fm.active_until()
        if until and datetime.now(timezone.utc) >= until:
            # Duration expired — auto-disable
            self.disable_focus()
            return False
        return True

    # ── Quiet hours ───────────────────────────────────────────────────────────

    def set_quiet_hours(self, start_time: str, end_time: str, enabled: bool = True) -> QuietHours:
        self._state.quiet_hours = QuietHours(
            enabled=enabled, start_time=start_time, end_time=end_time
        )
        self._store.save(self._state)
        logger.info("Quiet hours set: %s → %s (enabled=%s)", start_time, end_time, enabled)
        return self._state.quiet_hours

    def is_in_quiet_hours(self, now: Optional[datetime] = None) -> bool:
        qh = self._state.quiet_hours
        if not qh.enabled:
            return False
        now = now or datetime.now()
        return _in_quiet_window(now, qh.start_time, qh.end_time)

    # ── Suppression gate ──────────────────────────────────────────────────────

    def is_suppressed(self, level: NotificationLevel, now: Optional[datetime] = None) -> bool:
        """
        Returns True if a notification of the given level should be silenced.
        Critical notifications are never suppressed.
        """
        if level == "critical":
            return False
        return self.is_focus_active() or self.is_in_quiet_hours(now)

    # ── State access ──────────────────────────────────────────────────────────

    @property
    def state(self) -> FocusState:
        return self._state
