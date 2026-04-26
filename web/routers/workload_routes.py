"""Team workload aggregation — local tasks, Jira issues, GitLab MRs."""

import json
import time
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.base import SessionLocal
from db.models import (
    TeamMemberORM, TaskORM, MockJiraIssueORM, MockGitLabMRORM,
    JiraConfigORM, GitLabConfigORM, AppJiraConfigORM, AppGitLabConfigORM
)

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


@router.get("/team")
def get_team_workload(app_id: str = Query(...), db: Session = Depends(_db)):
    """Return team workload: aggregated local tasks, Jira issues, MRs."""

    cache_key = f"workload_team_{app_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    # Fetch all team members
    team_members = db.query(TeamMemberORM).filter(TeamMemberORM.is_active == True).all()

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

        # Mock Jira issues (or real Jira if configured)
        jira_issues = db.query(MockJiraIssueORM).filter(
            MockJiraIssueORM.assignee_email == member.email
        ).all()

        jira_list = [
            {
                "key": i.key,
                "summary": i.summary,
                "status": i.status,
                "priority": i.priority,
            }
            for i in jira_issues
        ]
        jira_count = len(jira_issues)
        total_jira += jira_count

        # Mock GitLab MRs (or real GitLab if configured)
        # Match by author_username or in reviewers
        mrs = db.query(MockGitLabMRORM).filter(
            (MockGitLabMRORM.author_username == member.gitlab_username) |
            (MockGitLabMRORM.reviewers.like(f'%{member.gitlab_username}%'))
        ).all()

        mr_list = [
            {
                "iid": m.iid,
                "title": m.title,
                "state": m.state,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in mrs
        ]
        mr_count = len(mrs)
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
def create_team_member(body: dict, db: Session = Depends(_db)):
    """Create new team member."""
    member = TeamMemberORM(
        name=body.get("name"),
        email=body.get("email"),
        gitlab_username=body.get("gitlab_username"),
        role=body.get("role"),
        max_concurrent_tasks=body.get("max_concurrent_tasks", 8),
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
def update_team_member(member_id: str, body: dict, db: Session = Depends(_db)):
    """Update team member."""
    member = db.query(TeamMemberORM).filter(TeamMemberORM.member_id == member_id).first()
    if not member:
        raise HTTPException(404, "Team member not found")

    if "name" in body:
        member.name = body["name"]
    if "email" in body:
        member.email = body["email"]
    if "role" in body:
        member.role = body["role"]
    if "max_concurrent_tasks" in body:
        member.max_concurrent_tasks = body["max_concurrent_tasks"]
    if "is_active" in body:
        member.is_active = body["is_active"]

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
