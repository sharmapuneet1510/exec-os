"""Team workload aggregation — local tasks, Jira issues, GitLab MRs."""

import json
import time
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.base import SessionLocal
from db.models import (
    TeamMemberORM, TaskORM, MockJiraIssueORM, MockGitLabMRORM,
    JiraConfigORM, GitLabConfigORM, AppJiraConfigORM, AppGitLabConfigORM
)


class TeamMemberCreate(BaseModel):
    name: str
    email: Optional[str] = None
    gitlab_username: Optional[str] = None
    role: Optional[str] = None
    max_concurrent_tasks: int = 8


class TeamMemberUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    gitlab_username: Optional[str] = None
    role: Optional[str] = None
    max_concurrent_tasks: Optional[int] = None
    is_active: Optional[bool] = None


router = APIRouter(prefix="/api/workload", tags=["workload"])

_cache: dict = {}
_CACHE_TTL = 60


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


# ── Jira HTTP helpers ─────────────────────────────────────────────────────────
def _jira_get(cfg: AppJiraConfigORM, path: str, params: dict = None):
    import requests, urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    url = f"{cfg.base_url.rstrip('/')}/rest/api/2/{path.lstrip('/')}"
    resp = requests.get(url, params=params or {},
        headers={"Authorization": f"Bearer {cfg.pat}", "Accept": "application/json",
                 "Content-Type": "application/json"},
        timeout=15, verify=False)
    if not resp.ok:
        return None
    return resp.json()


def _jira_search_all(cfg, jql: str, fields: str) -> list:
    all_issues, start_at = [], 0
    while True:
        data = _jira_get(cfg, "search", {"jql": jql, "fields": fields,
                                          "maxResults": 100, "startAt": start_at})
        if not data:
            break
        issues = data.get("issues", [])
        all_issues.extend(issues)
        total = data.get("total", 0)
        start_at += len(issues)
        if start_at >= min(total, 500) or not issues:
            break
    return all_issues


# ── GitLab HTTP helpers ───────────────────────────────────────────────────────
def _gl_get(cfg: AppGitLabConfigORM, path: str, params: dict = None):
    import requests
    base = (cfg.base_url or "https://gitlab.com").rstrip("/")
    url = f"{base}/api/v4/{path.lstrip('/')}"
    resp = requests.get(url, params=params or {},
        headers={"PRIVATE-TOKEN": cfg.access_token, "Accept": "application/json"},
        timeout=15)
    if not resp.ok:
        return None, {}
    return resp.json(), resp.headers


def _gl_all_mrs(cfg: AppGitLabConfigORM) -> list:
    import urllib.parse
    raw_ids = json.loads(cfg.project_ids or "[]")
    if not raw_ids:
        data, _ = _gl_get(cfg, "projects", {"membership": True, "per_page": 50})
        raw_ids = [str(p["id"]) for p in (data or [])]
    all_mrs = []
    for pid in raw_ids[:20]:
        encoded = urllib.parse.quote(str(pid), safe="")
        try:
            proj, _ = _gl_get(cfg, f"projects/{encoded}")
            mrs, _ = _gl_get(cfg, f"projects/{encoded}/merge_requests",
                              {"state": "opened", "per_page": 50, "order_by": "updated_at"})
            if not proj or not mrs:
                continue
            for mr in mrs:
                author = mr.get("author") or {}
                all_mrs.append({
                    "iid": mr["iid"],
                    "title": mr.get("title", ""),
                    "state": mr.get("state", "opened"),
                    "draft": mr.get("draft", False),
                    "author_user": author.get("username", ""),
                    "reviewers": [r.get("username", "") for r in (mr.get("reviewers") or [])],
                    "project_name": proj["name"],
                    "created_at": (mr.get("created_at") or "")[:10],
                    "web_url": mr.get("web_url", ""),
                })
        except Exception:
            pass
    return all_mrs


