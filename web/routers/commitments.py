from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import get_db
from db.models import CommitmentORM

router = APIRouter(prefix="/api/commitments", tags=["commitments"])


class CommitmentIn(BaseModel):
    title: str
    description: str = ""
    due_date: Optional[date] = None
    status: str = "pending"
    task_id: Optional[str] = None
    project_id: Optional[str] = None


class CommitmentOut(BaseModel):
    commitment_id: str
    title: str
    description: str
    due_date: Optional[date]
    status: str
    task_id: Optional[str]
    project_id: Optional[str]
    is_overdue: bool
    created_at: datetime

    class Config:
        from_attributes = True


def _to_out(c: CommitmentORM) -> dict:
    today = date.today()
    return {
        "commitment_id": c.commitment_id,
        "title": c.title,
        "description": c.description or "",
        "due_date": c.due_date,
        "status": c.status,
        "task_id": c.task_id,
        "project_id": c.project_id,
        "is_overdue": bool(c.due_date and c.due_date < today and c.status == "pending"),
        "created_at": c.created_at,
    }


@router.get("", response_model=List[CommitmentOut])
def list_commitments(db: Session = Depends(get_db)):
    rows = db.query(CommitmentORM).order_by(CommitmentORM.due_date).all()
    return [_to_out(c) for c in rows]


@router.post("", response_model=CommitmentOut, status_code=201)
def create_commitment(body: CommitmentIn, db: Session = Depends(get_db)):
    if not body.title.strip():
        raise HTTPException(400, "title must not be empty")
    c = CommitmentORM(
        title=body.title.strip(),
        description=body.description,
        due_date=body.due_date,
        status=body.status,
        task_id=body.task_id,
        project_id=body.project_id,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.patch("/{commitment_id}", response_model=CommitmentOut)
def update_commitment(commitment_id: str, body: dict, db: Session = Depends(get_db)):
    c = db.query(CommitmentORM).filter(CommitmentORM.commitment_id == commitment_id).first()
    if not c:
        raise HTTPException(404, "commitment not found")
    for k, v in body.items():
        if k in ("title", "description", "status", "task_id", "project_id"):
            setattr(c, k, v)
        elif k == "due_date":
            c.due_date = date.fromisoformat(v) if v else None
    c.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.delete("/{commitment_id}", status_code=204)
def delete_commitment(commitment_id: str, db: Session = Depends(get_db)):
    c = db.query(CommitmentORM).filter(CommitmentORM.commitment_id == commitment_id).first()
    if not c:
        raise HTTPException(404, "commitment not found")
    db.delete(c)
    db.commit()
