"""Day Planner — Outlook ICS calendar, auto-schedule, and daily plan CRUD."""

import json
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import SessionLocal
from db.models import OutlookConfigORM, DayPlanItemORM, TaskORM

log = logging.getLogger("execos.planner")
router = APIRouter(prefix="/api/planner", tags=["planner"])


def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_cfg(db: Session) -> OutlookConfigORM:
    cfg = db.query(OutlookConfigORM).filter(OutlookConfigORM.id == 1).first()
    if not cfg:
        cfg = OutlookConfigORM(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


# ── ICS helpers ───────────────────────────────────────────────────────────────

def _fetch_ics_events(cfg: OutlookConfigORM, target_date: date) -> list:
    if not cfg.enabled or not cfg.ics_url:
        return []
    try:
        import requests as req
        resp = req.get(cfg.ics_url, timeout=20, headers={"User-Agent": "ExecOS/1.0"})
        if not resp.ok:
            log.warning("ICS fetch failed: %s", resp.status_code)
            return []
        return _parse_ics(resp.text, target_date)
    except Exception as e:
        log.error("ICS fetch error: %s", e)
        return []


def _parse_ics(ics_text: str, target_date: date) -> list:
    try:
        from icalendar import Calendar
    except ImportError:
        log.error("icalendar not installed")
        return []

    events = []
    try:
        cal = Calendar.from_ical(ics_text)
    except Exception as e:
        log.error("ICS parse error: %s", e)
        return []

    for comp in cal.walk():
        if comp.name != "VEVENT":
            continue
        dtstart = comp.get("DTSTART")
        dtend   = comp.get("DTEND")
        if not dtstart:
            continue

        start = dtstart.dt
        end   = dtend.dt if dtend else None

        # All-day event (date, not datetime)
        if not isinstance(start, datetime):
            if start == target_date:
                events.append({
                    "uid":        str(comp.get("UID", "")),
                    "title":      str(comp.get("SUMMARY", "Meeting")),
                    "time_start": "00:00",
                    "time_end":   "23:59",
                    "all_day":    True,
                    "location":   str(comp.get("LOCATION", "")),
                })
            continue

        # Normalise to naive local time
        if start.tzinfo:
            start = start.astimezone().replace(tzinfo=None)
        if end and hasattr(end, "tzinfo") and end.tzinfo:
            end = end.astimezone().replace(tzinfo=None)

        if start.date() == target_date:
            end = end or (start + timedelta(hours=1))
            events.append({
                "uid":        str(comp.get("UID", "")),
                "title":      str(comp.get("SUMMARY", "Meeting")),
                "time_start": start.strftime("%H:%M"),
                "time_end":   end.strftime("%H:%M"),
                "all_day":    False,
                "location":   str(comp.get("LOCATION", "")),
            })

    return sorted(events, key=lambda x: x["time_start"])


# ── Planner helpers ───────────────────────────────────────────────────────────

def _t2m(t: str) -> int:
    h, m = map(int, t.split(":"))
    return h * 60 + m


def _m2t(mins: int) -> str:
    return f"{mins // 60:02d}:{mins % 60:02d}"


_DURATION = {"critical": 120, "high": 90, "medium": 60, "low": 30}
_PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _auto_generate(db: Session, plan_date: date, calendar_events: list,
                   working_start: str, working_end: str) -> list:
    items = []

    # 1. Calendar meetings
    for ev in calendar_events:
        if not ev.get("all_day"):
            items.append(dict(
                plan_date=plan_date,
                time_start=ev["time_start"],
                time_end=ev["time_end"],
                title=ev["title"],
                item_type="meeting",
                notes=ev.get("location", ""),
                source="calendar",
                calendar_uid=ev.get("uid"),
                priority="medium",
                task_id=None,
                completed=False,
            ))

    # 2. Work tasks: overdue high/critical + anything due today
    today_str = plan_date.isoformat()
    tasks = db.query(TaskORM).filter(
        TaskORM.status.in_(["todo", "in_progress"])
    ).all()

    work = sorted(
        [t for t in tasks if
         (t.due_date and t.due_date.isoformat() <= today_str) or
         t.priority in ("critical", "high")],
        key=lambda t: (
            _PRIORITY_ORDER.get(t.priority, 2),
            t.due_date or date(2099, 12, 31),
        )
    )

    # 3. Free-slot allocation
    ws, we = _t2m(working_start), _t2m(working_end)
    occupied = sorted(
        [(_t2m(i["time_start"]), _t2m(i["time_end"])) for i in items if i["item_type"] == "meeting"],
        key=lambda x: x[0]
    )

    free = []
    cursor = ws
    for s, e in occupied:
        if cursor + 15 < s:          # at least 15 min gap to be useful
            free.append((cursor, s))
        cursor = max(cursor, e)
    if cursor + 15 < we:
        free.append((cursor, we))

    fi, fc = 0, free[0][0] if free else None
    for t in work:
        if fi >= len(free) or fc is None:
            break
        dur = _DURATION.get(t.priority, 60)
        # Skip to next slot if no room
        while fi < len(free) and fc + dur > free[fi][1]:
            fi += 1
            if fi < len(free):
                fc = free[fi][0] + 5
        if fi >= len(free):
            break
        items.append(dict(
            plan_date=plan_date,
            time_start=_m2t(fc),
            time_end=_m2t(fc + dur),
            title=t.title,
            item_type="task",
            notes=t.description or "",
            source="auto",
            calendar_uid=None,
            priority=t.priority,
            task_id=t.task_id,
            completed=False,
        ))
        fc += dur + 10

    return sorted(items, key=lambda x: x["time_start"])


def _plan_to_dict(item: DayPlanItemORM) -> dict:
    return {
        "item_id":     item.item_id,
        "plan_date":   item.plan_date.isoformat() if item.plan_date else None,
        "time_start":  item.time_start,
        "time_end":    item.time_end,
        "title":       item.title,
        "item_type":   item.item_type,
        "task_id":     item.task_id,
        "notes":       item.notes or "",
        "completed":   item.completed,
        "source":      item.source,
        "priority":    item.priority,
        "calendar_uid": item.calendar_uid,
    }


# ── Schemas ───────────────────────────────────────────────────────────────────

class OutlookConfigIn(BaseModel):
    ics_url:       Optional[str] = ""
    enabled:       Optional[bool] = False
    working_start: Optional[str] = "09:00"
    working_end:   Optional[str] = "18:00"


class PlanItemIn(BaseModel):
    plan_date:  str
    time_start: str
    time_end:   str
    title:      str
    item_type:  str = "task"
    task_id:    Optional[str] = None
    notes:      str = ""
    priority:   str = "medium"


class PlanItemPatch(BaseModel):
    completed:  Optional[bool] = None
    title:      Optional[str] = None
    time_start: Optional[str] = None
    time_end:   Optional[str] = None
    notes:      Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/config")
def get_config(db: Session = Depends(_db)):
    cfg = _get_cfg(db)
    return {
        "ics_url":       "••••" if cfg.ics_url else "",
        "ics_configured": bool(cfg.ics_url),
        "enabled":       cfg.enabled,
        "working_start": cfg.working_start or "09:00",
        "working_end":   cfg.working_end   or "18:00",
    }


@router.post("/config")
def save_config(body: OutlookConfigIn, db: Session = Depends(_db)):
    cfg = _get_cfg(db)
    if body.ics_url is not None and body.ics_url != "••••":
        cfg.ics_url = body.ics_url
    if body.enabled is not None:
        cfg.enabled = body.enabled
    if body.working_start:
        cfg.working_start = body.working_start
    if body.working_end:
        cfg.working_end = body.working_end
    db.commit()
    return {"ok": True}


@router.get("/calendar")
def get_calendar(target_date: Optional[str] = None, db: Session = Depends(_db)):
    """Return calendar events from Outlook ICS for the given date (default today)."""
    cfg = _get_cfg(db)
    d = date.fromisoformat(target_date) if target_date else date.today()
    events = _fetch_ics_events(cfg, d)
    return {"date": d.isoformat(), "events": events, "calendar_enabled": cfg.enabled}


@router.get("/plan")
def get_plan(target_date: Optional[str] = None, db: Session = Depends(_db)):
    d = date.fromisoformat(target_date) if target_date else date.today()
    items = db.query(DayPlanItemORM).filter(
        DayPlanItemORM.plan_date == d
    ).order_by(DayPlanItemORM.time_start).all()
    cfg = _get_cfg(db)
    return {
        "date": d.isoformat(),
        "items": [_plan_to_dict(i) for i in items],
        "working_start": cfg.working_start,
        "working_end":   cfg.working_end,
        "calendar_enabled": cfg.enabled,
    }


@router.post("/generate")
def generate_plan(target_date: Optional[str] = None, db: Session = Depends(_db)):
    """Auto-generate a day plan. Clears existing auto items first, keeps manual ones."""
    cfg = _get_cfg(db)
    d = date.fromisoformat(target_date) if target_date else date.today()

    # Clear old auto/calendar items
    db.query(DayPlanItemORM).filter(
        DayPlanItemORM.plan_date == d,
        DayPlanItemORM.source.in_(["auto", "calendar"]),
    ).delete(synchronize_session=False)

    calendar_events = _fetch_ics_events(cfg, d)
    generated = _auto_generate(db, d, calendar_events, cfg.working_start or "09:00", cfg.working_end or "18:00")

    for item_dict in generated:
        db.add(DayPlanItemORM(**item_dict))
    db.commit()

    items = db.query(DayPlanItemORM).filter(
        DayPlanItemORM.plan_date == d
    ).order_by(DayPlanItemORM.time_start).all()
    return {
        "date": d.isoformat(),
        "items": [_plan_to_dict(i) for i in items],
        "generated": len(generated),
        "working_start": cfg.working_start,
        "working_end":   cfg.working_end,
    }


@router.post("/items")
def add_item(body: PlanItemIn, db: Session = Depends(_db)):
    item = DayPlanItemORM(
        plan_date=date.fromisoformat(body.plan_date),
        time_start=body.time_start,
        time_end=body.time_end,
        title=body.title,
        item_type=body.item_type,
        task_id=body.task_id,
        notes=body.notes,
        priority=body.priority,
        source="manual",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _plan_to_dict(item)


@router.patch("/items/{item_id}")
def update_item(item_id: str, body: PlanItemPatch, db: Session = Depends(_db)):
    item = db.query(DayPlanItemORM).filter(DayPlanItemORM.item_id == item_id).first()
    if not item:
        raise HTTPException(404, "item not found")
    if body.completed is not None:
        item.completed = body.completed
    if body.title is not None:
        item.title = body.title
    if body.time_start is not None:
        item.time_start = body.time_start
    if body.time_end is not None:
        item.time_end = body.time_end
    if body.notes is not None:
        item.notes = body.notes
    db.commit()
    return _plan_to_dict(item)


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: str, db: Session = Depends(_db)):
    item = db.query(DayPlanItemORM).filter(DayPlanItemORM.item_id == item_id).first()
    if not item:
        raise HTTPException(404, "item not found")
    db.delete(item)
    db.commit()


@router.delete("/plan", status_code=204)
def clear_plan(target_date: Optional[str] = None, db: Session = Depends(_db)):
    d = date.fromisoformat(target_date) if target_date else date.today()
    db.query(DayPlanItemORM).filter(DayPlanItemORM.plan_date == d).delete()
    db.commit()
