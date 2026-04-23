import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from runtime.scheduler import JobScheduler
from .service import BackupService

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path.home() / ".commanddesk" / "backup_schedule.json"


@dataclass
class BackupScheduleConfig:
    enabled: bool = False
    hour: int = 3
    minute: int = 0
    dest_dir: str = str(Path.home() / ".commanddesk" / "backups")
    retain_count: int = 7

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "hour": self.hour,
            "minute": self.minute,
            "dest_dir": self.dest_dir,
            "retain_count": self.retain_count,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BackupScheduleConfig":
        return cls(
            enabled=bool(d.get("enabled", False)),
            hour=int(d.get("hour", 3)),
            minute=int(d.get("minute", 0)),
            dest_dir=d.get("dest_dir", str(Path.home() / ".commanddesk" / "backups")),
            retain_count=int(d.get("retain_count", 7)),
        )


class ScheduledBackupService:
    """Registers a daily backup job with the runtime scheduler."""

    JOB_ID = "scheduled_backup"

    def __init__(
        self,
        backup_service: BackupService,
        scheduler: JobScheduler,
        config_path: Path = _DEFAULT_CONFIG_PATH,
    ):
        self._backup = backup_service
        self._scheduler = scheduler
        self._config_path = config_path

    def schedule(self, config: BackupScheduleConfig) -> None:
        dest = Path(config.dest_dir)
        self._scheduler.add_cron_job(
            self.JOB_ID,
            lambda: self._run_backup(dest, config.retain_count),
            hour=config.hour,
            minute=config.minute,
        )
        self._save_config(config)
        logger.info("Scheduled daily backup at %02d:%02d → %s", config.hour, config.minute, dest)

    def unschedule(self) -> None:
        self._scheduler.remove_job(self.JOB_ID)
        config = self.load_config()
        config.enabled = False
        self._save_config(config)
        logger.info("Scheduled backup cancelled")

    def load_config(self) -> BackupScheduleConfig:
        if not self._config_path.exists():
            return BackupScheduleConfig()
        with open(self._config_path, "r", encoding="utf-8") as f:
            return BackupScheduleConfig.from_dict(json.load(f))

    def is_scheduled(self) -> bool:
        return self.JOB_ID in self._scheduler.list_jobs()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run_backup(self, dest: Path, retain_count: int) -> None:
        try:
            manifest = self._backup.create_backup(dest)
            logger.info("Scheduled backup completed: %s", manifest.path)
            self._apply_retention(dest, retain_count)
        except Exception as exc:
            logger.error("Scheduled backup failed: %s", exc)

    def _apply_retention(self, dest: Path, retain_count: int) -> None:
        manifests = self._backup.list_backups(dest)
        for old in manifests[retain_count:]:
            p = Path(old.path)
            if p.exists():
                p.unlink()
                logger.info("Retention: removed old backup %s", p)

    def _save_config(self, config: BackupScheduleConfig) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2)
