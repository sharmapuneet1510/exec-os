"""APScheduler-based daily SOD/EOD email scheduler + periodic alert engine."""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

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


def _run_alert_engine():
    try:
        from web.alert_engine import run
        run()
    except Exception as e:
        log.error("Alert engine failed: %s", e)


def _run_planner_reminder():
    """Every 2 hours: remind what's next on today's plan."""
    try:
        from datetime import date, datetime, timedelta
        from db.base import SessionLocal
        from db.models import DayPlanItemORM, AlertORM

        db = SessionLocal()
        try:
            today = date.today()
            now_str = datetime.now().strftime("%H:%M")
            soon_str = (datetime.now() + timedelta(minutes=45)).strftime("%H:%M")

            upcoming = db.query(DayPlanItemORM).filter(
                DayPlanItemORM.plan_date == today,
                DayPlanItemORM.completed == False,      # noqa: E712
                DayPlanItemORM.time_start >= now_str,
                DayPlanItemORM.time_start <= soon_str,
            ).order_by(DayPlanItemORM.time_start).first()

            if upcoming:
                db.add(AlertORM(
                    title=f"⏰ Coming up at {upcoming.time_start}: {upcoming.title}",
                    message=f"Type: {upcoming.item_type} · {upcoming.time_start}–{upcoming.time_end}",
                    severity="info",
                    source=f"auto:reminder:{upcoming.item_id}:{today.isoformat()}:{now_str[:2]}",
                    is_read=False,
                ))
                db.commit()
        finally:
            db.close()
    except Exception as e:
        log.error("Planner reminder failed: %s", e)


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
    # Alert engine: run every 15 minutes
    _scheduler.add_job(_run_alert_engine, IntervalTrigger(minutes=15),
                       id="alert_engine", replace_existing=True, misfire_grace_time=60)
    # Planner reminder: every 2 hours
    _scheduler.add_job(_run_planner_reminder, IntervalTrigger(hours=2),
                       id="planner_reminder", replace_existing=True, misfire_grace_time=300)
    if not _scheduler.running:
        _scheduler.start()
        log.info("Scheduler started")
    # Run alert engine once immediately on startup (in background thread)
    import threading
    threading.Thread(target=_run_alert_engine, daemon=True, name="alert-engine-init").start()


def stop():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
