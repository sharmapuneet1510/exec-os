"""Jira issue comments — fetch from Jira + store local comments."""

import json, logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import SessionLocal
from db.models import JiraIssueCommentORM, JiraConfigORM, AppJiraConfigORM

log = logging.getLogger("execos.comments")
router = APIRouter(prefix="/api/issues", tags=["issue-comments"])


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


@router.get("/{issue_key}/comments")
def get_issue_comments(issue_key: str, db: Session = Depends(_db)):
    """Fetch comments: Jira comments + local comments."""
    jira_cfg = db.query(JiraConfigORM).first()
    if not jira_cfg or not jira_cfg.enabled or not jira_cfg.pat:
        raise HTTPException(400, "Jira not configured")

    comments = []

    # ── Fetch Jira comments ──────────────────────────────────────────────────
    try:
        data = _jira_get(jira_cfg, f"rest/api/2/issue/{issue_key}", {
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
                "is_jira": True,
                "is_editable": False,
            })
    except Exception as e:
        log.warning(f"Failed to fetch Jira comments for {issue_key}: {e}")

    # ── Fetch local comments ─────────────────────────────────────────────────
    local_comments = db.query(JiraIssueCommentORM).filter(
        JiraIssueCommentORM.issue_key == issue_key,
        JiraIssueCommentORM.is_jira_comment == False
    ).order_by(JiraIssueCommentORM.created_at.desc()).all()

    for comment in local_comments:
        comments.append({
            "id": comment.comment_id,
            "text": comment.text,
            "author": comment.author_name or comment.author_email.split('@')[0],
            "author_email": comment.author_email,
            "created_at": (comment.created_at.isoformat())[:10],
            "is_jira": False,
            "is_editable": True,
        })

    # Sort by created_at descending
    comments.sort(key=lambda x: x["created_at"], reverse=True)

    return {
        "issue_key": issue_key,
        "comments": comments,
        "total": len(comments),
    }


@router.post("/{issue_key}/comments")
def add_comment(
    issue_key: str,
    body: CommentIn,
    author_email: str = Query(...),
    author_name: str = Query(default=""),
    db: Session = Depends(_db)
):
    """Add a local comment (not posted to Jira)."""
    if not body.text or not body.text.strip():
        raise HTTPException(400, "Comment text cannot be empty")

    comment = JiraIssueCommentORM(
        issue_key=issue_key,
        author_email=author_email,
        author_name=author_name or author_email.split('@')[0],
        text=body.text.strip(),
        is_jira_comment=False,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return {
        "id": comment.comment_id,
        "issue_key": issue_key,
        "text": comment.text,
        "author": comment.author_name,
        "author_email": comment.author_email,
        "created_at": comment.created_at.isoformat(),
        "is_jira": False,
    }


@router.delete("/{issue_key}/comments/{comment_id}")
def delete_comment(issue_key: str, comment_id: str, db: Session = Depends(_db)):
    """Delete a local comment."""
    comment = db.query(JiraIssueCommentORM).filter(
        JiraIssueCommentORM.comment_id == comment_id,
        JiraIssueCommentORM.issue_key == issue_key,
        JiraIssueCommentORM.is_jira_comment == False
    ).first()

    if not comment:
        raise HTTPException(404, "Comment not found")

    db.delete(comment)
    db.commit()

    return {"ok": True}
