"""My Book of Work — aggregates local tasks, real Jira issues, and real GitLab MRs."""

import json
import logging
import urllib.parse
import urllib3

import requests
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date

from db.base import get_db
from db.models import TaskORM, JiraConfigORM, AppGitLabConfigORM, SprintConfigORM

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger("execos.my_work")
router = APIRouter(prefix="/api/my-work", tags=["my-work"])

def _headers_jira(pat: str) -> dict:
    return {"Authorization": f"Bearer {pat}", "Accept": "application/json", "Content-Type": "application/json"}


def _headers_gl(tok: str) -> dict:
    return {"PRIVATE-TOKEN": tok, "Accept": "application/json"}


def _get_sprint_cfg(db: Session) -> SprintConfigORM:
    cfg = db.query(SprintConfigORM).first()
    if not cfg:
        cfg = SprintConfigORM(id=1)
        db.add(cfg)
        db.commit()
    return cfg


def _get_jira_cfg(db: Session) -> JiraConfigORM:
    cfg = db.query(JiraConfigORM).first()
    if not cfg:
        cfg = JiraConfigORM(id=1)
        db.add(cfg)
        db.commit()
    return cfg


def _get_gl_configs(db: Session) -> list:
    return db.query(AppGitLabConfigORM).filter(AppGitLabConfigORM.enabled == True).all()


def _task_out(t: TaskORM) -> dict:
    today = date.today()
    return {
        "task_id":    t.task_id,
        "title":      t.title,
        "status":     t.status,
        "priority":   t.priority,
        "due_date":   str(t.due_date) if t.due_date else None,
        "is_overdue": bool(t.due_date and t.due_date < today and t.status not in ("done", "cancelled")),
        "project_id": t.project_id,
    }


@router.get("")
def my_work(db: Session = Depends(get_db)):
    """Personal work view: real local tasks + real Jira issues + real GitLab MRs."""
    sprint_cfg = _get_sprint_cfg(db)
    jira_cfg   = _get_jira_cfg(db)
    gl_cfgs    = _get_gl_configs(db)

    my_email  = sprint_cfg.my_jira_email or ""
    my_gitlab = sprint_cfg.my_gitlab_username or ""

    local_tasks = (
        db.query(TaskORM)
        .filter(TaskORM.status.notin_(["done", "cancelled"]))
        .order_by(TaskORM.due_date)
        .all()
    )

    jira_issues = []
    jira_error  = None
    if jira_cfg.enabled and jira_cfg.pat:
        jql = 'assignee = currentUser() AND statusCategory != "Done" ORDER BY updated DESC'
        try:
            resp = requests.get(
                f"{jira_cfg.base_url.rstrip('/')}/rest/api/2/search",
                headers=_headers_jira(jira_cfg.pat),
                params={
                    "jql":        jql,
                    "maxResults": 100,
                    "fields":     "summary,status,priority,issuetype,project,duedate,updated",
                },
                timeout=15,
                verify=False,
            )
            if resp.ok:
                for issue in resp.json().get("issues", []):
                    f = issue.get("fields", {}) or {}
                    jira_issues.append({
                        "key":      issue["key"],
                        "summary":  f.get("summary", ""),
                        "status":   (f.get("status")    or {}).get("name", ""),
                        "priority": (f.get("priority")  or {}).get("name", ""),
                        "type":     (f.get("issuetype") or {}).get("name", ""),
                        "project":  (f.get("project")   or {}).get("key", ""),
                        "due_date": f.get("duedate"),
                        "updated":  (f.get("updated")   or "")[:10],
                        "web_url":  f"{jira_cfg.base_url.rstrip('/')}/browse/{issue['key']}",
                    })
            else:
                jira_error = f"Jira returned {resp.status_code}"
        except Exception as exc:
            log.warning("Jira fetch error: %s", exc)
            jira_error = str(exc)

    mrs = []
    gl_errors = []
    if my_gitlab and gl_cfgs:
        for gl_cfg in gl_cfgs:
            if not gl_cfg.access_token:
                continue
            raw_ids = json.loads(gl_cfg.project_ids or "[]")
            base    = gl_cfg.base_url.rstrip("/")
            for pid in raw_ids[:15]:
                encoded = urllib.parse.quote(str(pid), safe="")
                try:
                    resp = requests.get(
                        f"{base}/api/v4/projects/{encoded}/merge_requests",
                        headers=_headers_gl(gl_cfg.access_token),
                        params={
                            "state":           "opened",
                            "author_username": my_gitlab,
                            "per_page":        50,
                            "order_by":        "updated_at",
                        },
                        timeout=10,
                        verify=False,
                    )
                    if resp.ok:
                        for mr in resp.json():
                            mrs.append({
                                "iid":           mr["iid"],
                                "title":         mr.get("title", ""),
                                "state":         mr.get("state", "opened"),
                                "draft":         mr.get("draft", mr.get("work_in_progress", False)),
                                "target_branch": mr.get("target_branch", ""),
                                "web_url":       mr.get("web_url", ""),
                                "updated_at":    (mr.get("updated_at") or "")[:10],
                                "project":       str(pid),
                                "has_conflicts": mr.get("has_conflicts", False),
                            })
                except Exception as exc:
                    log.warning("GitLab MR fetch error for %s: %s", pid, exc)
                    gl_errors.append(f"{pid}: {exc}")

    return {
        "my_jira_email":      my_email,
        "my_gitlab_username": my_gitlab,
        "tasks":              [_task_out(t) for t in local_tasks],
        "jira":               jira_issues,
        "mrs":                mrs,
        **({"error": jira_error} if jira_error else {}),
        **({"gl_errors": gl_errors} if gl_errors else {}),
    }


@router.get("/team/{member_id}")
def team_member_work(member_id: str, db: Session = Depends(get_db)):
    """Local tasks for a specific team member."""
    from db.models import TeamMemberORM
    member = db.query(TeamMemberORM).filter(TeamMemberORM.member_id == member_id).first()
    if not member:
        return {"tasks": [], "jira": [], "mrs": [], "member": None}

    tasks = (
        db.query(TaskORM)
        .filter(TaskORM.assignee_id == member_id, TaskORM.status.notin_(["done", "cancelled"]))
        .order_by(TaskORM.due_date)
        .all()
    )
    return {
        "member": {
            "member_id": member.member_id,
            "name":      member.name,
            "email":     member.email or "",
            "role":      member.role or "",
        },
        "tasks": [_task_out(t) for t in tasks],
        "jira":  [],
        "mrs":   [],
    }
