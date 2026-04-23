import logging
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class JobScheduler:
    """
    Thin wrapper around APScheduler's BackgroundScheduler.
    Runs jobs in background threads so the main thread stays free for the UI.
    """

    def __init__(self):
        self._scheduler = BackgroundScheduler(timezone="UTC")

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("Scheduler started")

    def shutdown(self, wait: bool = True) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info("Scheduler stopped")

    @property
    def running(self) -> bool:
        return self._scheduler.running

    # ── Job management ────────────────────────────────────────────────────────

    def add_cron_job(self, job_id: str, func: Callable, hour: int, minute: int) -> None:
        """Schedule a job to run daily at the given HH:MM (UTC)."""
        self._scheduler.add_job(
            func,
            trigger=CronTrigger(hour=hour, minute=minute),
            id=job_id,
            replace_existing=True,
        )
        logger.info("Registered cron job '%s' at %02d:%02d UTC", job_id, hour, minute)

    def add_interval_job(self, job_id: str, func: Callable, minutes: int) -> None:
        """Schedule a job to run every N minutes."""
        self._scheduler.add_job(
            func,
            trigger=IntervalTrigger(minutes=minutes),
            id=job_id,
            replace_existing=True,
        )
        logger.info("Registered interval job '%s' every %d min", job_id, minutes)

    def remove_job(self, job_id: str) -> None:
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
            logger.info("Removed job '%s'", job_id)

    def list_jobs(self) -> list[str]:
        return [job.id for job in self._scheduler.get_jobs()]
