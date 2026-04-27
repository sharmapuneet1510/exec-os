from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import get_db
from db.models import AlertORM

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class AlertIn(BaseModel):
    title: str
    message: str = ""
    severity: str = "info"
    source: str = "system"


class AlertOut(BaseModel):
    alert_id: str
    title: str
    message: str
    severity: str
    source: str
    is_read: bool
    is_snoozed: bool
    created_at: datetime

    class Config:
        from_attributes = True


def _to_out(a: AlertORM) -> dict:
    return {
        "alert_id": a.alert_id,
        "title": a.title,
        "message": a.message or "",
        "severity": a.severity,
        "source": a.source,
        "is_read": a.is_read,
        "is_snoozed": a.is_snoozed,
        "created_at": a.created_at,
    }


@router.get("", response_model=List[AlertOut])
def list_alerts(unread_only: bool = False, db: Session = Depends(get_db)):
    q = db.query(AlertORM)
    if unread_only:
        q = q.filter(AlertORM.is_read == False)  # noqa: E712
    return [_to_out(a) for a in q.order_by(AlertORM.created_at.desc()).limit(100).all()]


@router.post("", response_model=AlertOut, status_code=201)
def create_alert(body: AlertIn, db: Session = Depends(get_db)):
    a = AlertORM(
        title=body.title,
        message=body.message,
        severity=body.severity,
        source=body.source,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return _to_out(a)


@router.patch("/{alert_id}/read", response_model=AlertOut)
def mark_read(alert_id: str, db: Session = Depends(get_db)):
    a = db.query(AlertORM).filter(AlertORM.alert_id == alert_id).first()
    if not a:
        raise HTTPException(404, "alert not found")
    a.is_read = True
    db.commit()
    db.refresh(a)
    return _to_out(a)


@router.delete("/{alert_id}", status_code=204)
def delete_alert(alert_id: str, db: Session = Depends(get_db)):
    a = db.query(AlertORM).filter(AlertORM.alert_id == alert_id).first()
    if not a:
        raise HTTPException(404, "alert not found")
    db.delete(a)
    db.commit()


@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db)):
    count = db.query(AlertORM).filter(AlertORM.is_read == False).count()  # noqa: E712
    return {"count": count}


@router.get("/new-since/{iso_ts}")
def new_since(iso_ts: str, db: Session = Depends(get_db)):
    """Return unread alerts created after the given ISO timestamp (for polling)."""
    try:
        since = datetime.fromisoformat(iso_ts.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        raise HTTPException(400, "invalid timestamp — use ISO 8601")
    rows = db.query(AlertORM).filter(
        AlertORM.is_read == False,      # noqa: E712
        AlertORM.created_at > since,
    ).order_by(AlertORM.created_at.asc()).all()
    return [_to_out(a) for a in rows]


@router.post("/run-engine", status_code=202)
def trigger_engine():
    """Manually trigger the alert engine (useful for testing)."""
    import threading
    from web.alert_engine import run
    threading.Thread(target=run, daemon=True).start()
    return {"ok": True, "message": "Alert engine triggered"}
