"""Global settings — Jira, GitLab, and general system settings."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
import json
import os
import pathlib

from db.base import get_db, DATABASE_URL
from db.models import JiraConfigORM, GitLabConfigORM

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ── General Settings ──────────────────────────────────────────────────────────

@router.get("/general")
def get_general_settings():
    """Get general system settings including database info and backup config."""
    db_type = "sqlite" if DATABASE_URL.startswith("sqlite") else "postgresql" if DATABASE_URL.startswith("postgres") else "other"
    db_path = None
    if db_type == "sqlite":
        raw = DATABASE_URL.replace("sqlite:///", "")
        db_path = os.path.abspath(raw) if raw else None

    return {
        "database": {
            "type": db_type,
            "path": db_path,
            "url_masked": _mask_db_url(DATABASE_URL),
        },
        "backup": {
            "enabled": True,
            "location": os.path.expanduser("~/.commanddesk/"),
            "schedule": "Daily at 2:00 AM",
            "retention_days": 30,
            "recommendation": "Backup execos.db file daily to external storage",
        },
        "system": {
            "python_version": _get_python_version(),
            "config_file": str(pathlib.Path(__file__).parent.parent.parent / ".env"),
        }
    }


def _mask_db_url(url: str) -> str:
    """Mask sensitive parts of database URL."""
    if "@" in url:
        scheme, rest = url.split("://", 1)
        if "@" in rest:
            userinfo, hostpart = rest.split("@", 1)
            if ":" in userinfo:
                user = userinfo.split(":")[0]
                userinfo = f"{user}:••••"
            url = f"{scheme}://{userinfo}@{hostpart}"
    return url


def _get_python_version() -> str:
    """Get Python version."""
    import sys
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


# ── Database location (edit + persist to .env, applied on restart) ─────────────

def _env_file_path() -> str:
    return str(pathlib.Path(__file__).parent.parent.parent / ".env")


def _sqlite_url_for(abs_path: str) -> str:
    """Build a SQLAlchemy sqlite URL for an absolute filesystem path."""
    p = os.path.abspath(os.path.expanduser(abs_path))
    return "sqlite:///" + p if p.startswith("/") else "sqlite:///" + "/" + p


def _set_env_var(env_path: str, key: str, value: str) -> None:
    """Idempotently set KEY=value in a .env file, preserving other lines/comments."""
    lines = []
    if os.path.exists(env_path):
        with open(env_path) as f:
            lines = f.read().splitlines()
    out, replaced = [], False
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped and \
                stripped.split("=", 1)[0].strip() == key:
            out.append(f"{key}={value}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f"{key}={value}")
    with open(env_path, "w") as f:
        f.write("\n".join(out) + "\n")


class DatabaseSettingsIn(BaseModel):
    db_path: str
    copy_current: Optional[bool] = True


@router.post("/database")
def save_database_settings(body: DatabaseSettingsIn):
    """Set the SQLite database file path (persisted to .env; applied on restart)."""
    raw = (body.db_path or "").strip()
    if not raw:
        raise HTTPException(400, "db_path is required")
    new_path = os.path.abspath(os.path.expanduser(raw))
    if not new_path.endswith(".db"):
        raise HTTPException(400, "path should point to a .db file")

    parent = os.path.dirname(new_path)
    try:
        os.makedirs(parent, exist_ok=True)
    except OSError as e:
        raise HTTPException(400, f"cannot create directory {parent}: {e}")
    if not os.access(parent, os.W_OK):
        raise HTTPException(400, f"directory not writable: {parent}")

    # Optionally copy the current DB so data follows the move.
    copied = False
    cur_path = None
    if DATABASE_URL.startswith("sqlite"):
        cur_path = os.path.abspath(DATABASE_URL.replace("sqlite:///", ""))
    if body.copy_current and cur_path and os.path.exists(cur_path) \
            and os.path.abspath(cur_path) != new_path and not os.path.exists(new_path):
        import shutil
        try:
            shutil.copy2(cur_path, new_path)
            copied = True
        except OSError as e:
            raise HTTPException(400, f"failed to copy database: {e}")

    _set_env_var(_env_file_path(), "DATABASE_URL", _sqlite_url_for(new_path))
    return {
        "ok": True,
        "db_path": new_path,
        "copied_current_db": copied,
        "restart_required": True,
        "message": "Saved. Restart the app to connect to the new database location.",
    }


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
