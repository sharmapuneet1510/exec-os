"""Jira integration — config, connection test, and live team workload."""

import json, time, logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import SessionLocal
from db.models import JiraConfigORM

log = logging.getLogger("execos.jira")
router = APIRouter(prefix="/api/jira", tags=["jira"])

# ── Simple in-process cache (5-min TTL) ───────────────────────────────────────
_cache: dict = {}
_CACHE_TTL = 300  # seconds


def _cache_get(key):
    entry = _cache.get(key)
    if entry and time.time() - entry["ts"] < _CACHE_TTL:
        return entry["data"]
    return None


def _cache_set(key, data):
    _cache[key] = {"data": data, "ts": time.time()}


def _cache_bust():
    _cache.clear()


# ── DB helpers ────────────────────────────────────────────────────────────────
def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_cfg(db: Session) -> JiraConfigORM:
    cfg = db.query(JiraConfigORM).filter(JiraConfigORM.id == 1).first()
    if not cfg:
        cfg = JiraConfigORM(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


# ── Jira HTTP helpers ─────────────────────────────────────────────────────────
def _jira_get(cfg: JiraConfigORM, path: str, params: dict = None):
    """Make an authenticated GET to the Jira Cloud REST API."""
    import requests
    url = f"{cfg.base_url.rstrip('/')}/rest/api/3/{path.lstrip('/')}"
    resp = requests.get(
        url,
        params=params or {},
        auth=(cfg.email, cfg.api_token),
        headers={"Accept": "application/json"},
        timeout=15,
    )
    if resp.status_code == 401:
        raise HTTPException(401, "Jira auth failed — check email and API token")
    if resp.status_code == 403:
        raise HTTPException(403, "Jira returned 403 — token may lack permissions")
    if not resp.ok:
        raise HTTPException(resp.status_code, f"Jira error: {resp.text[:200]}")
    return resp.json()


def _build_jql(cfg: JiraConfigORM, extra: str = "") -> str:
    keys = json.loads(cfg.project_keys or "[]")
    parts = []
    if keys:
        quoted = ", ".join(f'"{k}"' for k in keys)
        parts.append(f"project in ({quoted})")
    parts.append('statusCategory != Done')
    if extra:
        parts.append(extra)
    return " AND ".join(parts)


# ── Schemas ───────────────────────────────────────────────────────────────────
class JiraConfigIn(BaseModel):
    base_url:     Optional[str] = ""
    email:        Optional[str] = ""
    api_token:    Optional[str] = ""
    project_keys: Optional[str] = "[]"  # raw JSON string
    enabled:      Optional[bool] = False


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("/config")
def get_config(db: Session = Depends(_db)):
    cfg = _get_cfg(db)
    return {
        "base_url":     cfg.base_url or "",
        "email":        cfg.email or "",
        "api_token":    "••••••••" if cfg.api_token else "",
        "project_keys": cfg.project_keys or "[]",
        "enabled":      cfg.enabled,
        "last_synced":  cfg.last_synced.isoformat() if cfg.last_synced else None,
    }


@router.post("/config")
def save_config(body: JiraConfigIn, db: Session = Depends(_db)):
    cfg = _get_cfg(db)
    if body.base_url is not None:
        cfg.base_url = body.base_url.rstrip("/")
    if body.email is not None:
        cfg.email = body.email
    if body.api_token and body.api_token != "••••••••":
        cfg.api_token = body.api_token
    if body.project_keys is not None:
        # Accept comma-separated string OR JSON array
        raw = body.project_keys.strip()
        if not raw.startswith("["):
            keys = [k.strip().upper() for k in raw.split(",") if k.strip()]
            cfg.project_keys = json.dumps(keys)
        else:
            cfg.project_keys = raw
    cfg.enabled = body.enabled
    db.commit()
    _cache_bust()
    return {"ok": True}


@router.post("/test")
def test_connection(db: Session = Depends(_db)):
    cfg = _get_cfg(db)
    if not cfg.base_url or not cfg.email or not cfg.api_token:
        raise HTTPException(400, "Jira not configured — fill in URL, email, and API token first")
    data = _jira_get(cfg, "myself")
    return {
        "ok": True,
        "display_name": data.get("displayName", ""),
        "account_id":   data.get("accountId", ""),
        "message": f"Connected as {data.get('displayName', cfg.email)}",
    }


@router.get("/projects")
def list_projects(db: Session = Depends(_db)):
    cfg = _get_cfg(db)
    if not cfg.enabled or not cfg.api_token:
        raise HTTPException(400, "Jira integration is not enabled")
    cached = _cache_get("projects")
    if cached:
        return cached
    data = _jira_get(cfg, "project/search", {"maxResults": 50, "orderBy": "name"})
    projects = [
        {"key": p["key"], "name": p["name"], "type": p.get("projectTypeKey", "")}
        for p in data.get("values", [])
    ]
    _cache_set("projects", projects)
    return projects


@router.get("/team")
def team_workload(db: Session = Depends(_db)):
    """Return team workload: one entry per assignee with their open issues."""
    cfg = _get_cfg(db)
    if not cfg.enabled or not cfg.api_token:
        raise HTTPException(400, "Jira integration is not enabled")

    cached = _cache_get("team")
    if cached:
        return cached

    jql = _build_jql(cfg)
    fields = "summary,assignee,status,priority,issuetype,project,created,updated,duedate"
    data = _jira_get(cfg, "search", {
        "jql": jql,
        "fields": fields,
        "maxResults": 200,
    })

    # Group by assignee
    team: dict = {}
    unassigned_issues = []

    for issue in data.get("issues", []):
        f = issue.get("fields", {})
        assignee = f.get("assignee")
        name  = assignee["displayName"] if assignee else "Unassigned"
        akey  = assignee["accountId"]   if assignee else "__unassigned__"
        avatar= assignee["avatarUrls"]["48x48"] if assignee else None

        rec = {
            "key":      issue["key"],
            "summary":  f.get("summary", ""),
            "status":   (f.get("status") or {}).get("name", ""),
            "priority": (f.get("priority") or {}).get("name", ""),
            "type":     (f.get("issuetype") or {}).get("name", ""),
            "project":  (f.get("project") or {}).get("key", ""),
            "due_date": f.get("duedate"),
            "updated":  (f.get("updated") or "")[:10],
        }

        if akey not in team:
            team[akey] = {
                "account_id":   akey,
                "display_name": name,
                "avatar_url":   avatar,
                "issues":       [],
                "total":        0,
                "by_priority":  {"Highest":0,"High":0,"Medium":0,"Low":0,"Lowest":0},
                "by_status":    {},
            }
        team[akey]["issues"].append(rec)
        team[akey]["total"] += 1
        pri = rec["priority"] or "Medium"
        team[akey]["by_priority"][pri] = team[akey]["by_priority"].get(pri, 0) + 1
        st = rec["status"]
        team[akey]["by_status"][st] = team[akey]["by_status"].get(st, 0) + 1

    result = {
        "total_issues": data.get("total", 0),
        "team": sorted(team.values(), key=lambda x: -x["total"]),
        "last_fetched": datetime.utcnow().isoformat(),
    }

    _cache_set("team", result)

    # Update last_synced timestamp
    cfg.last_synced = datetime.utcnow()
    db.commit()

    return result


@router.post("/refresh")
def refresh_cache(db: Session = Depends(_db)):
    _cache_bust()
    return {"ok": True, "message": "Cache cleared — next fetch will pull live data"}
