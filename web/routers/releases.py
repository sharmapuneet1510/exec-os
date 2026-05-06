from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from db.base import get_db
from db.models import ReleaseORM, ProjectORM

router = APIRouter(prefix="/api/releases", tags=["releases"])


class ReleaseIn(BaseModel):
    name: str
    version: str = ""
    project_id: Optional[str] = None
    application_id: Optional[str] = None
    due_date: Optional[date] = None
    status: str = "planned"
    description: str = ""


class ReleaseOut(BaseModel):
    release_id: str
    name: str
    version: str
    project_id: Optional[str]
    project_name: Optional[str]
    application_id: Optional[str]
    due_date: Optional[date]
    status: str
    description: str
    days_until_due: Optional[int]
    is_overdue: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


def _bust_dash():
    from web.deps import get_redis
    r = get_redis()
    r.delete("dashboard:operational")
    r.delete("dashboard:executive")


def _to_out(rel: ReleaseORM, db: Session) -> dict:
    today = date.today()
    days_until_due = None
    is_overdue = False
    if rel.due_date:
        days_until_due = (rel.due_date - today).days
        is_overdue = rel.due_date < today and rel.status not in ("completed", "cancelled")

    # Use eager-loaded relationship if available, fall back to query
    project_name = None
    if rel.project_id:
        if hasattr(rel, 'project') and rel.project:
            project_name = rel.project.name
        else:
            proj = db.query(ProjectORM).filter(ProjectORM.project_id == rel.project_id).first()
            if proj:
                project_name = proj.name

    return {
        "release_id": rel.release_id,
        "name": rel.name,
        "version": rel.version or "",
        "project_id": rel.project_id,
        "project_name": project_name,
        "application_id": rel.application_id,
        "due_date": rel.due_date,
        "status": rel.status,
        "description": rel.description or "",
        "days_until_due": days_until_due,
        "is_overdue": is_overdue,
        "created_at": rel.created_at,
        "updated_at": rel.updated_at,
    }


@router.get("", response_model=List[ReleaseOut])
def list_releases(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(ReleaseORM)
    if project_id:
        q = q.filter(ReleaseORM.project_id == project_id)
    if status:
        q = q.filter(ReleaseORM.status == status)
    releases = q.options(joinedload(ReleaseORM.project)).order_by(ReleaseORM.due_date.asc(), ReleaseORM.created_at.desc()).all()
    return [_to_out(rel, db) for rel in releases]
