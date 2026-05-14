"""Jira integration — config, connection test, and live team workload."""

import json, time, logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import SessionLocal
from db.models import JiraConfigORM, AppJiraConfigORM

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


# ── Jira Header Builder ───────────────────────────────────────────────────────
def _jira_headers(cfg: JiraConfigORM) -> dict:
    """Return centralized Jira API headers with bearer token authentication.

    All Jira API requests should use these headers for authentication.
    Centralized here for easy maintenance and future changes.

    Args:
        cfg: JiraConfigORM config with PAT

    Returns:
        dict: Headers including Authorization: Bearer <PAT>
    """
    return {
        "Authorization": f"Bearer {cfg.pat}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


# ── DB helpers ────────────────────────────────────────────────────────────────
def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_cfg(db: Session) -> JiraConfigORM:
    cfg = db.query(JiraConfigORM).first()
    if not cfg:
        raise HTTPException(404, "Jira config not found — configure it in Settings first")
    return cfg


def _get_app_cfg(app_id: str, db: Session) -> AppJiraConfigORM:
    cfg = db.query(AppJiraConfigORM).filter(AppJiraConfigORM.application_id == app_id).first()
    if not cfg:
        raise HTTPException(404, f"No Jira config found for application '{app_id}' — configure it in Settings first")
    return cfg


# ── Jira HTTP helpers ─────────────────────────────────────────────────────────
def _jira_get(cfg: JiraConfigORM, path: str, params: dict = None):
    """Make an authenticated GET to Jira API v2 with bearer token.

    Uses Jira REST API v2 with SSL verification disabled.
    """
    import requests
    import urllib3
    # Disable SSL warnings since verify=False
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    url = f"{cfg.base_url.rstrip('/')}/rest/api/2/{path.lstrip('/')}"
    resp = requests.get(
        url,
        params=params or {},
        headers=_jira_headers(cfg),
        timeout=15,
        verify=False,
    )
    if resp.status_code == 401:
        raise HTTPException(401, "Jira auth failed — check PAT and permissions")
    if resp.status_code == 403:
        raise HTTPException(403, "Jira returned 403 — PAT may lack permissions")
    if not resp.ok:
        raise HTTPException(resp.status_code, f"Jira error: {resp.text[:200]}")
    return resp.json()


def _build_jql(app_cfg: AppJiraConfigORM, extra: str = "") -> str:
    keys = json.loads(app_cfg.project_keys or "[]")
    parts = []
    if keys:
        quoted = ", ".join(f'"{k}"' for k in keys)
        parts.append(f"project in ({quoted})")
    parts.append('statusCategory != "Done"')
    if extra:
        parts.append(extra)
    return " AND ".join(parts)


def _jira_search_all(cfg: JiraConfigORM, jql: str, fields: str) -> list:
    """Paginate through all Jira search results (max 500)."""
    all_issues = []
    start_at = 0
    max_results = 100
    while True:
        data = _jira_get(cfg, "search", {
            "jql": jql, "fields": fields,
            "maxResults": max_results, "startAt": start_at,
        })
        issues = data.get("issues", [])
        all_issues.extend(issues)
        total = data.get("total", 0)
        start_at += len(issues)
        if start_at >= min(total, 500) or not issues:
            break
    return all_issues


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("/test")
def test_connection(app_id: str = Query(...), db: Session = Depends(_db)):
    cfg = _get_cfg(db)
    if not cfg.base_url or not cfg.pat:
        raise HTTPException(400, "Jira not configured — fill in URL and PAT first")
    data = _jira_get(cfg, "myself")
    return {
        "ok": True,
        "display_name": data.get("displayName", ""),
        "account_id":   data.get("accountId", ""),
        "message": f"Connected as {data.get('displayName', '')}",
    }


@router.get("/projects")
def list_projects(app_id: str = Query(...), db: Session = Depends(_db)):
    cfg = _get_cfg(db)
    if not cfg.enabled or not cfg.pat:
        raise HTTPException(400, "Jira integration is not enabled")
    cache_key = f"projects_{app_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
    data = _jira_get(cfg, "project/search", {"maxResults": 50, "orderBy": "name"})
    projects = [
        {"key": p["key"], "name": p["name"], "type": p.get("projectTypeKey", "")}
        for p in data.get("values", [])
    ]
    _cache_set(cache_key, projects)
    return projects


@router.get("/team")
def team_workload(app_id: str = Query(...), db: Session = Depends(_db)):
    """Return team workload: one entry per assignee with their open issues."""
    cfg = _get_cfg(db)
    if not cfg.enabled or not cfg.pat:
        raise HTTPException(400, "Jira integration is not enabled")

    cache_key = f"team_{app_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    app_cfg = _get_app_cfg(app_id, db)
    jql = _build_jql(app_cfg)
    fields = "summary,assignee,status,priority,issuetype,project,created,updated,duedate"
    issues = _jira_search_all(cfg, jql, fields)

    # Group by assignee
    team: dict = {}

    for issue in issues:
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
        "total_issues": len(issues),
        "team": sorted(team.values(), key=lambda x: -x["total"]),
        "last_fetched": datetime.utcnow().isoformat(),
    }

    _cache_set(cache_key, result)

    cfg.last_synced = datetime.utcnow()
    db.commit()

    return result


@router.post("/refresh")
def refresh_cache(app_id: str = Query(...)):
    _cache.pop(f"team_{app_id}", None)
    _cache.pop(f"projects_{app_id}", None)
    return {"ok": True, "message": "Cache cleared — next fetch will pull live data"}
