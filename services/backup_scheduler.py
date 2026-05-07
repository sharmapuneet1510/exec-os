"""
Automated backup scheduler using APScheduler.
Runs daily database backups and manages retention policy.
"""
import logging
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler

from backup.service import BackupService

logger = logging.getLogger(__name__)

BACKUP_DIR = Path.home() / ".commanddesk" / "backups"
RETENTION_COUNT = 7  # Keep only last 7 backups


class BackupScheduler:
    """Manages automated database backups."""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.service = BackupService()

    def run(self):
        """Execute a backup and apply retention policy."""
        try:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            manifest = self.service.create_backup(BACKUP_DIR)
            logger.info(f"✓ Backup created: {manifest.path} ({manifest.size_bytes} bytes)")

            # Apply retention policy
            self._cleanup_old_backups()
        except Exception as e:
            logger.error(f"✗ Backup failed: {e}")

    def _cleanup_old_backups(self):
        """Keep only the last N backups, delete older ones."""
        try:
            backups = self.service.list_backups(BACKUP_DIR)
            if len(backups) > RETENTION_COUNT:
                to_delete = backups[RETENTION_COUNT:]
                for manifest in to_delete:
                    backup_path = Path(manifest.path)
                    if backup_path.exists():
                        backup_path.unlink()
                        logger.info(f"Deleted old backup: {manifest.path}")
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

    def start(self):
        """Start the backup scheduler (daily at 2:00 AM)."""
        self.scheduler.add_job(
            self.run,
            'cron',
            hour=2,
            minute=0,
            id='daily_backup',
            replace_existing=True
        )
        self.scheduler.start()
        logger.info("✓ Backup scheduler started (daily at 2:00 AM)")

    def shutdown(self):
        """Gracefully shut down the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("✓ Backup scheduler shutdown")


# Global scheduler instance
_backup_scheduler: BackupScheduler = None


def start_backup_scheduler() -> BackupScheduler:
    """Initialize and start the backup scheduler."""
    global _backup_scheduler
    if _backup_scheduler is None:
        _backup_scheduler = BackupScheduler()
        _backup_scheduler.start()
    return _backup_scheduler


def shutdown_backup_scheduler():
    """Shut down the backup scheduler."""
    global _backup_scheduler
    if _backup_scheduler is not None:
        _backup_scheduler.shutdown()
        _backup_scheduler = None
