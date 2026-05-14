import atexit
import logging
import signal
import sys
from typing import Optional

from settings.manager import SettingsManager
from settings.model import UserSettings
from .scheduler import JobScheduler
from .jobs import sod_summary_job, eod_summary_job, reminder_job

logger = logging.getLogger(__name__)


def _parse_hhmm(time_str: str) -> tuple[int, int]:
    h, m = time_str.split(":")
    return int(h), int(m)


class AppRuntime:
    """
    Boots and owns all background services for CommandDesk.
    Call start() once at application launch and stop() on exit.
    """

    def __init__(self, settings_manager: Optional[SettingsManager] = None):
        self._settings_manager = settings_manager or SettingsManager()
        self._scheduler = JobScheduler()
        self._started = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._started:
            logger.warning("AppRuntime.start() called more than once — ignored")
            return

        logger.info("CommandDesk runtime starting…")
        settings = self._settings_manager.load()

        self._register_jobs(settings)
        self._scheduler.start()

        atexit.register(self.stop)
        signal.signal(signal.SIGTERM, self._handle_signal)
        if sys.platform != "win32":
            signal.signal(signal.SIGHUP, self._handle_signal)

        self._started = True
        logger.info("CommandDesk runtime started. Jobs: %s", self._scheduler.list_jobs())

    def stop(self) -> None:
        if not self._started:
            return
        logger.info("CommandDesk runtime stopping…")
        self._scheduler.shutdown(wait=False)
        self._started = False
        logger.info("CommandDesk runtime stopped")

    @property
    def running(self) -> bool:
        return self._started and self._scheduler.running

    # ── Internal ──────────────────────────────────────────────────────────────

    def _register_jobs(self, settings: UserSettings) -> None:
        sod_h, sod_m = _parse_hhmm(settings.sod_time)
        eod_h, eod_m = _parse_hhmm(settings.eod_time)

        self._scheduler.add_cron_job("sod_summary", sod_summary_job, hour=sod_h, minute=sod_m)
        self._scheduler.add_cron_job("eod_summary", eod_summary_job, hour=eod_h, minute=eod_m)
        self._scheduler.add_interval_job(
            "reminder", reminder_job, minutes=settings.reminder_interval_minutes
        )

    def _handle_signal(self, signum, frame) -> None:
        logger.info("Signal %s received — shutting down", signum)
        self.stop()
        sys.exit(0)