@router.get("/team")
def get_team_workload(app_id: str = Query(...), db: Session = Depends(_db)):
    """Return team workload: aggregated local tasks, real Jira issues, real GitLab MRs."""

    cache_key = f"workload_team_{app_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    team_members = db.query(TeamMemberORM).filter(TeamMemberORM.is_active == True).all()

    # ── Real Jira: one call for all members ────────────────────────────────
    jira_by_email: dict = {}
    jira_cfg = db.query(AppJiraConfigORM).filter(AppJiraConfigORM.application_id == app_id).first()
    if jira_cfg and jira_cfg.enabled and jira_cfg.pat and jira_cfg.base_url:
        emails = [m.email for m in team_members if m.email]
        if emails:
            quoted_emails = ", ".join(f'"{e}"' for e in emails)
            keys = json.loads(jira_cfg.project_keys or "[]")
            parts = []
            if keys:
                parts.append(f"project in ({', '.join(chr(34)+k+chr(34) for k in keys)})")
            parts.append('statusCategory != "Done"')
            parts.append(f'assignee in ({quoted_emails})')
            jql = " AND ".join(parts)
            fields = "summary,assignee,status,priority"
            for issue in _jira_search_all(jira_cfg, jql, fields):
                f = issue.get("fields", {})
                email = ((f.get("assignee") or {}).get("emailAddress") or "").lower()
                if email:
                    jira_by_email.setdefault(email, []).append({
                        "key": issue["key"],
                        "summary": f.get("summary", ""),
                        "status": (f.get("status") or {}).get("name", ""),
                        "priority": (f.get("priority") or {}).get("name", ""),
                    })

    # ── Real GitLab: one pass across all projects ───────────────────────────
    gl_by_username: dict = {}
    gl_cfg = db.query(AppGitLabConfigORM).filter(AppGitLabConfigORM.application_id == app_id).first()
    if gl_cfg and gl_cfg.enabled and gl_cfg.access_token:
        for mr in _gl_all_mrs(gl_cfg):
            for uname in set([mr["author_user"]] + mr["reviewers"]):
                if uname:
                    gl_by_username.setdefault(uname, []).append(mr)

    team_data = []
    overloaded_count = 0
    total_local = 0
    total_jira = 0
    total_mrs = 0

    for member in team_members:
        # Local tasks
        local_tasks = db.query(TaskORM).filter(
            TaskORM.assignee_id == member.member_id
        ).all()

        local_task_list = [
            {
                "task_id": t.task_id,
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "due_date": str(t.due_date) if t.due_date else None,
            }
            for t in local_tasks
        ]
        local_count = len(local_tasks)
        total_local += local_count

        # Real Jira issues via API
        jira_list = jira_by_email.get((member.email or "").lower(), [])
        jira_count = len(jira_list)
        total_jira += jira_count

        # Real GitLab MRs via API
        mr_list = gl_by_username.get(member.gitlab_username or "", [])
        mr_count = len(mr_list)
        total_mrs += mr_count

        # Calculate total and capacity
        total_active = local_count + jira_count + mr_count
        capacity_status = (
            "light" if total_active < 4
            else "moderate" if total_active < 8
            else "heavy"
        )

        if total_active >= member.max_concurrent_tasks:
            overloaded_count += 1

        team_data.append({
            "member_id": member.member_id,
            "name": member.name,
            "email": member.email,
            "gitlab_username": member.gitlab_username,
            "role": member.role,
            "max_concurrent_tasks": member.max_concurrent_tasks,
            "workload": {
                "local_tasks": local_task_list,
                "local_count": local_count,
                "jira_issues": jira_list,
                "jira_count": jira_count,
                "gitlab_mrs": mr_list,
                "mr_count": mr_count,
                "total_active": total_active,
                "capacity_status": capacity_status,
            }
        })

    result = {
        "team": sorted(team_data, key=lambda x: -x["workload"]["total_active"]),
        "summary": {
            "total_members": len(team_members),
            "overloaded_count": overloaded_count,
            "total_local_tasks": total_local,
            "total_jira_issues": total_jira,
            "total_mrs": total_mrs,
            "last_updated": datetime.utcnow().isoformat(),
        }
    }

    _cache_set(cache_key, result)
    return result


@router.get("/team/members")
def get_team_members(db: Session = Depends(_db)):
    """Return list of all team members."""
    members = db.query(TeamMemberORM).all()
    return [
        {
            "member_id": m.member_id,
            "name": m.name,
            "email": m.email,
            "gitlab_username": m.gitlab_username,
            "role": m.role,
            "max_concurrent_tasks": m.max_concurrent_tasks,
            "is_active": m.is_active,
        }
        for m in members
    ]


@router.post("/team/members")
def create_team_member(body: TeamMemberCreate, db: Session = Depends(_db)):
    """Create new team member."""
    member = TeamMemberORM(
        name=body.name,
        email=body.email,
        gitlab_username=body.gitlab_username,
        role=body.role,
        max_concurrent_tasks=body.max_concurrent_tasks,
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    _cache_bust()

    return {
        "member_id": member.member_id,
        "name": member.name,
        "email": member.email,
    }


@router.patch("/team/members/{member_id}")
def update_team_member(member_id: str, body: TeamMemberUpdate, db: Session = Depends(_db)):
    """Update team member."""
    member = db.query(TeamMemberORM).filter(TeamMemberORM.member_id == member_id).first()
    if not member:
        raise HTTPException(404, "Team member not found")

    if body.name is not None:
        member.name = body.name
    if body.email is not None:
        member.email = body.email
    if body.role is not None:
        member.role = body.role
    if body.max_concurrent_tasks is not None:
        member.max_concurrent_tasks = body.max_concurrent_tasks
    if body.is_active is not None:
        member.is_active = body.is_active

    db.commit()
    db.refresh(member)

    _cache_bust()

    return {"status": "updated", "member_id": member.member_id}


@router.delete("/team/members/{member_id}")
def delete_team_member(member_id: str, db: Session = Depends(_db)):
    """Delete team member (tasks get unassigned)."""
    member = db.query(TeamMemberORM).filter(TeamMemberORM.member_id == member_id).first()
    if not member:
        raise HTTPException(404, "Team member not found")

    # Unassign tasks
    db.query(TaskORM).filter(TaskORM.assignee_id == member_id).update(
        {TaskORM.assignee_id: None}
    )

    db.delete(member)
    db.commit()

    _cache_bust()

    return {"status": "deleted", "member_id": member_id}


@router.post("/team/refresh")
def refresh_workload_cache():
    """Manually bust cache and reload data."""
    _cache_bust()
    return {"ok": True}
