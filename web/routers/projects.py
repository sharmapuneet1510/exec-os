import json
from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import get_db
from db.models import ProjectORM, TaskORM
from db.activity_helper import log_activity


def _bust_dash():
    from web.deps import get_redis
    r = get_redis()
    r.delete("dashboard:operational")
    r.delete("dashboard:executive")

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectIn(BaseModel):
    name: str
    description: str = ""
    status: str = "active"
    owner: Optional[str] = None
    due_date: Optional[date] = None
    tags: List[str] = []
    application_id: Optional[str] = None


class ProjectOut(BaseModel):
    project_id: str
    name: str
    description: str
    status: str
    owner: Optional[str]
    due_date: Optional[date]
    tags: List[str]
    application_id: Optional[str]
    task_count: int = 0
    completed_count: int = 0
    health: str = "green"
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


def _health(total: int, completed: int, overdue: int) -> str:
    if total == 0:
        return "grey"
    if overdue > 0:
        return "red"
    rate = completed / total
    if rate >= 0.8:
        return "green"
    if rate >= 0.5:
        return "yellow"
    return "red"


def _to_out(p: ProjectORM, db: Session) -> dict:
    today = date.today()
    tasks = db.query(TaskORM).filter(TaskORM.project_id == p.project_id).all()
    total = len(tasks)
    completed = sum(1 for t in tasks if t.status == "done")
    overdue = sum(1 for t in tasks if t.due_date and t.due_date < today and t.status not in ("done", "cancelled"))
    return {
        "project_id": p.project_id,
        "name": p.name,
        "description": p.description or "",
        "status": p.status or "active",
        "owner": p.owner,
        "due_date": p.due_date,
        "tags": json.loads(p.tags or "[]"),
        "application_id": p.application_id,
        "task_count": total,
        "completed_count": completed,
        "health": _health(total, completed, overdue),
        "created_at": p.created_at or datetime.utcnow(),
        "updated_at": p.updated_at,
    }


@router.get("", response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(ProjectORM).order_by(ProjectORM.created_at.desc()).all()
    return [_to_out(p, db) for p in projects]


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectIn, db: Session = Depends(get_db)):
    if not body.name.strip():
        raise HTTPException(400, "name must not be empty")
    p = ProjectORM(
        name=body.name.strip(),
        description=body.description,
        status=body.status,
        owner=body.owner,
        due_date=body.due_date,
        tags=json.dumps(body.tags),
        application_id=body.application_id,
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    # Log activity
    log_activity(
        db=db,
        entity_type="project",
        entity_id=p.project_id,
        action="created",
        description=f"Created project: {p.name}",
        details={"name": p.name, "status": p.status, "owner": p.owner}
    )

    _bust_dash()
    return _to_out(p, db)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    p = db.query(ProjectORM).filter(ProjectORM.project_id == project_id).first()
    if not p:
        raise HTTPException(404, "project not found")
    return _to_out(p, db)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, body: dict, db: Session = Depends(get_db)):
    p = db.query(ProjectORM).filter(ProjectORM.project_id == project_id).first()
    if not p:
        raise HTTPException(404, "project not found")
    allowed = {"name", "description", "status", "owner", "due_date", "tags", "application_id"}
    for k, v in body.items():
        if k not in allowed:
            continue
        if k == "tags":
            v = json.dumps(v)
        if k == "due_date" and isinstance(v, str):
            v = date.fromisoformat(v) if v else None
        setattr(p, k, v)
    p.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(p)
    _bust_dash()
    return _to_out(p, db)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    p = db.query(ProjectORM).filter(ProjectORM.project_id == project_id).first()
    if not p:
        raise HTTPException(404, "project not found")

    # Cascade delete: remove all tasks for this project
    db.query(TaskORM).filter(TaskORM.project_id == project_id).delete()

    # Delete the project
    db.delete(p)
    db.commit()
    _bust_dash()
