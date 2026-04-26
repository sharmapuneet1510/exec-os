"""Sprint Board — configure sprint, fetch items, correlate GitLab MRs."""

import json, time, re, logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import SessionLocal
from db.models import SprintConfigORM, JiraConfigORM, GitLabConfigORM

log = logging.getLogger("execos.sprint")
router = APIRouter(prefix="/api/sprint", tags=["sprint"])

_cache: dict = {}
_CACHE_TTL = 300


def _cache_get(key):
    e = _cache.get(key)
    if e and time.time() - e["ts"] < _CACHE_TTL:
        return e["data"]
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


def _get_cfg(db: Session) -> SprintConfigORM:
    cfg = db.query(SprintConfigORM).filter(SprintConfigORM.id == 1).first()
    if not cfg:
        cfg = SprintConfigORM(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def _get_jira_cfg(db: Session) -> JiraConfigORM:
    cfg = db.query(JiraConfigORM).filter(JiraConfigORM.id == 1).first()
    if not cfg:
        cfg = JiraConfigORM(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def _get_gl_cfg(db: Session) -> GitLabConfigORM:
    cfg = db.query(GitLabConfigORM).filter(GitLabConfigORM.id == 1).first()
    if not cfg:
        cfg = GitLabConfigORM(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def _jira_get(cfg, path: str, params: dict = None):
    import requests
    url = f"{cfg.base_url.rstrip('/')}/{path.lstrip('/')}"
    resp = requests.get(
        url, params=params or {},
        auth=(cfg.email, cfg.api_token),
        headers={"Accept": "application/json"},
        timeout=20,
    )
    if resp.status_code == 401:
        raise HTTPException(401, "Jira auth failed")
    if not resp.ok:
        raise HTTPException(resp.status_code, f"Jira error: {resp.text[:300]}")
    return resp.json()


def _gl_get(cfg, path: str, params: dict = None):
    import requests
    base = cfg.base_url.rstrip("/") if cfg.base_url else "https://gitlab.com"
    url = f"{base}/api/v4/{path.lstrip('/')}"
    resp = requests.get(
        url, params=params or {},
        headers={"PRIVATE-TOKEN": cfg.access_token, "Accept": "application/json"},
        timeout=20,
    )
    if resp.status_code == 401:
        raise HTTPException(401, "GitLab auth failed")
    if not resp.ok:
        raise HTTPException(resp.status_code, f"GitLab error: {resp.text[:200]}")
    return resp.json(), resp.headers


def _extract_jira_keys(text: str) -> list:
    """Extract Jira issue keys like ABC-123 from text."""
    return list(set(re.findall(r'\b([A-Z]+-\d+)\b', text or "")))


# ── Schemas ───────────────────────────────────────────────────────────────────
class SprintConfigIn(BaseModel):
    board_id:           Optional[str] = ""
    sprint_id:          Optional[str] = ""
    sprint_name:        Optional[str] = ""
    my_jira_email:      Optional[str] = ""
    my_gitlab_username: Optional[str] = ""


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("/config")
def get_config(db: Session = Depends(_db)):
    cfg = _get_cfg(db)
    return {
        "board_id":           cfg.board_id or "",
        "sprint_id":          cfg.sprint_id or "",
        "sprint_name":        cfg.sprint_name or "",
        "my_jira_email":      cfg.my_jira_email or "",
        "my_gitlab_username": cfg.my_gitlab_username or "",
    }


@router.post("/config")
def save_config(body: SprintConfigIn, db: Session = Depends(_db)):
    cfg = _get_cfg(db)
    if body.board_id is not None:
        cfg.board_id = body.board_id
    if body.sprint_id is not None:
        cfg.sprint_id = body.sprint_id
    if body.sprint_name is not None:
        cfg.sprint_name = body.sprint_name
    if body.my_jira_email is not None:
        cfg.my_jira_email = body.my_jira_email
    if body.my_gitlab_username is not None:
        cfg.my_gitlab_username = body.my_gitlab_username
    db.commit()
    _cache_bust()
    return {"ok": True}


@router.get("/boards")
def list_boards(db: Session = Depends(_db)):
    """List Jira boards (Software boards that have sprints)."""
    jira_cfg = _get_jira_cfg(db)
    if not jira_cfg.enabled or not jira_cfg.api_token:
        raise HTTPException(400, "Jira integration is not enabled")

    cached = _cache_get("boards")
    if cached:
        return cached

    data = _jira_get(jira_cfg, "rest/agile/1.0/board", {"type": "scrum", "maxResults": 50})
    boards = [
        {"id": str(b["id"]), "name": b.get("name", ""), "type": b.get("type", "")}
        for b in data.get("values", [])
    ]
    _cache_set("boards", boards)
    return boards


@router.get("/sprints")
def list_sprints(board_id: str = Query(...), db: Session = Depends(_db)):
    """List sprints for a Jira board."""
    jira_cfg = _get_jira_cfg(db)
    if not jira_cfg.enabled or not jira_cfg.api_token:
        raise HTTPException(400, "Jira integration is not enabled")

    cache_key = f"sprints_{board_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    # Get active + recently closed sprints
    sprints = []
    for state in ("active", "future", "closed"):
        try:
            data = _jira_get(jira_cfg, f"rest/agile/1.0/board/{board_id}/sprint",
                             {"state": state, "maxResults": 10})
            for s in data.get("values", []):
                sprints.append({
                    "id":         str(s["id"]),
                    "name":       s.get("name", ""),
                    "state":      s.get("state", ""),
                    "start_date": (s.get("startDate") or "")[:10],
                    "end_date":   (s.get("endDate") or "")[:10],
                    "goal":       s.get("goal", ""),
                })
        except HTTPException:
            pass

    _cache_set(cache_key, sprints)
    return sprints


@router.get("/board")
def sprint_board(db: Session = Depends(_db)):
    """Fetch sprint items with correlated GitLab MRs."""
    cached = _cache_get("board")
    if cached:
        return cached

    cfg      = _get_cfg(db)
    jira_cfg = _get_jira_cfg(db)
    gl_cfg   = _get_gl_cfg(db)

    if not jira_cfg.enabled or not jira_cfg.api_token:
        raise HTTPException(400, "Jira integration is not enabled")

    if not cfg.sprint_id:
        raise HTTPException(400, "No sprint configured — go to Sprint Settings and select a sprint")

    # ── Fetch sprint info ────────────────────────────────────────────────────
    sprint_info = {}
    try:
        s = _jira_get(jira_cfg, f"rest/agile/1.0/sprint/{cfg.sprint_id}")
        sprint_info = {
            "id":         str(s.get("id", "")),
            "name":       s.get("name", ""),
            "state":      s.get("state", ""),
            "start_date": (s.get("startDate") or "")[:10],
            "end_date":   (s.get("endDate") or "")[:10],
            "goal":       s.get("goal", ""),
        }
    except HTTPException:
        sprint_info = {"id": cfg.sprint_id, "name": cfg.sprint_name or cfg.sprint_id}

    # ── Fetch sprint issues ──────────────────────────────────────────────────
    fields = "summary,assignee,status,priority,issuetype,project,duedate,updated,created"
    all_issues = []
    start_at = 0
    while True:
        try:
            data = _jira_get(jira_cfg, f"rest/agile/1.0/sprint/{cfg.sprint_id}/issue", {
                "fields": fields, "maxResults": 100, "startAt": start_at
            })
        except HTTPException:
            break
        issues = data.get("issues", [])
        all_issues.extend(issues)
        total = data.get("total", 0)
        start_at += len(issues)
        if start_at >= min(total, 500) or not issues:
            break

    # ── Fetch GitLab MRs for correlation ────────────────────────────────────
    import urllib.parse
    all_gl_mrs = []
    merged_gl_mrs = []
    if gl_cfg.enabled and gl_cfg.access_token:
        raw_ids = json.loads(gl_cfg.project_ids or "[]")
        if not raw_ids:
            try:
                data, _ = _gl_get(gl_cfg, "projects", {"membership": True, "per_page": 50})
                raw_ids = [str(p["id"]) for p in data]
            except HTTPException:
                pass

        for pid in raw_ids[:20]:
            encoded = urllib.parse.quote(str(pid), safe="")
            try:
                proj, _ = _gl_get(gl_cfg, f"projects/{encoded}")
                # Open MRs
                open_mrs, _ = _gl_get(gl_cfg, f"projects/{encoded}/merge_requests", {
                    "state": "opened", "per_page": 100
                })
                for mr in open_mrs:
                    author = mr.get("author") or {}
                    reviewer_names = [r.get("username", "") for r in (mr.get("reviewers") or [])]
                    all_gl_mrs.append({
                        "id":            mr["iid"],
                        "title":         mr.get("title", ""),
                        "state":         "opened",
                        "draft":         mr.get("draft", mr.get("work_in_progress", False)),
                        "author":        author.get("name", ""),
                        "author_user":   author.get("username", ""),
                        "source_branch": mr.get("source_branch", ""),
                        "created_at":    (mr.get("created_at") or "")[:10],
                        "merged_at":     None,
                        "web_url":       mr.get("web_url", ""),
                        "project_name":  proj["name"],
                        "reviewers":     reviewer_names,
                        "upvotes":       mr.get("upvotes", 0),
                        "is_reviewed":   mr.get("upvotes", 0) > 0,
                    })
                # Recently merged MRs (last 50)
                merged_mrs, _ = _gl_get(gl_cfg, f"projects/{encoded}/merge_requests", {
                    "state": "merged", "per_page": 50, "order_by": "updated_at"
                })
                for mr in merged_mrs:
                    author = mr.get("author") or {}
                    merged_gl_mrs.append({
                        "id":            mr["iid"],
                        "title":         mr.get("title", ""),
                        "state":         "merged",
                        "draft":         False,
                        "author":        author.get("name", ""),
                        "author_user":   author.get("username", ""),
                        "source_branch": mr.get("source_branch", ""),
                        "created_at":    (mr.get("created_at") or "")[:10],
                        "merged_at":     (mr.get("merged_at") or "")[:10],
                        "web_url":       mr.get("web_url", ""),
                        "project_name":  proj["name"],
                        "reviewers":     [],
                        "upvotes":       0,
                        "is_reviewed":   True,
                    })
            except HTTPException:
                pass

    combined_mrs = all_gl_mrs + merged_gl_mrs

    # ── Build lookup: Jira key → list of matching MRs ────────────────────────
    def _matches_key(mr, jira_key: str) -> bool:
        key_lower = jira_key.lower()
        return (
            key_lower in mr["source_branch"].lower() or
            key_lower in mr["title"].lower()
        )

    # ── Assemble sprint items ────────────────────────────────────────────────
    items = []
    stats = {"total": 0, "done": 0, "in_progress": 0, "todo": 0,
             "with_mr": 0, "needs_review": 0, "merged": 0}

    for issue in all_issues:
        f        = issue.get("fields", {})
        status   = (f.get("status")    or {}).get("name", "")
        cat      = (f.get("status")    or {}).get("statusCategory", {}).get("key", "")
        priority = (f.get("priority")  or {}).get("name", "Medium")
        itype    = (f.get("issuetype") or {}).get("name", "")
        assignee = (f.get("assignee")  or {})
        jira_key = issue["key"]

        # Find matching MRs
        matching = [m for m in combined_mrs if _matches_key(m, jira_key)]
        # Prefer open over merged in display; merged as fallback
        open_mr   = next((m for m in matching if m["state"] == "opened"), None)
        merged_mr = next((m for m in matching if m["state"] == "merged"), None)
        mr_display = open_mr or merged_mr

        item = {
            "key":         jira_key,
            "summary":     f.get("summary", ""),
            "status":      status,
            "cat":         cat,
            "priority":    priority,
            "type":        itype,
            "assignee":    assignee.get("displayName", "Unassigned"),
            "due_date":    f.get("duedate"),
            "updated":     (f.get("updated") or "")[:10],
            "web_url":     f"{jira_cfg.base_url.rstrip('/')}/browse/{jira_key}",
            "mr":          mr_display,
        }
        items.append(item)

        stats["total"] += 1
        if cat == "done":
            stats["done"] += 1
        elif cat == "indeterminate":
            stats["in_progress"] += 1
        else:
            stats["todo"] += 1

        if mr_display:
            stats["with_mr"] += 1
            if mr_display["state"] == "merged":
                stats["merged"] += 1
            elif not mr_display["is_reviewed"] and not mr_display["draft"]:
                stats["needs_review"] += 1

    # Sort: in_progress first, then todo, then done
    order = {"indeterminate": 0, "new": 1, "done": 2}
    items.sort(key=lambda x: order.get(x["cat"], 1))

    result = {
        "sprint":       sprint_info,
        "items":        items,
        "stats":        stats,
        "last_fetched": datetime.utcnow().isoformat(),
    }

    _cache_set("board", result)
    return result


@router.post("/refresh")
def refresh_cache():
    _cache_bust()
    return {"ok": True}
