"""My Hub — personal dashboard: my Jira issues + my GitLab MRs + book of work."""

import json, time, logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.base import SessionLocal
from db.models import SprintConfigORM, JiraConfigORM, GitLabConfigORM

log = logging.getLogger("execos.team")
router = APIRouter(prefix="/api/team", tags=["team"])

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


def _get_sprint_cfg(db: Session) -> SprintConfigORM:
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
    url = f"{cfg.base_url.rstrip('/')}/rest/api/3/{path.lstrip('/')}"
    resp = requests.get(
        url, params=params or {},
        headers={
            "Authorization": f"Bearer {cfg.pat}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=15,
    )
    if resp.status_code == 401:
        raise HTTPException(401, "Jira auth failed — check PAT and permissions")
    if resp.status_code == 403:
        raise HTTPException(403, "Jira returned 403 — PAT may lack permissions")
    if not resp.ok:
        raise HTTPException(resp.status_code, f"Jira error: {resp.text[:200]}")
    return resp.json()


def _gl_get(cfg, path: str, params: dict = None):
    import requests
    base = cfg.base_url.rstrip("/") if cfg.base_url else "https://gitlab.com"
    url = f"{base}/api/v4/{path.lstrip('/')}"
    resp = requests.get(
        url, params=params or {},
        headers={"PRIVATE-TOKEN": cfg.access_token, "Accept": "application/json"},
        timeout=15,
    )
    if resp.status_code == 401:
        raise HTTPException(401, "GitLab auth failed")
    if not resp.ok:
        raise HTTPException(resp.status_code, f"GitLab error: {resp.text[:200]}")
    return resp.json(), resp.headers


def _jira_search_all(cfg, jql: str, fields: str) -> list:
    all_issues = []
    start_at = 0
    while True:
        data = _jira_get(cfg, "search", {
            "jql": jql, "fields": fields,
            "maxResults": 100, "startAt": start_at,
        })
        issues = data.get("issues", [])
        all_issues.extend(issues)
        total = data.get("total", 0)
        start_at += len(issues)
        if start_at >= min(total, 500) or not issues:
            break
    return all_issues


def _gl_all_mrs(cfg) -> list:
    """Fetch all open MRs across configured projects."""
    import urllib.parse
    raw_ids = json.loads(cfg.project_ids or "[]")
    if not raw_ids:
        data, _ = _gl_get(cfg, "projects", {"membership": True, "per_page": 50})
        raw_ids = [str(p["id"]) for p in data]

    all_mrs = []
    for pid in raw_ids[:20]:
        encoded = urllib.parse.quote(str(pid), safe="")
        try:
            proj, _ = _gl_get(cfg, f"projects/{encoded}")
            mrs, _ = _gl_get(cfg, f"projects/{encoded}/merge_requests", {
                "state": "opened", "per_page": 50, "order_by": "updated_at"
            })
            for mr in mrs:
                author = mr.get("author") or {}
                reviewer_names = [r.get("username", "") for r in (mr.get("reviewers") or [])]
                all_mrs.append({
                    "id":            mr["iid"],
                    "global_id":     mr["id"],
                    "title":         mr.get("title", ""),
                    "state":         mr.get("state", "opened"),
                    "draft":         mr.get("draft", mr.get("work_in_progress", False)),
                    "author":        author.get("name", ""),
                    "author_user":   author.get("username", ""),
                    "author_avatar": author.get("avatar_url"),
                    "source_branch": mr.get("source_branch", ""),
                    "target_branch": mr.get("target_branch", ""),
                    "created_at":    (mr.get("created_at") or "")[:10],
                    "updated_at":    (mr.get("updated_at") or "")[:10],
                    "merged_at":     (mr.get("merged_at") or "")[:10] if mr.get("merged_at") else None,
                    "web_url":       mr.get("web_url", ""),
                    "project_name":  proj["name"],
                    "project_path":  proj.get("path_with_namespace", ""),
                    "reviewers":     reviewer_names,
                    "upvotes":       mr.get("upvotes", 0),
                    "changes_count": str(mr.get("changes_count") or ""),
                    "is_reviewed":   (mr.get("upvotes", 0) > 0),
                })
        except HTTPException:
            pass
    return all_mrs


@router.get("/me")
def my_dashboard(db: Session = Depends(_db)):
    """Personal dashboard: my Jira issues by category + my open GitLab MRs."""
    cached = _cache_get("me")
    if cached:
        return cached

    sprint_cfg = _get_sprint_cfg(db)
    jira_cfg   = _get_jira_cfg(db)
    gl_cfg     = _get_gl_cfg(db)

    my_jira_email      = sprint_cfg.my_jira_email or ""
    my_gitlab_username = sprint_cfg.my_gitlab_username or ""

    result = {
        "my_jira_email":      my_jira_email,
        "my_gitlab_username": my_gitlab_username,
        "jira_enabled":       jira_cfg.enabled and bool(jira_cfg.pat),
        "gitlab_enabled":     gl_cfg.enabled and bool(gl_cfg.access_token),
        "jira":               None,
        "my_mrs":             [],
        "needs_review":       [],
        "book_of_work":       [],
    }

    # ── Jira: my assigned issues ──────────────────────────────────────────────
    if jira_cfg.enabled and jira_cfg.pat:
        try:
            # Build JQL: my assigned open issues
            keys = json.loads(jira_cfg.project_keys or "[]")
            project_filter = ""
            if keys:
                quoted = ", ".join(f'"{k}"' for k in keys)
                project_filter = f"project in ({quoted}) AND "
            jql = f'{project_filter}assignee = currentUser() AND statusCategory != "Done" ORDER BY updated DESC'

            fields = "summary,assignee,status,priority,issuetype,project,created,updated,duedate"
            issues = _jira_search_all(jira_cfg, jql, fields)

            by_status:   dict = {}
            by_type:     dict = {}
            by_priority: dict = {}
            in_progress, in_review, bugs, reopened, todos, all_list = [], [], [], [], [], []

            for issue in issues:
                f = issue.get("fields", {})
                status   = (f.get("status")    or {}).get("name", "")
                cat      = (f.get("status")    or {}).get("statusCategory", {}).get("key", "")
                itype    = (f.get("issuetype") or {}).get("name", "")
                priority = (f.get("priority")  or {}).get("name", "Medium")

                rec = {
                    "key":      issue["key"],
                    "summary":  f.get("summary", ""),
                    "status":   status,
                    "cat":      cat,
                    "type":     itype,
                    "priority": priority,
                    "project":  (f.get("project") or {}).get("key", ""),
                    "due_date": f.get("duedate"),
                    "updated":  (f.get("updated") or "")[:10],
                    "web_url":  f"{jira_cfg.base_url.rstrip('/')}/browse/{issue['key']}",
                }
                all_list.append(rec)

                # Group by status
                by_status[status] = by_status.get(status, 0) + 1
                by_type[itype]    = by_type.get(itype, 0) + 1
                by_priority[priority] = by_priority.get(priority, 0) + 1

                sl = status.lower()
                if cat == "indeterminate" or "progress" in sl:
                    in_progress.append(rec)
                if "review" in sl or "review" in itype.lower():
                    in_review.append(rec)
                if itype.lower() == "bug":
                    bugs.append(rec)
                if "reopen" in sl:
                    reopened.append(rec)
                if cat == "new" or "todo" in sl or "backlog" in sl:
                    todos.append(rec)

            result["jira"] = {
                "total":       len(issues),
                "in_progress": in_progress,
                "in_review":   in_review,
                "bugs":        bugs,
                "reopened":    reopened,
                "todos":       todos,
                "all":         all_list,
                "by_status":   by_status,
                "by_type":     by_type,
                "by_priority": by_priority,
            }
        except HTTPException as e:
            result["jira"] = {"error": str(e.detail)}
        except Exception as e:
            result["jira"] = {"error": str(e)}

    # ── GitLab: my open MRs + MRs needing my review ──────────────────────────
    if gl_cfg.enabled and gl_cfg.access_token:
        try:
            all_mrs = _gl_all_mrs(gl_cfg)

            # My authored MRs
            if my_gitlab_username:
                result["my_mrs"] = [m for m in all_mrs if m["author_user"] == my_gitlab_username]
            else:
                result["my_mrs"] = all_mrs

            # MRs needing my review (I'm listed as reviewer)
            if my_gitlab_username:
                result["needs_review"] = [
                    m for m in all_mrs
                    if my_gitlab_username in m["reviewers"] and not m["is_reviewed"]
                ]

            # Book of work: unreviewed non-draft MRs older than 1 day
            result["book_of_work"] = [
                m for m in all_mrs
                if not m["draft"] and not m["is_reviewed"]
                and (my_gitlab_username in m["reviewers"] if my_gitlab_username else True)
            ]
        except HTTPException as e:
            result["my_mrs"] = [{"error": str(e.detail)}]
        except Exception as e:
            result["my_mrs"] = [{"error": str(e)}]

    _cache_set("me", result)
    return result


@router.post("/refresh")
def refresh_cache():
    _cache_bust()
    return {"ok": True}
