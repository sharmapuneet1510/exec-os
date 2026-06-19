"""Applications — top-level entity above Projects."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from db.base import get_db
from db.models import ApplicationORM, ProjectORM

router = APIRouter(prefix="/api/applications", tags=["applications"])


class AppIn(BaseModel):
    name: str
    code: Optional[str] = ""
    description: Optional[str] = ""
    owner: Optional[str] = ""
    status: Optional[str] = "active"
    jira_project_key: Optional[str] = ""
    jira_projects: Optional[str] = ""
    gitlab_projects: Optional[str] = ""
    sprints: Optional[str] = ""


def _out(a: ApplicationORM) -> dict:
    return {
        "application_id":   a.application_id,
        "name":             a.name,
        "code":             a.code or "",
        "description":      a.description or "",
        "owner":            a.owner or "",
        "status":           a.status or "active",
        "jira_project_key": a.jira_project_key or "",
        "jira_projects":    a.jira_projects or "",
        "gitlab_projects":  a.gitlab_projects or "",
        "sprints":          a.sprints or "",
        "created_at":       a.created_at,
        "updated_at":       a.updated_at,
    }


@router.get("")
def list_apps(db: Session = Depends(get_db)):
    apps = db.query(ApplicationORM).order_by(ApplicationORM.name).all()
    result = []
    for a in apps:
        d = _out(a)
        d["project_count"] = db.query(ProjectORM).filter(
            ProjectORM.application_id == a.application_id
        ).count()
        result.append(d)
    return result


@router.post("", status_code=201)
def create_app(body: AppIn, db: Session = Depends(get_db)):
    if not body.name.strip():
        raise HTTPException(400, "name required")
    a = ApplicationORM(
        name=body.name.strip(),
        code=body.code.upper().strip() if body.code else "",
        description=body.description or "",
        owner=body.owner or "",
        status=body.status or "active",
        jira_project_key=body.jira_project_key or "",
        jira_projects=body.jira_projects or "",
        gitlab_projects=body.gitlab_projects or "",
        sprints=body.sprints or "",
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return _out(a)


@router.get("/cleanup-preview")
def cleanup_preview(db: Session = Depends(get_db)):
    """Return active applications that match test/dev naming patterns."""
    import re
    TEST_PATTERNS = [
        re.compile(r"TestApp_\d+",   re.IGNORECASE),
        re.compile(r"^(test|demo|temp|tmp|ewe|hh|asd|abc|foo|bar|baz|qux)$", re.IGNORECASE),
        re.compile(r"(Modal Test|Final Test|test\s*\d+)",   re.IGNORECASE),
    ]

    active_apps = (db.query(ApplicationORM)
                   .filter(ApplicationORM.status == "active")
                   .all())
    candidates = []
    for a in active_apps:
        if any(p.search(a.name) for p in TEST_PATTERNS):
            candidates.append({
                "application_id": a.application_id,
                "name":           a.name,
                "reason":         "name matches test/dev pattern",
            })

    return {
        "total_active":    len(active_apps),
        "candidate_count": len(candidates),
        "candidates":      candidates,
    }


@router.get("/{app_id}")
def get_app(app_id: str, db: Session = Depends(get_db)):
    a = db.query(ApplicationORM).filter(ApplicationORM.application_id == app_id).first()
    if not a:
        raise HTTPException(404, "not found")
    return _out(a)


@router.patch("/{app_id}")
def update_app(app_id: str, body: AppIn, db: Session = Depends(get_db)):
    a = db.query(ApplicationORM).filter(ApplicationORM.application_id == app_id).first()
    if not a:
        raise HTTPException(404, "not found")
    a.name             = body.name.strip()
    a.code             = body.code.upper().strip() if body.code else ""
    a.description      = body.description or ""
    a.owner            = body.owner or ""
    a.status           = body.status or "active"
    a.jira_project_key = body.jira_project_key or ""
    a.jira_projects    = body.jira_projects or ""
    a.gitlab_projects  = body.gitlab_projects or ""
    a.sprints          = body.sprints or ""
    db.commit()
    db.refresh(a)
    return _out(a)


@router.delete("/{app_id}", status_code=204)
def delete_app(app_id: str, db: Session = Depends(get_db)):
    a = db.query(ApplicationORM).filter(ApplicationORM.application_id == app_id).first()
    if not a:
        raise HTTPException(404, "not found")

    # Cascade delete: delete all projects for this application
    db.query(ProjectORM).filter(ProjectORM.application_id == app_id).delete()

    # Delete the application
    db.delete(a)
    db.commit()


@router.get("/{app_id}/projects")
def list_projects_for_app(app_id: str, db: Session = Depends(get_db)):
    """Projects scoped to a specific application."""
    a = db.query(ApplicationORM).filter(ApplicationORM.application_id == app_id).first()
    if not a:
        raise HTTPException(404, "application not found")
    projects = db.query(ProjectORM).filter(
        ProjectORM.application_id == app_id
    ).order_by(ProjectORM.name).all()
    return [
        {
            "project_id":     p.project_id,
            "name":           p.name,
            "description":    p.description or "",
            "status":         p.status,
            "owner":          p.owner or "",
            "due_date":       str(p.due_date) if p.due_date else None,
            "application_id": p.application_id,
        }
        for p in projects
    ]


@router.post("/{app_id}/archive")
def archive_application(app_id: str, db: Session = Depends(get_db)):
    """Soft-delete: mark application as archived (hidden but not permanently deleted)."""
    a = db.query(ApplicationORM).filter(ApplicationORM.application_id == app_id).first()
    if not a:
        raise HTTPException(status_code=404, detail=f"Application '{app_id}' not found")
    a.status = "archived"
    db.commit()
    db.refresh(a)
    return _out(a)
