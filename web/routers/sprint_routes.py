"""Sprint Board — configure sprint, fetch items, correlate GitLab MRs."""

import json, time, logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.base import SessionLocal
from db.models import AppSprintConfigORM, JiraConfigORM, AppGitLabConfigORM, TeamMemberORM

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


def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_cfg(app_id: str, db: Session) -> AppSprintConfigORM:
    cfg = db.query(AppSprintConfigORM).filter(AppSprintConfigORM.application_id == app_id).first()
    if not cfg:
        raise HTTPException(404, "Sprint config not found for this application — configure it in Settings")
    return cfg


def _get_jira_cfg(db: Session) -> JiraConfigORM:
    cfg = db.query(JiraConfigORM).first()
    if not cfg or not cfg.enabled or not cfg.pat:
        raise HTTPException(400, "Jira integration is not enabled in Settings")
    return cfg


def _get_gl_cfg(app_id: str, db: Session) -> AppGitLabConfigORM:
    cfg = db.query(AppGitLabConfigORM).filter(AppGitLabConfigORM.application_id == app_id).first()
    if not cfg:
        raise HTTPException(404, "GitLab config not found for this application")
    return cfg


def _jira_get(cfg, path: str, params: dict = None):
    import requests
    url = f"{cfg.base_url.rstrip('/')}/{path.lstrip('/')}"
    resp = requests.get(
        url, params=params or {},
        headers={
            "Authorization": f"Bearer {cfg.pat}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        verify=False,
        timeout=20,
    )
    if resp.status_code == 401:
        raise HTTPException(401, "Jira auth failed — check PAT and permissions")
    if resp.status_code == 403:
        raise HTTPException(403, "Jira returned 403 — PAT may lack permissions")
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


def _auto_create_team_from_jira(issues: list, db: Session):
    """Extract assignees from Jira issues and create team members if they don't exist."""
    for issue in issues:
        assignee = (issue.get("fields", {}) or {}).get("assignee") or {}
        email = (assignee.get("emailAddress") or "").lower()
        name = assignee.get("displayName", "")

        if not email:
            continue

        existing = db.query(TeamMemberORM).filter(TeamMemberORM.email == email).first()
        if not existing:
            member = TeamMemberORM(
                name=name or email.split('@')[0],
                email=email,
                role="Engineer",
                is_active=True,
                max_concurrent_tasks=8
            )
            db.add(member)

    db.commit()


def _extract_pr_from_jira_links(issue: dict) -> dict | None:
    """Extract PR/MR info from Jira issue links (GitHub/GitLab PRs linked in Jira)."""
    issuelinks = (issue.get("fields", {}) or {}).get("issuelinks") or []

    for link in issuelinks:
        link_type = (link.get("type") or {}).get("name", "").lower()
        # Look for PR/MR related link types
        if "pull request" in link_type or "relates to" in link_type or "blocks" in link_type:
            summary = link.get("inwardIssue", {}).get("key", "") or link.get("outwardIssue", {}).get("key", "")
            url = link.get("inwardIssue", {}).get("self", "") or link.get("outwardIssue", {}).get("self", "")

            # Check if it's a PR link (contains /pull/ or /merge_requests/)
            if "/pull/" in url or "/merge_requests/" in url:
                title = link.get("inwardIssue", {}).get("fields", {}).get("summary", "") or \
                        link.get("outwardIssue", {}).get("fields", {}).get("summary", "") or summary
                return {
                    "title": title,
                    "web_url": url,
                    "state": "linked",
                    "draft": False,
                }

    return None


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("/boards")
def list_boards(app_id: str = Query(...), db: Session = Depends(_db)):
    """List Jira boards (Software boards that have sprints)."""
    jira_cfg = _get_jira_cfg(db)

    cached = _cache_get(f"boards_{app_id}")
    if cached:
        return cached

    data = _jira_get(jira_cfg, "rest/agile/1.0/board", {"type": "scrum", "maxResults": 50})
    boards = [
        {"id": str(b["id"]), "name": b.get("name", ""), "type": b.get("type", "")}
        for b in data.get("values", [])
    ]
    _cache_set(f"boards_{app_id}", boards)
    return boards


@router.get("/sprints")
def list_sprints(app_id: str = Query(...), board_id: str = Query(...), db: Session = Depends(_db)):
    """List sprints for a Jira board."""
    jira_cfg = _get_jira_cfg(db)

    cache_key = f"sprints_{app_id}_{board_id}"
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
def sprint_board(app_id: str = Query(...), db: Session = Depends(_db)):
    """Fetch sprint items with correlated GitLab MRs."""
    cached = _cache_get(f"board_{app_id}")
    if cached:
        return cached

    cfg      = _get_cfg(app_id, db)
    jira_cfg = _get_jira_cfg(db)
    try:
        gl_cfg = _get_gl_cfg(app_id, db)
    except HTTPException:
        gl_cfg = None

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
    fields = "summary,assignee,status,priority,issuetype,project,duedate,updated,created,issuelinks"
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

    # Auto-create team members from Jira assignees
    _auto_create_team_from_jira(all_issues, db)

    # ── Fetch GitLab MRs for correlation ────────────────────────────────────
    import urllib.parse
    all_gl_mrs = []
    merged_gl_mrs = []
    if gl_cfg and gl_cfg.enabled and gl_cfg.access_token:
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

        # Check for PR linked directly in Jira first
        mr_display = _extract_pr_from_jira_links(issue)

        # If no Jira PR link, try matching against GitLab MRs
        if not mr_display:
            matching = [m for m in combined_mrs if _matches_key(m, jira_key)]
            # Prefer open over merged in display; merged as fallback
            open_mr   = next((m for m in matching if m["state"] == "opened"), None)
            merged_mr = next((m for m in matching if m["state"] == "merged"), None)
            mr_display = open_mr or merged_mr

        project_name = (f.get("project") or {}).get("key", "")
        item = {
            "key":         jira_key,
            "project":     project_name,
            "type":        itype,
            "summary":     f.get("summary", ""),
            "status":      status,
            "cat":         cat,
            "priority":    priority,
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
            elif mr_display.get("is_reviewed") is False and not mr_display.get("draft", False):
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

    _cache_set(f"board_{app_id}", result)
    return result


@router.post("/refresh")
def refresh_cache(app_id: str = Query(...)):
    for key in (f"board_{app_id}", f"boards_{app_id}"):
        _cache.pop(key, None)
    # Also clear any sprints keys for this app
    for key in list(_cache.keys()):
        if key.startswith(f"sprints_{app_id}"):
            _cache.pop(key, None)
    return {"ok": True}
