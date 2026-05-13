"""My Book of Work — aggregates local tasks, Jira issues, and MRs for a user."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
import json

from db.base import get_db
from db.models import TaskORM, TeamMemberORM, MockJiraIssueORM, MockGitLabMRORM

router = APIRouter(prefix="/api/my-work", tags=["my-work"])


def _task_out(t: TaskORM) -> dict:
    today = date.today()
    is_overdue = bool(t.due_date and t.due_date < today and t.status not in ("done", "cancelled"))
    return {
        "task_id":    t.task_id,
        "title":      t.title,
        "status":     t.status,
        "priority":   t.priority,
        "due_date":   str(t.due_date) if t.due_date else None,
        "is_overdue": is_overdue,
        "project_id": t.project_id,
    }


def _jira_out(j: MockJiraIssueORM) -> dict:
    return {
        "key":         j.key,
        "summary":     j.summary,
        "status":      j.status,
        "priority":    j.priority,
        "project_key": j.project_key,
    }


def _mr_out(m: MockGitLabMRORM, is_review: bool = False) -> dict:
    return {
        "iid":       m.iid,
        "title":     m.title,
        "state":     m.state,
        "author":    m.author_username,
        "project":   m.project_path,
        "is_review": is_review,
    }


@router.get("")
def my_work(
    jira_email: str = Query("", description="Jira email to filter issues"),
    gitlab_username: str = Query("", description="GitLab username to filter MRs"),
    db: Session = Depends(get_db),
):
    """Returns local tasks, Jira issues, and MRs for the current user."""
    tasks = db.query(TaskORM).filter(
        TaskORM.status.notin_(["done", "cancelled"])
    ).order_by(TaskORM.due_date).all()

    jira_issues = []
    if jira_email:
        jira_issues = db.query(MockJiraIssueORM).filter(
            MockJiraIssueORM.assignee_email == jira_email
        ).all()

    mrs = []
    if gitlab_username:
        all_mrs = db.query(MockGitLabMRORM).filter(
            MockGitLabMRORM.state == "opened"
        ).all()
        for m in all_mrs:
            try:
                reviewers = json.loads(m.reviewers or "[]")
            except (json.JSONDecodeError, TypeError):
                reviewers = []
            if m.author_username == gitlab_username or gitlab_username in reviewers:
                is_review = gitlab_username in reviewers and m.author_username != gitlab_username
                mrs.append(_mr_out(m, is_review=is_review))

    return {
        "tasks": [_task_out(t) for t in tasks],
        "jira":  [_jira_out(j) for j in jira_issues],
        "mrs":   mrs,
    }


@router.get("/team/{member_id}")
def team_member_work(member_id: str, db: Session = Depends(get_db)):
    """Returns tasks, Jira issues, and MRs for a specific team member."""
    member = db.query(TeamMemberORM).filter(TeamMemberORM.member_id == member_id).first()
    if not member:
        return {"tasks": [], "jira": [], "mrs": [], "member": None}

    tasks = db.query(TaskORM).filter(
        TaskORM.assignee_id == member_id,
        TaskORM.status.notin_(["done", "cancelled"])
    ).order_by(TaskORM.due_date).all()

    jira_issues = []
    if member.email:
        jira_issues = db.query(MockJiraIssueORM).filter(
            MockJiraIssueORM.assignee_email == member.email
        ).all()

    mrs = []
    if member.gitlab_username:
        all_mrs = db.query(MockGitLabMRORM).filter(
            MockGitLabMRORM.state == "opened"
        ).all()
        for m in all_mrs:
            try:
                reviewers = json.loads(m.reviewers or "[]")
            except (json.JSONDecodeError, TypeError):
                reviewers = []
            if m.author_username == member.gitlab_username or member.gitlab_username in reviewers:
                is_review = member.gitlab_username in reviewers and m.author_username != member.gitlab_username
                mrs.append(_mr_out(m, is_review=is_review))

    return {
        "member": {
            "member_id": member.member_id,
            "name":      member.name,
            "email":     member.email or "",
            "role":      member.role or "",
        },
        "tasks": [_task_out(t) for t in tasks],
        "jira":  [_jira_out(j) for j in jira_issues],
        "mrs":   mrs,
    }
