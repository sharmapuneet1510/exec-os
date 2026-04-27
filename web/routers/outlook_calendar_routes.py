"""
Local Outlook calendar integration (Windows).
Reads events from Outlook using pywin32 (requires: pip install pywin32).
"""

from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/outlook", tags=["outlook"])


class OutlookEvent(BaseModel):
    """Outlook calendar event."""
    id: str
    title: str
    start: str  # ISO 8601
    end: str    # ISO 8601
    description: Optional[str] = None
    organizer: Optional[str] = None
    is_all_day: bool = False


def _get_outlook() -> object:
    """Get Outlook COM object. Raises HTTPException if not available."""
    try:
        import win32com.client
    except ImportError:
        raise HTTPException(
            500,
            "pywin32 not installed — run: pip install pywin32",
        )

    try:
        outlook = win32com.client.GetObject(Class="Outlook.Application")
        return outlook
    except Exception as e:
        raise HTTPException(
            500,
            f"Cannot connect to Outlook. Is it running? Error: {str(e)}",
        )


def _get_calendar() -> object:
    """Get Outlook Calendar folder."""
    outlook = _get_outlook()
    try:
        namespace = outlook.GetNamespace("MAPI")
        calendar = namespace.GetDefaultFolder(9)  # 9 = olFolderCalendar
        return calendar
    except Exception as e:
        raise HTTPException(500, f"Cannot access calendar: {str(e)}")


def _event_to_dict(event) -> Optional[OutlookEvent]:
    """Convert Outlook event COM object to dict."""
    try:
        start = event.Start
        end = event.End
        return OutlookEvent(
            id=event.EntryID,
            title=event.Subject or "(No title)",
            start=start.isoformat() if start else "",
            end=end.isoformat() if end else "",
            description=event.Body or None,
            organizer=event.Organizer.Name if event.Organizer else None,
            is_all_day=bool(event.AllDayEvent),
        )
    except Exception:
        return None


@router.get("/test")
def test_connection():
    """Test connection to local Outlook."""
    try:
        _get_outlook()
        return {"ok": True, "message": "Connected to Outlook"}
    except HTTPException as e:
        raise e


@router.get("/events/today")
def get_today_events() -> List[OutlookEvent]:
    """Get all calendar events for today."""
    calendar = _get_calendar()
    today = datetime.now().date()
    start = datetime.combine(today, datetime.min.time())
    end = datetime.combine(today, datetime.max.time())

    try:
        items = calendar.Items
        items.Sort("[Start]")
        items.IncludeRecurrences = True

        events = []
        for item in items:
            if hasattr(item, "Start") and item.Start:
                if start <= item.Start <= end:
                    event = _event_to_dict(item)
                    if event:
                        events.append(event)
        return events
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch events: {str(e)}")


@router.get("/events/upcoming")
def get_upcoming_events(days: int = Query(7, ge=1, le=365)) -> List[OutlookEvent]:
    """Get calendar events for the next N days."""
    calendar = _get_calendar()
    today = datetime.now().date()
    start = datetime.combine(today, datetime.min.time())
    end = datetime.combine(today + timedelta(days=days), datetime.max.time())

    try:
        items = calendar.Items
        items.Sort("[Start]")
        items.IncludeRecurrences = True

        events = []
        for item in items:
            if hasattr(item, "Start") and item.Start:
                if start <= item.Start <= end:
                    event = _event_to_dict(item)
                    if event:
                        events.append(event)
        return events
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch events: {str(e)}")


@router.post("/sync-to-tasks")
def sync_calendar_to_tasks(days: int = Query(7, ge=1, le=365)):
    """Sync Outlook calendar events to tasks (stub)."""
    return {
        "ok": True,
        "message": f"Synced events from next {days} days to tasks",
        "synced_count": 0,
    }
