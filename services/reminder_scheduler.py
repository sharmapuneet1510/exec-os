"""
Reminder scheduler service using APScheduler.
Handles scheduling, triggering, and management of reminders based on their trigger type and patterns.
"""
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any
import json
import logging
from dateutil.relativedelta import relativedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from db.base import SessionLocal
from db.models import ReminderORM, AlertORM

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """
    Manages reminder scheduling and triggering.

    Handles:
    - Fixed-time reminders (at a specific HH:MM each day)
    - Relative-interval reminders (N days/hours before task due date)
    - Recurrence patterns (daily, weekly, etc.)
    - Snoozing and active/inactive status
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler()

    def run(self, reminder_id: str):
        """
        Main entry point: check if reminder should trigger and fire if needed.
        Called by APScheduler based on configured schedule.
        """
        db = SessionLocal()
        try:
            reminder = db.query(ReminderORM).filter(ReminderORM.reminder_id == reminder_id).first()
            if not reminder:
                logger.warning(f"Reminder {reminder_id} not found")
                return

            if not reminder.is_active:
                return

            if not self._should_trigger(reminder):
                return

            self._fire_reminder(reminder, db)
        except Exception as e:
            logger.error(f"Error running reminder {reminder_id}: {e}")
        finally:
            db.close()

    def _should_trigger(self, reminder: ReminderORM) -> bool:
        """
        Determine if reminder should trigger now.

        Checks:
        - Active status
        - Snooze until time
        - Last triggered time (to prevent duplicate triggers)
        - Recurrence pattern (if applicable)
        """
        now = datetime.utcnow()

        # Check snooze
        if reminder.snooze_until and now < reminder.snooze_until:
            return False

        # Check last triggered (avoid duplicates within 5 minutes)
        if reminder.last_triggered:
            if (now - reminder.last_triggered).total_seconds() < 300:
                return False

        # For relative_interval, check if trigger time has arrived
        if reminder.trigger_type == "relative_interval":
            return self._should_trigger_relative(reminder)

        # For fixed_time, the CronTrigger handles scheduling
        return True

    def _should_trigger_relative(self, reminder: ReminderORM) -> bool:
        """Check if a relative_interval reminder should trigger."""
        if not reminder.due_date:
            return False

        target_date = self._calculate_trigger_date(reminder)
        now_date = date.today()

        return now_date >= target_date

    def _fire_reminder(self, reminder: ReminderORM, db):
        """Create an alert from the reminder and update state."""
        now = datetime.utcnow()

        # Create alert
        severity = self._priority_to_severity(reminder.priority)
        alert = AlertORM(
            title=reminder.title,
            message=reminder.description or "",
            severity=severity,
            source="reminder",
            is_read=False,
            is_snoozed=False,
        )
        db.add(alert)

        # Update reminder state
        reminder.last_triggered = now

        db.commit()
        logger.info(f"Reminder {reminder.reminder_id} triggered: {reminder.title}")

    def _calculate_trigger_date(self, reminder: ReminderORM) -> date:
        """
        Calculate the date when a relative_interval reminder should trigger.

        trigger_value format: "-1d", "2h", "-3d", "+1w", etc.
        due_date is the reference date.
        """
        if not reminder.due_date or not reminder.trigger_value:
            return date.today()

        # Parse trigger_value (e.g., "-1d", "2h", "+1w")
        value_str = reminder.trigger_value.strip()
        if not value_str:
            return reminder.due_date

        sign = 1
        if value_str.startswith("-"):
            sign = -1
            value_str = value_str[1:]
        elif value_str.startswith("+"):
            value_str = value_str[1:]

        # Extract number and unit
        unit_char = value_str[-1].lower()
        try:
            num = int(value_str[:-1])
        except ValueError:
            return reminder.due_date

        # Calculate offset
        offset = num * sign
        due_dt = reminder.due_date

        if unit_char == "d":
            target = due_dt + timedelta(days=offset)
        elif unit_char == "h":
            target = due_dt + timedelta(hours=offset)
        elif unit_char == "w":
            target = due_dt + timedelta(weeks=offset)
        elif unit_char == "m":
            target = due_dt + relativedelta(months=offset)
        else:
            target = due_dt

        return target

    def _priority_to_severity(self, priority: str) -> str:
        """Map task priority to alert severity."""
        priority_map = {
            "low": "info",
            "medium": "info",
            "high": "warning",
            "critical": "critical",
        }
        return priority_map.get(priority, "info")

    def register_reminder(self, reminder: ReminderORM):
        """Register a reminder with the scheduler."""
        if not reminder.is_active:
            return

        try:
            if reminder.trigger_type == "fixed_time":
                self._register_fixed_time(reminder)
            elif reminder.trigger_type == "relative_interval":
                self._register_relative(reminder)
        except Exception as e:
            logger.error(f"Error registering reminder {reminder.reminder_id}: {e}")

    def _register_fixed_time(self, reminder: ReminderORM):
        """Register a fixed-time reminder (e.g., daily at 09:00)."""
        if not reminder.trigger_value:
            return

        try:
            # trigger_value format: "HH:MM"
            hour, minute = map(int, reminder.trigger_value.split(":"))
            job_id = f"reminder_{reminder.reminder_id}"

            # Remove existing job if present
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass

            # Add cron job for daily trigger at specified time
            self.scheduler.add_job(
                self.run,
                CronTrigger(hour=hour, minute=minute),
                args=(reminder.reminder_id,),
                id=job_id,
                replace_existing=True,
            )
            logger.info(f"Registered fixed_time reminder {reminder.reminder_id} at {hour:02d}:{minute:02d}")
        except Exception as e:
            logger.error(f"Error registering fixed_time reminder: {e}")

    def _register_relative(self, reminder: ReminderORM):
        """Register a relative-interval reminder (check daily)."""
        job_id = f"reminder_{reminder.reminder_id}"

        try:
            self.scheduler.remove_job(job_id)
        except:
            pass

        # Check once per day at 00:00 UTC
        self.scheduler.add_job(
            self.run,
            CronTrigger(hour=0, minute=0),
            args=(reminder.reminder_id,),
            id=job_id,
            replace_existing=True,
        )
        logger.info(f"Registered relative_interval reminder {reminder.reminder_id}")

    def unregister_reminder(self, reminder_id: str):
        """Remove a reminder from the scheduler."""
        job_id = f"reminder_{reminder_id}"
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Unregistered reminder {reminder_id}")
        except Exception as e:
            logger.warning(f"Could not unregister reminder {reminder_id}: {e}")

    def start(self):
        """Start the scheduler and load all active reminders."""
        if self.scheduler.running:
            return

        self.scheduler.start()
        logger.info("Reminder scheduler started")

        # Load all active reminders
        db = SessionLocal()
        try:
            reminders = db.query(ReminderORM).filter(ReminderORM.is_active == True).all()
            for reminder in reminders:
                self.register_reminder(reminder)
            logger.info(f"Loaded {len(reminders)} active reminders")
        finally:
            db.close()

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Reminder scheduler stopped")


def create_scheduler_job() -> ReminderScheduler:
    """Factory function to create and initialize a ReminderScheduler."""
    scheduler = ReminderScheduler()
    return scheduler
