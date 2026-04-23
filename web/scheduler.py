"""APScheduler-based daily SOD/EOD email scheduler."""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger("execos.scheduler")
_scheduler = BackgroundScheduler(timezone="UTC", daemon=True)


def _run_sod():
    from db.base import SessionLocal
    from web.email_sender import send_sod
    db = SessionLocal()
    try:
        send_sod(db)
        log.info("SOD email sent")
    except Exception as e:
        log.error("SOD email failed: %s", e)
    finally:
        db.close()


def _run_eod():
    from db.base import SessionLocal
    from web.email_sender import send_eod
    db = SessionLocal()
    try:
        send_eod(db)
        log.info("EOD email sent")
    except Exception as e:
        log.error("EOD email failed: %s", e)
    finally:
        db.close()


def reschedule(sod_time: str = "08:00", eod_time: str = "18:00"):
    """(Re)schedule SOD/EOD jobs. Times are HH:MM in local system timezone."""
    sod_h, sod_m = map(int, sod_time.split(":"))
    eod_h, eod_m = map(int, eod_time.split(":"))

    _scheduler.add_job(_run_sod, CronTrigger(hour=sod_h, minute=sod_m),
                       id="sod", replace_existing=True, misfire_grace_time=300)
    _scheduler.add_job(_run_eod, CronTrigger(hour=eod_h, minute=eod_m),
                       id="eod", replace_existing=True, misfire_grace_time=300)
    log.info("Scheduled SOD=%s EOD=%s", sod_time, eod_time)


def start(sod_time: str = "08:00", eod_time: str = "18:00"):
    reschedule(sod_time, eod_time)
    if not _scheduler.running:
        _scheduler.start()
        log.info("Scheduler started")


def stop():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
