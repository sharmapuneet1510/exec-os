from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import get_db
from db.models import MilestoneORM

router = APIRouter(prefix="/api/milestones", tags=["milestones"])


class MilestoneIn(BaseModel):
    title: str
    description: str = ""
    project_id: Optional[str] = None
    release_id: Optional[str] = None
    due_date: Optional[date] = None
    status: str = "pending"


class MilestoneOut(BaseModel):
    milestone_id: str
    title: str
    description: str
    project_id: Optional[str]
    release_id: Optional[str]
    due_date: Optional[date]
    status: str
    is_overdue: bool
    created_at: datetime

    class Config:
        from_attributes = True


def _to_out(m: MilestoneORM) -> dict:
    today = date.today()
    return {
        "milestone_id": m.milestone_id,
        "title": m.title,
        "description": m.description or "",
        "project_id": m.project_id,
        "release_id": m.release_id,
        "due_date": m.due_date,
        "status": m.status,
        "is_overdue": bool(m.due_date and m.due_date < today and m.status == "pending"),
        "created_at": m.created_at,
    }


@router.get("", response_model=List[MilestoneOut])
def list_milestones(project_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(MilestoneORM)
    if project_id:
        q = q.filter(MilestoneORM.project_id == project_id)
    return [_to_out(m) for m in q.order_by(MilestoneORM.due_date).all()]


@router.post("", response_model=MilestoneOut, status_code=201)
def create_milestone(body: MilestoneIn, db: Session = Depends(get_db)):
    if not body.title.strip():
        raise HTTPException(400, "title must not be empty")
    m = MilestoneORM(
        title=body.title.strip(),
        description=body.description,
        project_id=body.project_id,
        release_id=body.release_id,
        due_date=body.due_date,
        status=body.status,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return _to_out(m)


@router.patch("/{milestone_id}", response_model=MilestoneOut)
def update_milestone(milestone_id: str, body: dict, db: Session = Depends(get_db)):
    m = db.query(MilestoneORM).filter(MilestoneORM.milestone_id == milestone_id).first()
    if not m:
        raise HTTPException(404, "milestone not found")
    for k, v in body.items():
        if k in ("title", "description", "status", "project_id", "release_id"):
            setattr(m, k, v)
        elif k == "due_date":
            m.due_date = date.fromisoformat(v) if v else None
    m.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(m)
    return _to_out(m)


@router.delete("/{milestone_id}", status_code=204)
def delete_milestone(milestone_id: str, db: Session = Depends(get_db)):
    m = db.query(MilestoneORM).filter(MilestoneORM.milestone_id == milestone_id).first()
    if not m:
        raise HTTPException(404, "milestone not found")
    db.delete(m)
    db.commit()
