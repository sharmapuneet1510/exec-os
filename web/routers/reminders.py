"""
Reminders CRUD API endpoints.

Provides full management of reminders including:
- CRUD operations
- Snoozing reminders
- Manual triggering for testing
- Listing with filters
"""
from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import get_db
from db.models import ReminderORM

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


class ReminderCreate(BaseModel):
    """Request body for creating a reminder."""
    title: str
    description: str = ""
    reminder_type: str = "independent"  # 'task' | 'independent'
    task_id: Optional[str] = None
    trigger_type: str  # 'fixed_time' | 'relative_interval'
    trigger_value: str  # "HH:MM" or "-1d"
    trigger_date: Optional[date] = None
    due_date: Optional[date] = None
    recurrence_pattern: Optional[dict] = None
    is_active: bool = True
    include_in_sod: bool = True
    include_in_eod: bool = True
    priority: str = "medium"


class ReminderUpdate(BaseModel):
    """Request body for updating a reminder."""
    title: Optional[str] = None
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_value: Optional[str] = None
    trigger_date: Optional[date] = None
    due_date: Optional[date] = None
    recurrence_pattern: Optional[dict] = None
    is_active: Optional[bool] = None
    include_in_sod: Optional[bool] = None
    include_in_eod: Optional[bool] = None
    priority: Optional[str] = None


class ReminderResponse(BaseModel):
    """Response model for reminders."""
    reminder_id: str
    title: str
    description: str
    reminder_type: str
    task_id: Optional[str]
    trigger_type: str
    trigger_value: str
    trigger_date: Optional[date]
    due_date: Optional[date]
    recurrence_pattern: dict
    is_active: bool
    last_triggered: Optional[datetime]
    snooze_until: Optional[datetime]
    include_in_sod: bool
    include_in_eod: bool
    priority: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


def _to_response(reminder: ReminderORM) -> dict:
    """Convert ORM object to response dict."""
    import json
    return {
        "reminder_id": reminder.reminder_id,
        "title": reminder.title,
        "description": reminder.description or "",
        "reminder_type": reminder.reminder_type,
        "task_id": reminder.task_id,
        "trigger_type": reminder.trigger_type,
        "trigger_value": reminder.trigger_value,
        "trigger_date": reminder.trigger_date,
        "due_date": reminder.due_date,
        "recurrence_pattern": json.loads(reminder.recurrence_pattern or "{}"),
        "is_active": reminder.is_active,
        "last_triggered": reminder.last_triggered,
        "snooze_until": reminder.snooze_until,
        "include_in_sod": reminder.include_in_sod,
        "include_in_eod": reminder.include_in_eod,
        "priority": reminder.priority,
        "created_at": reminder.created_at,
        "updated_at": reminder.updated_at,
    }


