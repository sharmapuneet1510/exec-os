from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from db.base import get_db
from db.models import ReleaseORM, ProjectORM, JiraConfigORM, AppJiraConfigORM

router = APIRouter(prefix="/api/releases", tags=["releases"])


def _parse_date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


class ReleaseIn(BaseModel):
    name: str
    version: Optional[str] = ""
    project_id: Optional[str] = None
    application_id: Optional[str] = None
    due_date: Optional[str] = None
    start_date: Optional[str] = None
    uat_date: Optional[str] = None
    sign_off_date: Optional[str] = None
    jira_project_key: Optional[str] = ""
    load_release_option: Optional[str] = ""
    status: Optional[str] = "planned"
    description: Optional[str] = ""


class ReleaseOut(BaseModel):
    release_id: str
    name: str
    version: str
    project_id: Optional[str]
    project_name: Optional[str]
    application_id: Optional[str]
    due_date: Optional[date]
    start_date: Optional[date]
    uat_date: Optional[date]
    sign_off_date: Optional[date]
    jira_project_key: Optional[str]
    load_release_option: Optional[str]
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


def _jira_get(cfg: JiraConfigORM, path: str, params: dict = None):
    import requests
    url = f"{cfg.base_url.rstrip('/')}/rest/api/2/{path.lstrip('/')}"
    try:
        resp = requests.get(
            url, params=params or {},
            headers={
                "Authorization": f"Bearer {cfg.pat}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        if resp.status_code == 422:
            return {"error": "Invalid Jira parameters"}
        if not resp.ok:
            return None
        return resp.json()
    except Exception:
        return None


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
        "start_date":          rel.start_date      if rel.start_date      else None,
        "uat_date":            rel.uat_date        if rel.uat_date        else None,
        "sign_off_date":       rel.sign_off_date   if rel.sign_off_date   else None,
        "jira_project_key":    rel.jira_project_key    or "",
        "load_release_option": rel.load_release_option or "",
        "status": rel.status,
        "description": rel.description or "",
        "days_until_due": days_until_due,
        "is_overdue": is_overdue,
        "created_at": rel.created_at,
        "updated_at": rel.updated_at,
    }


# ── Jira Integration Endpoints ────────────────────────────────────────────────
@router.get("/jira/projects", tags=["releases-jira"])
def jira_projects(app_id: str = Query(...), db: Session = Depends(get_db)):
    """Fetch Jira projects for an application."""
    jira_cfg = db.query(JiraConfigORM).first()
    if not jira_cfg or not jira_cfg.enabled or not jira_cfg.pat:
        raise HTTPException(400, "Jira integration not configured")

    data = _jira_get(jira_cfg, "project")
    if not data:
        raise HTTPException(502, "Failed to fetch Jira projects")

    projects = [
        {"key": p.get("key"), "name": p.get("name"), "id": p.get("id")}
        for p in data
    ]
    return {"projects": projects}


@router.get("/jira/versions", tags=["releases-jira"])
def jira_versions(
    app_id: str = Query(...),
    project_key: str = Query(...),
    db: Session = Depends(get_db)
):
    """Fetch versions/releases for a Jira project."""
    jira_cfg = db.query(JiraConfigORM).first()
    if not jira_cfg or not jira_cfg.enabled or not jira_cfg.pat:
        raise HTTPException(400, "Jira integration not configured")

    data = _jira_get(jira_cfg, f"project/{project_key}/versions")
    if not data:
        raise HTTPException(502, "Failed to fetch Jira versions")

    versions = [
        {
            "id": v.get("id"),
            "name": v.get("name"),
            "released": v.get("released", False),
            "releaseDate": v.get("releaseDate"),
            "description": v.get("description", ""),
        }
        for v in data
    ]
    return {"versions": versions}


@router.get("/jira/issues-in-version", tags=["releases-jira"])
def jira_issues_in_version(
    app_id: str = Query(...),
    project_key: str = Query(...),
    version_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Fetch all issues fixed in a specific Jira version."""
    jira_cfg = db.query(JiraConfigORM).first()
    if not jira_cfg or not jira_cfg.enabled or not jira_cfg.pat:
        raise HTTPException(400, "Jira integration not configured")

    # Query: project = PROJECT_KEY AND fixVersion = VERSION_ID
    jql = f'project = "{project_key}" AND fixVersion = "{version_id}"'
    fields = "summary,key,status,priority,issuetype,assignee"

    all_issues = []
    start_at = 0
    while True:
        data = _jira_get(jira_cfg, "search", {
            "jql": jql,
            "fields": fields,
            "maxResults": 100,
            "startAt": start_at
        })
        if not data:
            break
        if data.get("error"):
            raise HTTPException(400, data["error"])

        issues = data.get("issues", [])
        for issue in issues:
            f = issue.get("fields", {})
            all_issues.append({
                "key": issue.get("key"),
                "summary": f.get("summary", ""),
                "status": (f.get("status") or {}).get("name", ""),
                "priority": (f.get("priority") or {}).get("name", ""),
                "type": (f.get("issuetype") or {}).get("name", ""),
                "assignee": (f.get("assignee") or {}).get("displayName", "Unassigned"),
            })

        total = data.get("total", 0)
        start_at += len(issues)
        if start_at >= total or not issues:
            break

    return {
        "issues": all_issues,
        "count": len(all_issues),
        "summary": f"{len(all_issues)} issues in this version"
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


@router.post("", response_model=ReleaseOut, status_code=201)
def create_release(body: ReleaseIn, db: Session = Depends(get_db)):
    if not body.name.strip():
        raise HTTPException(400, "name must not be empty")

    # Validate project_id if provided
    if body.project_id:
        project = db.query(ProjectORM).filter(ProjectORM.project_id == body.project_id).first()
        if not project:
            raise HTTPException(400, "project not found")

    rel = ReleaseORM(
        name=body.name.strip(),
        version=body.version,
        project_id=body.project_id,
        application_id=body.application_id,
        due_date=_parse_date(body.due_date),
        start_date=_parse_date(body.start_date),
        uat_date=_parse_date(body.uat_date),
        sign_off_date=_parse_date(body.sign_off_date),
        jira_project_key=body.jira_project_key or "",
        load_release_option=body.load_release_option or "",
        status=body.status,
        description=body.description,
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)
    _bust_dash()
    return _to_out(rel, db)


@router.get("/{release_id}", response_model=ReleaseOut)
def get_release(release_id: str, db: Session = Depends(get_db)):
    rel = db.query(ReleaseORM).filter(ReleaseORM.release_id == release_id).first()
    if not rel:
        raise HTTPException(404, "release not found")
    return _to_out(rel, db)


@router.patch("/{release_id}", response_model=ReleaseOut)
def update_release(release_id: str, body: dict, db: Session = Depends(get_db)):
    rel = db.query(ReleaseORM).filter(ReleaseORM.release_id == release_id).first()
    if not rel:
        raise HTTPException(404, "release not found")

    date_fields = {"due_date", "start_date", "uat_date", "sign_off_date"}
    allowed = {
        "name", "version", "project_id", "application_id",
        "due_date", "start_date", "uat_date", "sign_off_date",
        "jira_project_key", "load_release_option",
        "status", "description",
    }
    for k, v in body.items():
        if k not in allowed:
            continue
        if k in date_fields and isinstance(v, str):
            v = _parse_date(v)
        setattr(rel, k, v)

    # Validate project_id if changed
    if "project_id" in body and body["project_id"]:
        project = db.query(ProjectORM).filter(ProjectORM.project_id == body["project_id"]).first()
        if not project:
            raise HTTPException(400, "project not found")

    rel.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rel)
    _bust_dash()
    return _to_out(rel, db)


@router.delete("/{release_id}", status_code=204)
def delete_release(release_id: str, db: Session = Depends(get_db)):
    rel = db.query(ReleaseORM).filter(ReleaseORM.release_id == release_id).first()
    if not rel:
        raise HTTPException(404, "release not found")
    db.delete(rel)
    db.commit()
    _bust_dash()
