"""GitLab integration — config, connection test, and open MR feed."""

import json, time, logging
from datetime import datetime
from typing import Optional

from web.config import get_ssl_verify

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import SessionLocal
from db.models import AppGitLabConfigORM

log = logging.getLogger("execos.gitlab")
router = APIRouter(prefix="/api/gitlab", tags=["gitlab"])

_cache: dict = {}
_CACHE_TTL = 300


def _cache_get(key):
    entry = _cache.get(key)
    if entry and time.time() - entry["ts"] < _CACHE_TTL:
        return entry["data"]
    return None


def _cache_set(key, data):
    _cache[key] = {"data": data, "ts": time.time()}


def _cache_bust():
    _cache.clear()


def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_cfg(app_id: str, db: Session) -> AppGitLabConfigORM:
    cfg = db.query(AppGitLabConfigORM).filter(AppGitLabConfigORM.application_id == app_id).first()
    if not cfg:
        raise HTTPException(404, f"No GitLab config found for application '{app_id}' — configure it in Settings first")
    return cfg


def _gl_get(cfg: AppGitLabConfigORM, path: str, params: dict = None):
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    base = cfg.base_url.rstrip("/") if cfg.base_url else "https://gitlab.com"
    url = f"{base}/api/v4/{path.lstrip('/')}"
    resp = requests.get(
        url,
        params=params or {},
        headers={"PRIVATE-TOKEN": cfg.access_token, "Accept": "application/json"},
        timeout=15,
        verify=get_ssl_verify(),  # Controlled via EXECOS_SSL_VERIFY env var
    )
    if resp.status_code == 401:
        raise HTTPException(401, "GitLab auth failed — check your access token")
    if resp.status_code == 403:
        raise HTTPException(403, "GitLab returned 403 — token may lack api scope")
    if resp.status_code == 404:
        raise HTTPException(404, "GitLab resource not found — check project URLs/IDs")
    if not resp.ok:
        raise HTTPException(resp.status_code, f"GitLab error: {resp.text[:200]}")
    return resp.json(), resp.headers




@router.post("/test")
def test_connection(app_id: str = Query(...), db: Session = Depends(_db)):
    cfg = _get_cfg(app_id, db)
    if not cfg.access_token:
        raise HTTPException(400, "GitLab not configured — enter an access token first")
    data, _ = _gl_get(cfg, "user")
    return {
        "ok": True,
        "username":     data.get("username", ""),
        "display_name": data.get("name", ""),
        "message": f"Connected as {data.get('name', data.get('username', ''))}",
    }


@router.get("/projects")
def list_projects(app_id: str = Query(...), db: Session = Depends(_db)):
    """Return projects from the configured list (resolves path-based IDs)."""
    cfg = _get_cfg(app_id, db)
    if not cfg.enabled or not cfg.access_token:
        raise HTTPException(400, "GitLab integration is not enabled")
    cache_key = f"gl_projects_{app_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    raw_ids = json.loads(cfg.project_ids or "[]")
    if not raw_ids:
        # Fall back to listing accessible projects
        data, _ = _gl_get(cfg, "projects", {"membership": True, "per_page": 50, "order_by": "name"})
        raw_ids = [str(p["id"]) for p in data]

    projects = []
    for pid in raw_ids[:30]:
        import urllib.parse
        encoded = urllib.parse.quote(str(pid), safe="")
        try:
            p, _ = _gl_get(cfg, f"projects/{encoded}")
            projects.append({"id": p["id"], "name": p["name"], "path": p["path_with_namespace"], "web_url": p.get("web_url","")})
        except HTTPException:
            pass
    _cache_set(cache_key, projects)
    return projects


