"""Jira sync endpoints — fetch sprints and sync team members."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.base import get_db
from db.models import ApplicationORM, DeliveryReleaseORM
from services.jira_service import get_jira_service

router = APIRouter(prefix="/api/jira", tags=["jira"])


@router.post("/sync-members/{app_id}")
def sync_members_from_jira(app_id: str, db: Session = Depends(get_db)):
    """Fetch Jira issues and create team members from reporter/assignee."""
    # Verify app exists
    app = db.query(ApplicationORM).filter(ApplicationORM.application_id == app_id).first()
    if not app:
        raise HTTPException(404, "application not found")

    # Get Jira service
    jira = get_jira_service(app_id, db)
    if not jira:
        raise HTTPException(400, "Jira not configured for this application")

    # Get Jira project keys from application
    jira_projects = []
    if app.jira_projects:
        try:
            import json
            jira_projects = json.loads(app.jira_projects)
        except:
            pass

    if not jira_projects:
        raise HTTPException(400, "no Jira projects configured")

    # Fetch all issues from all projects
    all_members = []
    for project_key in jira_projects:
        sprints = jira.get_sprints(project_key)
        for sprint in sprints:
            sprint_id = sprint.get("id")
            if sprint_id:
                issues = jira.get_sprint_issues(project_key, sprint_id)
                members = jira.extract_members_from_issues(issues)
                all_members.extend(members)

    # Sync to database
    result = jira.sync_members_to_db(all_members, db)
    return {
        "status": "success",
        "created": result["created"],
        "existing": result["existing"]
    }


@router.get("/sprints/{release_id}")
def get_release_sprints(release_id: str, db: Session = Depends(get_db)):
    """Get sprints for a release's Jira project."""
    # Verify release exists
    release = db.query(DeliveryReleaseORM).filter(DeliveryReleaseORM.release_id == release_id).first()
    if not release:
        raise HTTPException(404, "release not found")

    if not release.application_id:
        raise HTTPException(400, "release not linked to application")

    # Get Jira service
    jira = get_jira_service(release.application_id, db)
    if not jira:
        raise HTTPException(400, "Jira not configured for this application")

    # Get project key
    project_key = release.jira_project_key or ""
    if not project_key:
        raise HTTPException(400, "release Jira project not set")

    # Fetch sprints
    sprints = jira.get_sprints(project_key)
    return {
        "release_id": release_id,
        "project_key": project_key,
        "sprints": sprints
    }


@router.get("/sprints/{release_id}/{sprint_id}/issues")
def get_sprint_issues(release_id: str, sprint_id: int, db: Session = Depends(get_db)):
    """Get issues in a sprint."""
    release = db.query(DeliveryReleaseORM).filter(DeliveryReleaseORM.release_id == release_id).first()
    if not release:
        raise HTTPException(404, "release not found")

    if not release.application_id:
        raise HTTPException(400, "release not linked to application")

    jira = get_jira_service(release.application_id, db)
    if not jira:
        raise HTTPException(400, "Jira not configured")

    project_key = release.jira_project_key or ""
    if not project_key:
        raise HTTPException(400, "release Jira project not set")

    issues = jira.get_sprint_issues(project_key, sprint_id)
    return {
        "release_id": release_id,
        "sprint_id": sprint_id,
        "issues": issues
    }


@router.get("/members/workload")
def get_team_workload(db: Session = Depends(get_db)):
    """Get workload summary for all team members."""
    from db.models import TeamMemberORM

    team_members = db.query(TeamMemberORM).filter(TeamMemberORM.is_team_member == True).all()

    workload = []
    for member in team_members:
        workload.append({
            "member_id": member.member_id,
            "name": member.name,
            "email": member.email,
            "role": member.role,
            "is_team_member": member.is_team_member
        })

    return {"team_members": workload}
