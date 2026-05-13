"""Per-application Jira, GitLab, and Sprint configuration."""

import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import get_db
from db.models import (
    ApplicationORM,
    AppJiraConfigORM, AppGitLabConfigORM, AppSprintConfigORM,
)

router = APIRouter(prefix="/api/applications/{app_id}/integrations", tags=["app-integrations"])


def _get_app(app_id: str, db: Session):
    a = db.query(ApplicationORM).filter(ApplicationORM.application_id == app_id).first()
    if not a:
        raise HTTPException(404, "application not found")
    return a


# ── Jira ──────────────────────────────────────────────────────────────────────

class JiraIn(BaseModel):
    base_url: str = ""
    pat: str = ""  # Personal Access Token
    project_keys: list = []
    enabled: bool = False


def _jira_out(c: AppJiraConfigORM) -> dict:
    return {
        "base_url": c.base_url or "",
        "pat": "••••" if c.pat else "",
        "project_keys": json.loads(c.project_keys or "[]"),
        "enabled": c.enabled,
        "last_synced": c.last_synced,
    }


@router.get("/jira")
def get_jira(app_id: str, db: Session = Depends(get_db)):
    _get_app(app_id, db)
    c = db.query(AppJiraConfigORM).filter(AppJiraConfigORM.application_id == app_id).first()
    if not c:
        return {"base_url": "", "pat": "", "project_keys": [], "enabled": False, "last_synced": None}
    return _jira_out(c)


@router.post("/jira")
def save_jira(app_id: str, body: JiraIn, db: Session = Depends(get_db)):
    _get_app(app_id, db)
    c = db.query(AppJiraConfigORM).filter(AppJiraConfigORM.application_id == app_id).first()
    if not c:
        c = AppJiraConfigORM(application_id=app_id)
        db.add(c)
    c.base_url = body.base_url.strip()

    # PAT preservation: only update if it's a new value
    if body.pat and body.pat not in ("••••", ""):
        c.pat = body.pat
    elif body.pat == "" and not c.pat:
        c.pat = ""
    # If PAT is "••••", keep existing

    c.project_keys = json.dumps(body.project_keys)
    c.enabled = body.enabled
    db.commit()
    db.refresh(c)
    return _jira_out(c)


# ── GitLab ────────────────────────────────────────────────────────────────────

class GitLabIn(BaseModel):
    base_url: str = "https://gitlab.com"
    access_token: str = ""
    project_ids: list = []
    enabled: bool = False


def _gl_out(c: AppGitLabConfigORM) -> dict:
    return {
        "id": c.id,
        "application_id": c.application_id,
        "base_url": c.base_url or "https://gitlab.com",
        "access_token": "••••" if c.access_token else "",
        "project_ids": json.loads(c.project_ids or "[]"),
        "enabled": c.enabled,
        "updated_at": c.updated_at,
    }


@router.get("/gitlab")
def get_gitlab(app_id: str, db: Session = Depends(get_db)):
    _get_app(app_id, db)
    c = db.query(AppGitLabConfigORM).filter(AppGitLabConfigORM.application_id == app_id).first()
    if not c:
        return {"application_id": app_id, "base_url": "https://gitlab.com",
                "access_token": "", "project_ids": [], "enabled": False}
    return _gl_out(c)


@router.post("/gitlab")
def save_gitlab(app_id: str, body: GitLabIn, db: Session = Depends(get_db)):
    _get_app(app_id, db)
    c = db.query(AppGitLabConfigORM).filter(AppGitLabConfigORM.application_id == app_id).first()
    if not c:
        c = AppGitLabConfigORM(application_id=app_id)
        db.add(c)
    c.base_url = body.base_url.strip() or "https://gitlab.com"
    # Only update token if it's a new value (not masked "••••" and not empty)
    if body.access_token and body.access_token not in ("••••", ""):
        c.access_token = body.access_token
    elif body.access_token == "" and not c.access_token:
        # New record with empty token — that's ok, just leave it empty
        c.access_token = ""
    # If token is "••••", it means user didn't change it — keep existing
    c.project_ids = json.dumps(body.project_ids)
    c.enabled = body.enabled
    db.commit()
    db.refresh(c)
    return _gl_out(c)


# ── Sprint ────────────────────────────────────────────────────────────────────

class SprintIn(BaseModel):
    board_id: str = ""
    sprint_id: str = ""
    sprint_name: str = ""
    my_jira_email: str = ""
    my_gitlab_username: str = ""


def _sprint_out(c: AppSprintConfigORM) -> dict:
    return {
        "id": c.id,
        "application_id": c.application_id,
        "board_id": c.board_id or "",
        "sprint_id": c.sprint_id or "",
        "sprint_name": c.sprint_name or "",
        "my_jira_email": c.my_jira_email or "",
        "my_gitlab_username": c.my_gitlab_username or "",
        "updated_at": c.updated_at,
    }


@router.get("/sprint")
def get_sprint(app_id: str, db: Session = Depends(get_db)):
    _get_app(app_id, db)
    c = db.query(AppSprintConfigORM).filter(AppSprintConfigORM.application_id == app_id).first()
    if not c:
        return {"application_id": app_id, "board_id": "", "sprint_id": "",
                "sprint_name": "", "my_jira_email": "", "my_gitlab_username": ""}
    return _sprint_out(c)


@router.post("/sprint")
def save_sprint(app_id: str, body: SprintIn, db: Session = Depends(get_db)):
    _get_app(app_id, db)
    c = db.query(AppSprintConfigORM).filter(AppSprintConfigORM.application_id == app_id).first()
    if not c:
        c = AppSprintConfigORM(application_id=app_id)
        db.add(c)
    c.board_id = body.board_id.strip()
    c.sprint_id = body.sprint_id.strip()
    c.sprint_name = body.sprint_name.strip()
    c.my_jira_email = body.my_jira_email.strip()
    c.my_gitlab_username = body.my_gitlab_username.strip()
    db.commit()
    db.refresh(c)
    return _sprint_out(c)


