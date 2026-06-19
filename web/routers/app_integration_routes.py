"""Per-application Jira, GitLab, and Sprint configuration."""

import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import get_db
from db.models import (
    ApplicationORM,
    JiraConfigORM, AppJiraConfigORM, AppGitLabConfigORM, AppSprintConfigORM,
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


def _jira_out(global_cfg: JiraConfigORM, app_cfg: AppJiraConfigORM) -> dict:
    effective_url = (
        (app_cfg.base_url if app_cfg and app_cfg.base_url else None) or
        (global_cfg.base_url if global_cfg else None) or ""
    )
    has_pat = bool(
        (app_cfg.pat if app_cfg else None) or
        (global_cfg.pat if global_cfg else None)
    )
    return {
        "base_url":     effective_url,
        "pat":          "••••" if has_pat else "",
        "project_keys": json.loads(app_cfg.project_keys or "[]") if app_cfg else [],
        "enabled":      bool(
            (app_cfg.enabled if app_cfg else False) or
            (global_cfg.enabled if global_cfg else False)
        ),
        "last_synced":  global_cfg.last_synced if global_cfg else None,
    }


@router.get("/jira")
def get_jira(app_id: str, db: Session = Depends(get_db)):
    _get_app(app_id, db)
    global_cfg = db.query(JiraConfigORM).first()
    app_cfg = db.query(AppJiraConfigORM).filter(AppJiraConfigORM.application_id == app_id).first()
    return _jira_out(global_cfg, app_cfg)


@router.post("/jira")
def save_jira(app_id: str, body: JiraIn, db: Session = Depends(get_db)):
    _get_app(app_id, db)

    # Get or create global Jira config (shared across all apps)
    global_cfg = db.query(JiraConfigORM).first()
    if not global_cfg:
        global_cfg = JiraConfigORM()
        db.add(global_cfg)

    global_cfg.base_url = body.base_url.strip()
    # PAT preservation: only update if it's a new value
    if body.pat and body.pat not in ("••••", ""):
        global_cfg.pat = body.pat
    elif body.pat == "" and not global_cfg.pat:
        global_cfg.pat = ""
    # If PAT is "••••", keep existing
    global_cfg.enabled = body.enabled

    # Get or create app-specific Jira config (for project keys)
    app_cfg = db.query(AppJiraConfigORM).filter(AppJiraConfigORM.application_id == app_id).first()
    if not app_cfg:
        app_cfg = AppJiraConfigORM(application_id=app_id)
        db.add(app_cfg)

    app_cfg.project_keys = json.dumps(body.project_keys)

    # Write per-app credentials (isolates this app from others)
    app_cfg.base_url = body.base_url.strip()
    if body.pat and body.pat not in ("••••", ""):
        app_cfg.pat = body.pat
    elif body.pat == "" and not app_cfg.pat:
        app_cfg.pat = ""
    app_cfg.enabled = body.enabled

    db.commit()
    db.refresh(global_cfg)
    db.refresh(app_cfg)
    return _jira_out(global_cfg, app_cfg)


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


