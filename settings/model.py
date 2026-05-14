from dataclasses import dataclass, field
from typing import Literal


@dataclass
class UserSettings:
    # Work hours
    work_hours_start: str = "09:00"       # HH:MM 24-hr
    work_hours_end: str = "18:00"

    # Daily summary times
    sod_time: str = "08:45"               # Start-of-day summary generation time
    eod_time: str = "18:15"               # End-of-day summary generation time

    # Reminders
    reminder_interval_minutes: int = 30   # How often progress reminders fire

    # UI
    default_view: Literal["tasks", "projects", "dashboard", "commitments"] = "tasks"

    # Notifications
    desktop_notifications_enabled: bool = True
    email_notifications_enabled: bool = False

    # Startup behaviour
    startup_on_boot: bool = False
    minimize_to_tray: bool = True

    def to_dict(self) -> dict:
        return {
            "work_hours_start": self.work_hours_start,
            "work_hours_end": self.work_hours_end,
            "sod_time": self.sod_time,
            "eod_time": self.eod_time,
            "reminder_interval_minutes": self.reminder_interval_minutes,
            "default_view": self.default_view,
            "desktop_notifications_enabled": self.desktop_notifications_enabled,
            "email_notifications_enabled": self.email_notifications_enabled,
            "startup_on_boot": self.startup_on_boot,
            "minimize_to_tray": self.minimize_to_tray,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserSettings":
        return cls(
            work_hours_start=data.get("work_hours_start", "09:00"),
            work_hours_end=data.get("work_hours_end", "18:00"),
            sod_time=data.get("sod_time", "08:45"),
            eod_time=data.get("eod_time", "18:15"),
            reminder_interval_minutes=int(data.get("reminder_interval_minutes", 30)),
            default_view=data.get("default_view", "tasks"),
            desktop_notifications_enabled=bool(data.get("desktop_notifications_enabled", True)),
            email_notifications_enabled=bool(data.get("email_notifications_enabled", False)),
            startup_on_boot=bool(data.get("startup_on_boot", False)),
            minimize_to_tray=bool(data.get("minimize_to_tray", True)),
        )