@router.get("/mrs")
def open_mrs(app_id: str = Query(...), db: Session = Depends(_db)):
    """Return all open MRs across configured projects, grouped by author."""
    cfg = _get_cfg(app_id, db)
    if not cfg.enabled or not cfg.access_token:
        raise HTTPException(400, "GitLab integration is not enabled")

    cache_key = f"gl_mrs_{app_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    projects = list_projects.__wrapped__(db) if hasattr(list_projects, "__wrapped__") else []
    # Re-fetch projects without cache for simplicity
    raw_ids = json.loads(cfg.project_ids or "[]")
    if not raw_ids:
        data, _ = _gl_get(cfg, "projects", {"membership": True, "per_page": 50})
        raw_ids = [str(p["id"]) for p in data]

    all_mrs = []
    project_map = {}

    import urllib.parse
    for pid in raw_ids[:20]:
        encoded = urllib.parse.quote(str(pid), safe="")
        try:
            proj, _ = _gl_get(cfg, f"projects/{encoded}")
            project_map[proj["id"]] = {"name": proj["name"], "path": proj["path_with_namespace"], "web_url": proj.get("web_url","")}
            mrs, _ = _gl_get(cfg, f"projects/{encoded}/merge_requests", {
                "state": "opened", "per_page": 50, "order_by": "updated_at"
            })
            for mr in mrs:
                author = mr.get("author") or {}
                reviewer_names = [r.get("name","") for r in (mr.get("reviewers") or [])]
                all_mrs.append({
                    "id":           mr["iid"],
                    "title":        mr.get("title",""),
                    "state":        mr.get("state","opened"),
                    "draft":        mr.get("draft", mr.get("work_in_progress", False)),
                    "author":       author.get("name",""),
                    "author_avatar":author.get("avatar_url"),
                    "author_user":  author.get("username",""),
                    "target_branch":mr.get("target_branch",""),
                    "source_branch":mr.get("source_branch",""),
                    "created_at":   (mr.get("created_at") or "")[:10],
                    "updated_at":   (mr.get("updated_at") or "")[:10],
                    "web_url":      mr.get("web_url",""),
                    "project_id":   proj["id"],
                    "project_name": proj["name"],
                    "has_conflicts":mr.get("has_conflicts", False),
                    "reviewers":    reviewer_names,
                    "upvotes":      mr.get("upvotes", 0),
                    "downvotes":    mr.get("downvotes", 0),
                    "changes_count":str(mr.get("changes_count") or ""),
                })
        except HTTPException:
            pass

    # Group by author
    by_author: dict = {}
    for mr in all_mrs:
        a = mr["author"] or "Unknown"
        if a not in by_author:
            by_author[a] = {"name": a, "avatar": mr["author_avatar"], "username": mr["author_user"], "mrs": [], "total": 0, "draft": 0, "ready": 0}
        by_author[a]["mrs"].append(mr)
        by_author[a]["total"] += 1
        if mr["draft"]:
            by_author[a]["draft"] += 1
        else:
            by_author[a]["ready"] += 1

    # Project summary
    proj_summary = {}
    for mr in all_mrs:
        pid = mr["project_id"]
        if pid not in proj_summary:
            proj_summary[pid] = {**project_map.get(pid, {"name": str(pid), "path": ""}), "open": 0, "draft": 0}
        proj_summary[pid]["open"] += 1
        if mr["draft"]:
            proj_summary[pid]["draft"] += 1

    result = {
        "total_mrs":     len(all_mrs),
        "ready_mrs":     sum(1 for m in all_mrs if not m["draft"]),
        "draft_mrs":     sum(1 for m in all_mrs if m["draft"]),
        "authors":       sorted(by_author.values(), key=lambda x: -x["total"]),
        "projects":      list(proj_summary.values()),
        "all_mrs":       sorted(all_mrs, key=lambda x: x["updated_at"], reverse=True),
        "last_fetched":  datetime.utcnow().isoformat(),
    }

    _cache_set(cache_key, result)
    cfg.last_synced = datetime.utcnow()
    db.commit()
    return result


@router.post("/refresh")
def refresh_cache(app_id: str = Query(...)):
    _cache.pop(f"gl_mrs_{app_id}", None)
    _cache.pop(f"gl_projects_{app_id}", None)
    return {"ok": True}
