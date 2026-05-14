"""Entity comments — fetch from Jira + store local comments for issues and tasks."""

import json, logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import SessionLocal
from db.models import EntityCommentORM, JiraConfigORM, AppJiraConfigORM, TaskORM, TeamMemberORM

log = logging.getLogger("execos.comments")
router = APIRouter(prefix="/api/entities", tags=["entity-comments"])


def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CommentIn(BaseModel):
    text: str


def _jira_get(cfg, path: str, params: dict = None):
    """Helper to fetch from Jira API."""
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
    if not resp.ok:
        raise HTTPException(resp.status_code, f"Jira error: {resp.text[:300]}")
    return resp.json()


@router.get("/{entity_type}/{entity_id}/comments")
def get_entity_comments(entity_type: str, entity_id: str, db: Session = Depends(_db)):
    """Fetch comments: Jira comments (for issues) + local comments."""
    if entity_type not in ("issue", "task"):
        raise HTTPException(400, "Invalid entity_type. Use 'issue' or 'task'")

    comments = []

    # ── Fetch Jira comments (only for issues) ────────────────────────────────
    if entity_type == "issue":
        jira_cfg = db.query(JiraConfigORM).first()
        if jira_cfg and jira_cfg.enabled and jira_cfg.pat:
            try:
                data = _jira_get(jira_cfg, f"rest/api/2/issue/{entity_id}", {
                    "fields": "comment"
                })
                jira_comments = data.get("fields", {}).get("comment", {}).get("comments", [])

                for jira_comment in jira_comments:
                    author = jira_comment.get("author", {})
                    comments.append({
                        "id": jira_comment.get("id", ""),
                        "text": jira_comment.get("body", ""),
                        "author": author.get("displayName", "Unknown"),
                        "author_email": author.get("emailAddress", ""),
                        "created_at": (jira_comment.get("created", ""))[:10],
                        "is_external": True,
                        "is_editable": False,
                    })
            except Exception as e:
                log.warning(f"Failed to fetch Jira comments for {entity_id}: {e}")

    # ── Fetch local comments ─────────────────────────────────────────────────
    local_comments = db.query(EntityCommentORM).filter(
        EntityCommentORM.entity_type == entity_type,
        EntityCommentORM.entity_id == entity_id,
        EntityCommentORM.is_external == False
    ).order_by(EntityCommentORM.created_at.desc()).all()

    for comment in local_comments:
        comments.append({
            "id": comment.comment_id,
            "text": comment.text,
            "author": comment.author_name or comment.author_email.split('@')[0],
            "author_email": comment.author_email,
            "created_at": (comment.created_at.isoformat())[:10],
            "is_external": False,
            "is_editable": True,
        })

    # Sort by created_at descending
    comments.sort(key=lambda x: x["created_at"], reverse=True)

    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "comments": comments,
        "total": len(comments),
    }


@router.post("/{entity_type}/{entity_id}/comments")
def add_comment(
    entity_type: str,
    entity_id: str,
    body: CommentIn,
    author_email: str = Query(...),
    author_name: str = Query(default=""),
    db: Session = Depends(_db)
):
    """Add a local comment."""
    if entity_type not in ("issue", "task"):
        raise HTTPException(400, "Invalid entity_type. Use 'issue' or 'task'")

    if not body.text or not body.text.strip():
        raise HTTPException(400, "Comment text cannot be empty")

    # Validate that task exists if adding comment to task
    if entity_type == "task":
        task = db.query(TaskORM).filter(TaskORM.task_id == entity_id).first()
        if not task:
            raise HTTPException(404, "Task not found")

    comment = EntityCommentORM(
        entity_type=entity_type,
        entity_id=entity_id,
        author_email=author_email,
        author_name=author_name or author_email.split('@')[0],
        text=body.text.strip(),
        is_external=False,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return {
        "id": comment.comment_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "text": comment.text,
        "author": comment.author_name,
        "author_email": comment.author_email,
        "created_at": comment.created_at.isoformat(),
        "is_external": False,
    }


@router.delete("/{entity_type}/{entity_id}/comments/{comment_id}")
def delete_comment(entity_type: str, entity_id: str, comment_id: str, db: Session = Depends(_db)):
    """Delete a local comment."""
    if entity_type not in ("issue", "task"):
        raise HTTPException(400, "Invalid entity_type. Use 'issue' or 'task'")

    comment = db.query(EntityCommentORM).filter(
        EntityCommentORM.comment_id == comment_id,
        EntityCommentORM.entity_type == entity_type,
        EntityCommentORM.entity_id == entity_id,
        EntityCommentORM.is_external == False
    ).first()

    if not comment:
        raise HTTPException(404, "Comment not found")

    db.delete(comment)
    db.commit()

    return {"ok": True}


@router.patch("/{entity_type}/{entity_id}/assign")
def assign_entity(
    entity_type: str,
    entity_id: str,
    assignee_email: str = Query(...),
    db: Session = Depends(_db)
):
    """Assign a task to a team member."""
    if entity_type != "task":
        raise HTTPException(400, "Assignment only supported for tasks")

    task = db.query(TaskORM).filter(TaskORM.task_id == entity_id).first()
    if not task:
        raise HTTPException(404, "Task not found")

    # Find team member by email
    member = db.query(TeamMemberORM).filter(
        TeamMemberORM.email == assignee_email.lower()
    ).first()

    if not member:
        raise HTTPException(404, "Team member not found")

    task.assignee_id = member.member_id
    db.commit()
    db.refresh(task)

    return {
        "task_id": task.task_id,
        "assignee_id": task.assignee_id,
        "assignee_email": assignee_email,
    }
