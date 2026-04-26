import json
from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import get_db
from db.models import TaskORM

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskIn(BaseModel):
    title: str
    description: str = ""
    due_date: Optional[date] = None
    priority: str = "medium"
    status: str = "todo"
    project_id: Optional[str] = None
    assignee_id: Optional[str] = None
    tags: List[str] = []


class TaskOut(BaseModel):
    task_id: str
    title: str
    description: str
    due_date: Optional[date]
    reminder_date: Optional[date]
    priority: str
    status: str
    project_id: Optional[str]
    assignee_id: Optional[str]
    tags: List[str]
    postponed_count: int
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


def _to_out(t: TaskORM) -> dict:
    return {
        "task_id": t.task_id,
        "title": t.title,
        "description": t.description or "",
        "due_date": t.due_date,
        "reminder_date": t.reminder_date,
        "priority": t.priority,
        "status": t.status,
        "project_id": t.project_id,
        "assignee_id": t.assignee_id,
        "tags": json.loads(t.tags or "[]"),
        "postponed_count": t.postponed_count or 0,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
        "completed_at": t.completed_at,
    }


@router.get("", response_model=List[TaskOut])
def list_tasks(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(TaskORM)
    if status:
        q = q.filter(TaskORM.status == status)
    if priority:
        q = q.filter(TaskORM.priority == priority)
    if project_id:
        q = q.filter(TaskORM.project_id == project_id)
    tasks = q.order_by(TaskORM.created_at.desc()).all()
    return [_to_out(t) for t in tasks]


def _bust_dash():
    from web.deps import get_redis
    r = get_redis()
    r.delete("dashboard:operational")
    r.delete("dashboard:executive")


@router.post("", response_model=TaskOut, status_code=201)
def create_task(body: TaskIn, db: Session = Depends(get_db)):
    if not body.title.strip():
        raise HTTPException(400, "title must not be empty")
    t = TaskORM(
        title=body.title.strip(),
        description=body.description,
        due_date=body.due_date,
        priority=body.priority,
        status=body.status,
        project_id=body.project_id,
        assignee_id=body.assignee_id,
        tags=json.dumps(body.tags),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    _bust_dash()
    return _to_out(t)


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str, db: Session = Depends(get_db)):
    t = db.query(TaskORM).filter(TaskORM.task_id == task_id).first()
    if not t:
        raise HTTPException(404, "task not found")
    return _to_out(t)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: str, body: dict, db: Session = Depends(get_db)):
    t = db.query(TaskORM).filter(TaskORM.task_id == task_id).first()
    if not t:
        raise HTTPException(404, "task not found")
    allowed = {"title", "description", "due_date", "reminder_date", "priority", "status", "project_id", "assignee_id", "tags"}
    for k, v in body.items():
        if k not in allowed:
            continue
        if k == "tags":
            v = json.dumps(v)
        if k in ("due_date", "reminder_date") and isinstance(v, str):
            v = date.fromisoformat(v) if v else None
        setattr(t, k, v)
    t.updated_at = datetime.utcnow()
    if body.get("status") == "done" and not t.completed_at:
        t.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(t)
    _bust_dash()
    return _to_out(t)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str, db: Session = Depends(get_db)):
    t = db.query(TaskORM).filter(TaskORM.task_id == task_id).first()
    if not t:
        raise HTTPException(404, "task not found")
    db.delete(t)
    db.commit()
    _bust_dash()