@router.get("", response_model=List[ReminderResponse])
def list_reminders(
    task_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """List all reminders with optional filters."""
    q = db.query(ReminderORM)

    if task_id is not None:
        q = q.filter(ReminderORM.task_id == task_id)

    if is_active is not None:
        q = q.filter(ReminderORM.is_active == is_active)

    reminders = q.order_by(ReminderORM.created_at.desc()).all()
    return [_to_response(r) for r in reminders]


@router.post("", response_model=ReminderResponse, status_code=201)
def create_reminder(body: ReminderCreate, db: Session = Depends(get_db)):
    """Create a new reminder."""
    if not body.title.strip():
        raise HTTPException(400, "title must not be empty")

    if body.trigger_type not in ("fixed_time", "relative_interval"):
        raise HTTPException(400, "trigger_type must be 'fixed_time' or 'relative_interval'")

    if body.reminder_type not in ("task", "independent"):
        raise HTTPException(400, "reminder_type must be 'task' or 'independent'")

    # Validate trigger_value format
    if body.trigger_type == "fixed_time":
        if not _validate_time_format(body.trigger_value):
            raise HTTPException(400, "trigger_value must be 'HH:MM' for fixed_time reminders")
    elif body.trigger_type == "relative_interval":
        if not _validate_interval_format(body.trigger_value):
            raise HTTPException(400, "trigger_value must be '-Nd', 'Nh', '+Nw', or 'Nm' for relative_interval reminders")

    import json
    reminder = ReminderORM(
        title=body.title.strip(),
        description=body.description,
        reminder_type=body.reminder_type,
        task_id=body.task_id,
        trigger_type=body.trigger_type,
        trigger_value=body.trigger_value,
        trigger_date=body.trigger_date,
        due_date=body.due_date,
        recurrence_pattern=json.dumps(body.recurrence_pattern or {}),
        is_active=body.is_active,
        include_in_sod=body.include_in_sod,
        include_in_eod=body.include_in_eod,
        priority=body.priority,
    )

    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    # Register with scheduler
    _register_reminder_with_scheduler(reminder)

    return _to_response(reminder)


@router.get("/{reminder_id}", response_model=ReminderResponse)
def get_reminder(reminder_id: str, db: Session = Depends(get_db)):
    """Get a specific reminder by ID."""
    reminder = db.query(ReminderORM).filter(ReminderORM.reminder_id == reminder_id).first()
    if not reminder:
        raise HTTPException(404, "reminder not found")
    return _to_response(reminder)


@router.patch("/{reminder_id}", response_model=ReminderResponse)
def update_reminder(reminder_id: str, body: ReminderUpdate, db: Session = Depends(get_db)):
    """Update a reminder."""
    reminder = db.query(ReminderORM).filter(ReminderORM.reminder_id == reminder_id).first()
    if not reminder:
        raise HTTPException(404, "reminder not found")

    # Validate trigger_type and trigger_value if updating those
    if body.trigger_type is not None:
        if body.trigger_type not in ("fixed_time", "relative_interval"):
            raise HTTPException(400, "trigger_type must be 'fixed_time' or 'relative_interval'")
        reminder.trigger_type = body.trigger_type

    if body.trigger_value is not None:
        if reminder.trigger_type == "fixed_time":
            if not _validate_time_format(body.trigger_value):
                raise HTTPException(400, "trigger_value must be 'HH:MM' for fixed_time reminders")
        elif reminder.trigger_type == "relative_interval":
            if not _validate_interval_format(body.trigger_value):
                raise HTTPException(400, "trigger_value must be '-Nd', 'Nh', '+Nw', or 'Nm' for relative_interval reminders")
        reminder.trigger_value = body.trigger_value

    # Update fields
    if body.title is not None:
        if not body.title.strip():
            raise HTTPException(400, "title must not be empty")
        reminder.title = body.title.strip()

    if body.description is not None:
        reminder.description = body.description

    if body.trigger_date is not None:
        reminder.trigger_date = body.trigger_date

    if body.due_date is not None:
        reminder.due_date = body.due_date

    if body.recurrence_pattern is not None:
        import json
        reminder.recurrence_pattern = json.dumps(body.recurrence_pattern)

    if body.is_active is not None:
        reminder.is_active = body.is_active
        # Re-register with scheduler when activating
        if body.is_active:
            _register_reminder_with_scheduler(reminder)
        else:
            _unregister_reminder_from_scheduler(reminder.reminder_id)

    if body.include_in_sod is not None:
        reminder.include_in_sod = body.include_in_sod

    if body.include_in_eod is not None:
        reminder.include_in_eod = body.include_in_eod

    if body.priority is not None:
        reminder.priority = body.priority

    db.commit()
    db.refresh(reminder)

    # Re-register with scheduler if trigger settings changed
    if body.trigger_type is not None or body.trigger_value is not None:
        _register_reminder_with_scheduler(reminder)

    return _to_response(reminder)


@router.delete("/{reminder_id}", status_code=204)
def delete_reminder(reminder_id: str, db: Session = Depends(get_db)):
    """Delete a reminder."""
    reminder = db.query(ReminderORM).filter(ReminderORM.reminder_id == reminder_id).first()
    if not reminder:
        raise HTTPException(404, "reminder not found")

    db.delete(reminder)
    db.commit()

    # Unregister from scheduler
    _unregister_reminder_from_scheduler(reminder_id)


@router.post("/{reminder_id}/snooze")
def snooze_reminder(
    reminder_id: str,
    minutes: int = 15,
    db: Session = Depends(get_db),
):
    """Snooze a reminder for a specified number of minutes."""
    if minutes < 1:
        raise HTTPException(400, "minutes must be at least 1")

    reminder = db.query(ReminderORM).filter(ReminderORM.reminder_id == reminder_id).first()
    if not reminder:
        raise HTTPException(404, "reminder not found")

    from datetime import timedelta
    reminder.snooze_until = datetime.utcnow() + timedelta(minutes=minutes)
    db.commit()
    db.refresh(reminder)

    return _to_response(reminder)


@router.post("/{reminder_id}/trigger")
def trigger_reminder(reminder_id: str, db: Session = Depends(get_db)):
    """
    Manually trigger a reminder for testing purposes.
    Creates an alert from the reminder.
    """
    reminder = db.query(ReminderORM).filter(ReminderORM.reminder_id == reminder_id).first()
    if not reminder:
        raise HTTPException(404, "reminder not found")

    from services.reminder_scheduler import ReminderScheduler
    scheduler = ReminderScheduler()
    scheduler._fire_reminder(reminder, db)

    db.refresh(reminder)
    return {
        "ok": True,
        "message": f"Reminder '{reminder.title}' triggered successfully",
        "reminder": _to_response(reminder),
    }


def _validate_time_format(value: str) -> bool:
    """Validate time format 'HH:MM'."""
    try:
        parts = value.split(":")
        if len(parts) != 2:
            return False
        hour = int(parts[0])
        minute = int(parts[1])
        return 0 <= hour < 24 and 0 <= minute < 60
    except (ValueError, AttributeError):
        return False


def _validate_interval_format(value: str) -> bool:
    """Validate interval format like '-1d', '2h', '+1w', '1m'."""
    try:
        if not value or len(value) < 2:
            return False

        # Extract sign
        idx = 0
        if value[0] in ("-", "+"):
            idx = 1

        # Extract number and unit
        if idx >= len(value):
            return False

        unit_char = value[-1].lower()
        if unit_char not in ("d", "h", "w", "m"):
            return False

        num_str = value[idx:-1]
        num = int(num_str)
        return num > 0
    except (ValueError, IndexError):
        return False


def _register_reminder_with_scheduler(reminder: ReminderORM):
    """Register a reminder with the background scheduler."""
    try:
        from web.app import _reminder_scheduler
        if _reminder_scheduler:
            _reminder_scheduler.register_reminder(reminder)
    except Exception as e:
        import logging
        logging.warning(f"Could not register reminder with scheduler: {e}")


def _unregister_reminder_from_scheduler(reminder_id: str):
    """Unregister a reminder from the background scheduler."""
    try:
        from web.app import _reminder_scheduler
        if _reminder_scheduler:
            _reminder_scheduler.unregister_reminder(reminder_id)
    except Exception as e:
        import logging
        logging.warning(f"Could not unregister reminder from scheduler: {e}")
