"""Global settings — Jira and GitLab credentials management."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
import json

from db.base import get_db
from db.models import JiraConfigORM, GitLabConfigORM

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ── Jira ──────────────────────────────────────────────────────────────────────

class JiraSettingsIn(BaseModel):
    base_url: str
    pat: str
    enabled: Optional[bool] = False


def _jira_out(cfg: JiraConfigORM) -> dict:
    return {
        "base_url": cfg.base_url or "",
        "pat": "••••••••" if cfg.pat else "",
        "pat_is_set": bool(cfg.pat),
        "enabled": cfg.enabled,
        "last_synced": cfg.last_synced,
        "created_at": cfg.created_at,
        "updated_at": cfg.updated_at,
    }


@router.get("/jira")
def get_jira_settings(db: Session = Depends(get_db)):
    """Get global Jira configuration."""
    cfg = db.query(JiraConfigORM).filter(JiraConfigORM.id == 1).first()
    if not cfg:
        cfg = JiraConfigORM(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return _jira_out(cfg)


@router.post("/jira")
def save_jira_settings(body: JiraSettingsIn, db: Session = Depends(get_db)):
    """Update global Jira configuration."""
    cfg = db.query(JiraConfigORM).filter(JiraConfigORM.id == 1).first()
    if not cfg:
        cfg = JiraConfigORM(id=1)
        db.add(cfg)

    cfg.base_url = body.base_url.strip() if body.base_url else ""

    # PAT preservation: only update if new value provided (not masked)
    if body.pat and body.pat not in ("••••••••", ""):
        cfg.pat = body.pat
    elif body.pat == "" and not cfg.pat:
        cfg.pat = ""
    # If PAT is masked, keep existing

    cfg.enabled = body.enabled
    db.commit()
    db.refresh(cfg)
    return _jira_out(cfg)


# ── GitLab ────────────────────────────────────────────────────────────────────

class GitLabSettingsIn(BaseModel):
    base_url: str
    access_token: str
    enabled: Optional[bool] = False


def _gitlab_out(cfg: GitLabConfigORM) -> dict:
    return {
        "base_url": cfg.base_url or "https://gitlab.com",
        "access_token": "••••••••" if cfg.access_token else "",
        "access_token_is_set": bool(cfg.access_token),
        "enabled": cfg.enabled,
        "last_synced": cfg.last_synced,
        "created_at": cfg.created_at,
        "updated_at": cfg.updated_at,
    }


@router.get("/gitlab")
def get_gitlab_settings(db: Session = Depends(get_db)):
    """Get global GitLab configuration."""
    cfg = db.query(GitLabConfigORM).filter(GitLabConfigORM.id == 1).first()
    if not cfg:
        cfg = GitLabConfigORM(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return _gitlab_out(cfg)


@router.post("/gitlab")
def save_gitlab_settings(body: GitLabSettingsIn, db: Session = Depends(get_db)):
    """Update global GitLab configuration."""
    cfg = db.query(GitLabConfigORM).filter(GitLabConfigORM.id == 1).first()
    if not cfg:
        cfg = GitLabConfigORM(id=1)
        db.add(cfg)

    cfg.base_url = body.base_url.strip() if body.base_url else "https://gitlab.com"

    # Token preservation: only update if new value provided (not masked)
    if body.access_token and body.access_token not in ("••••••••", ""):
        cfg.access_token = body.access_token
    elif body.access_token == "" and not cfg.access_token:
        cfg.access_token = ""
    # If token is masked, keep existing

    cfg.enabled = body.enabled
    db.commit()
    db.refresh(cfg)
    return _gitlab_out(cfg)
