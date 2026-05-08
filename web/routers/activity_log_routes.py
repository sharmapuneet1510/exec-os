"""Activity log — tracks all HTTP requests/responses and entity changes."""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db.base import get_db
from db.models import ActivityLogORM, EntityActivityLogORM

router = APIRouter(prefix="/api/activity", tags=["activity"])


class ActivityLogIn(BaseModel):
    method: str
    endpoint: str
    status_code: int
    request_headers: dict
    request_body: Optional[str] = None
    response_headers: dict
    response_body: Optional[str] = None
    duration_ms: float
    error: Optional[str] = None


class ActivityLogOut(BaseModel):
    log_id: str
    method: str
    endpoint: str
    status_code: int
    request_headers: dict
    request_body: Optional[str] = None
    response_headers: dict
    response_body: Optional[str] = None
    duration_ms: float
    error: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("", status_code=201)
def log_activity(body: ActivityLogIn, db: Session = Depends(get_db)):
    """Log a request/response."""
    log = ActivityLogORM(
        method=body.method,
        endpoint=body.endpoint,
        status_code=body.status_code,
        request_headers=body.request_headers,
        request_body=body.request_body,
        response_headers=body.response_headers,
        response_body=body.response_body,
        duration_ms=body.duration_ms,
        error=body.error,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return ActivityLogOut.model_validate(log)


@router.get("")
def list_activities(
    limit: int = 100,
    offset: int = 0,
    method: Optional[str] = None,
    endpoint: Optional[str] = None,
    status_code: Optional[int] = None,
    db: Session = Depends(get_db),
) -> List[ActivityLogOut]:
    """List activity logs with optional filters."""
    query = db.query(ActivityLogORM)

    if method:
        query = query.filter(ActivityLogORM.method == method)
    if endpoint:
        query = query.filter(ActivityLogORM.endpoint.contains(endpoint))
    if status_code:
        query = query.filter(ActivityLogORM.status_code == status_code)

    logs = query.order_by(desc(ActivityLogORM.created_at)).offset(offset).limit(limit).all()
    return [ActivityLogOut.model_validate(log) for log in logs]


@router.get("/{log_id}")
def get_activity(log_id: str, db: Session = Depends(get_db)) -> ActivityLogOut:
    """Get a specific activity log entry."""
    log = db.query(ActivityLogORM).filter(ActivityLogORM.log_id == log_id).first()
    if not log:
        from fastapi import HTTPException
        raise HTTPException(404, "Activity log not found")
    return ActivityLogOut.model_validate(log)


@router.delete("")
def clear_activities(db: Session = Depends(get_db)):
    """Clear all activity logs."""
    db.query(ActivityLogORM).delete()
    db.commit()
    return {"ok": True, "message": "Activity logs cleared"}


class EntityActivityOut(BaseModel):
    activity_id: str
    entity_type: str
    entity_id: str
    action: str
    description: str
    details: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/entity", response_model=List[EntityActivityOut])
def get_entity_activities(
    limit: int = 50,
    offset: int = 0,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get entity activity logs (create, update, delete operations)."""
    query = db.query(EntityActivityLogORM)

    if entity_type:
        query = query.filter(EntityActivityLogORM.entity_type == entity_type)
    if entity_id:
        query = query.filter(EntityActivityLogORM.entity_id == entity_id)
    if action:
        query = query.filter(EntityActivityLogORM.action == action)

    logs = query.order_by(desc(EntityActivityLogORM.created_at)).offset(offset).limit(limit).all()
    return [EntityActivityOut.model_validate(log) for log in logs]
