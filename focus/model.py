from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional

NotificationLevel = Literal["critical", "high", "normal", "low"]

# Notifications at or below this level are suppressed during focus / quiet hours
_SUPPRESS_BELOW: NotificationLevel = "high"
_LEVEL_ORDER: list[NotificationLevel] = ["critical", "high", "normal", "low"]


def is_non_critical(level: NotificationLevel) -> bool:
    """Return True if the level is below 'high' (i.e. normal or low)."""
    return _LEVEL_ORDER.index(level) > _LEVEL_ORDER.index(_SUPPRESS_BELOW)


@dataclass
class FocusMode:
    enabled: bool = False
    started_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None          # None = indefinite

    def active_until(self) -> Optional[datetime]:
        if not self.enabled or not self.started_at or not self.duration_minutes:
            return None
        from datetime import timedelta
        return self.started_at + timedelta(minutes=self.duration_minutes)

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "duration_minutes": self.duration_minutes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FocusMode":
        return cls(
            enabled=bool(d.get("enabled", False)),
            started_at=datetime.fromisoformat(d["started_at"]) if d.get("started_at") else None,
            duration_minutes=d.get("duration_minutes"),
        )


@dataclass
class QuietHours:
    enabled: bool = False
    start_time: str = "22:00"   # HH:MM local
    end_time: str = "08:00"     # HH:MM local

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "QuietHours":
        return cls(
            enabled=bool(d.get("enabled", False)),
            start_time=d.get("start_time", "22:00"),
            end_time=d.get("end_time", "08:00"),
        )


@dataclass
class FocusState:
    focus_mode: FocusMode = field(default_factory=FocusMode)
    quiet_hours: QuietHours = field(default_factory=QuietHours)

    def to_dict(self) -> dict:
        return {
            "focus_mode": self.focus_mode.to_dict(),
            "quiet_hours": self.quiet_hours.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FocusState":
        return cls(
            focus_mode=FocusMode.from_dict(d.get("focus_mode", {})),
            quiet_hours=QuietHours.from_dict(d.get("quiet_hours", {})),
        )
