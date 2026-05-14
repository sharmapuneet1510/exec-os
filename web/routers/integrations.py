"""Integrations — GitLab, Jira, and Application Stakeholders."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import get_db
from db.models import (
    ApplicationORM,
    GitLabIntegrationORM,
    JiraIntegrationORM,
    ApplicationStakeholderORM,
    StakeholderORM,
)

router = APIRouter(prefix="/api/applications", tags=["integrations"])


# ===== Pydantic Schemas =====

class GitLabIntegrationIn(BaseModel):
    namespace: str
    project_name: Optional[str] = ""


class GitLabIntegrationOut(BaseModel):
    id: str
    namespace: str
    project_name: str
    created_at: str
    updated_at: str


class JiraIntegrationIn(BaseModel):
    project_key: str
    project_name: Optional[str] = ""


class JiraIntegrationOut(BaseModel):
    id: str
    project_key: str
    project_name: str
    created_at: str
    updated_at: str


class ApplicationStakeholderIn(BaseModel):
    stakeholder_id: str


class ApplicationStakeholderOut(BaseModel):
    stakeholder_id: str
    name: str
    email: str
    role: str


# ===== Helper functions =====

def _get_app_or_404(db: Session, app_id: str) -> ApplicationORM:
    """Get application or raise 404."""
    app = db.query(ApplicationORM).filter(
        ApplicationORM.application_id == app_id
    ).first()
    if not app:
        raise HTTPException(404, "application not found")
    return app


def _gitlab_to_out(g: GitLabIntegrationORM) -> dict:
    """Convert GitLabIntegrationORM to output dict."""
    return {
        "id": g.gitlab_id,
        "namespace": g.namespace,
        "project_name": g.project_name or "",
        "created_at": str(g.created_at),
        "updated_at": str(g.updated_at),
    }


def _jira_to_out(j: JiraIntegrationORM) -> dict:
    """Convert JiraIntegrationORM to output dict."""
    return {
        "id": j.jira_id,
        "project_key": j.project_key,
        "project_name": j.project_name or "",
        "created_at": str(j.created_at),
        "updated_at": str(j.updated_at),
    }


def _stakeholder_to_out(s: StakeholderORM) -> dict:
    """Convert StakeholderORM to output dict."""
    return {
        "stakeholder_id": s.stakeholder_id,
        "name": s.name,
        "email": s.email,
        "role": s.role or "",
    }


# ===== GitLab Endpoints =====

@router.get("/{app_id}/gitlab", response_model=List[GitLabIntegrationOut])
def list_gitlab_integrations(app_id: str, db: Session = Depends(get_db)):
    """List all GitLab namespaces for an application, ordered by created_at."""
    # Check app exists
    _get_app_or_404(db, app_id)

    integrations = db.query(GitLabIntegrationORM).filter(
        GitLabIntegrationORM.application_id == app_id
    ).order_by(GitLabIntegrationORM.created_at).all()

    return [_gitlab_to_out(g) for g in integrations]


@router.post("/{app_id}/gitlab", response_model=GitLabIntegrationOut, status_code=201)
def create_gitlab_integration(
    app_id: str, body: GitLabIntegrationIn, db: Session = Depends(get_db)
):
    """Add a GitLab namespace to an application."""
    # Check app exists
    _get_app_or_404(db, app_id)

    # Validate namespace
    if not body.namespace.strip():
        raise HTTPException(400, "namespace required")

    g = GitLabIntegrationORM(
        application_id=app_id,
        namespace=body.namespace.strip(),
        project_name=body.project_name.strip() if body.project_name else "",
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    return _gitlab_to_out(g)


@router.patch("/{app_id}/gitlab/{gitlab_id}", response_model=GitLabIntegrationOut)
def update_gitlab_integration(
    app_id: str, gitlab_id: str, body: GitLabIntegrationIn, db: Session = Depends(get_db)
):
    """Update a GitLab namespace."""
    # Check app exists
    _get_app_or_404(db, app_id)

    # Get integration
    g = db.query(GitLabIntegrationORM).filter(
        GitLabIntegrationORM.gitlab_id == gitlab_id,
        GitLabIntegrationORM.application_id == app_id,
    ).first()
    if not g:
        raise HTTPException(404, "gitlab integration not found")

    # Validate namespace
    if not body.namespace.strip():
        raise HTTPException(400, "namespace required")

    g.namespace = body.namespace.strip()
    g.project_name = body.project_name.strip() if body.project_name else ""
    g.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(g)
    return _gitlab_to_out(g)


@router.delete("/{app_id}/gitlab/{gitlab_id}", status_code=204)
def delete_gitlab_integration(
    app_id: str, gitlab_id: str, db: Session = Depends(get_db)
):
    """Remove a GitLab namespace."""
    # Check app exists
    _get_app_or_404(db, app_id)

    # Get integration
    g = db.query(GitLabIntegrationORM).filter(
        GitLabIntegrationORM.gitlab_id == gitlab_id,
        GitLabIntegrationORM.application_id == app_id,
    ).first()
    if not g:
        raise HTTPException(404, "gitlab integration not found")

    db.delete(g)
    db.commit()


# ===== Jira Endpoints =====

@router.get("/{app_id}/jira", response_model=List[JiraIntegrationOut])
def list_jira_integrations(app_id: str, db: Session = Depends(get_db)):
    """List all Jira projects for an application, ordered by created_at."""
    # Check app exists
    _get_app_or_404(db, app_id)

    integrations = db.query(JiraIntegrationORM).filter(
        JiraIntegrationORM.application_id == app_id
    ).order_by(JiraIntegrationORM.created_at).all()

    return [_jira_to_out(j) for j in integrations]


@router.post("/{app_id}/jira", response_model=JiraIntegrationOut, status_code=201)
def create_jira_integration(
    app_id: str, body: JiraIntegrationIn, db: Session = Depends(get_db)
):
    """Add a Jira project to an application (project_key converted to uppercase)."""
    # Check app exists
    _get_app_or_404(db, app_id)

    # Validate project_key
    if not body.project_key.strip():
        raise HTTPException(400, "project_key required")

    # Convert to uppercase
    project_key = body.project_key.strip().upper()

    j = JiraIntegrationORM(
        application_id=app_id,
        project_key=project_key,
        project_name=body.project_name.strip() if body.project_name else "",
    )
    db.add(j)
    db.commit()
    db.refresh(j)
    return _jira_to_out(j)


@router.patch("/{app_id}/jira/{jira_id}", response_model=JiraIntegrationOut)
def update_jira_integration(
    app_id: str, jira_id: str, body: JiraIntegrationIn, db: Session = Depends(get_db)
):
    """Update a Jira project."""
    # Check app exists
    _get_app_or_404(db, app_id)

    # Get integration
    j = db.query(JiraIntegrationORM).filter(
        JiraIntegrationORM.jira_id == jira_id,
        JiraIntegrationORM.application_id == app_id,
    ).first()
    if not j:
        raise HTTPException(404, "jira integration not found")

    # Validate project_key
    if not body.project_key.strip():
        raise HTTPException(400, "project_key required")

    # Convert to uppercase
    project_key = body.project_key.strip().upper()

    j.project_key = project_key
    j.project_name = body.project_name.strip() if body.project_name else ""
    j.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(j)
    return _jira_to_out(j)


@router.delete("/{app_id}/jira/{jira_id}", status_code=204)
def delete_jira_integration(
    app_id: str, jira_id: str, db: Session = Depends(get_db)
):
    """Remove a Jira project."""
    # Check app exists
    _get_app_or_404(db, app_id)

    # Get integration
    j = db.query(JiraIntegrationORM).filter(
        JiraIntegrationORM.jira_id == jira_id,
        JiraIntegrationORM.application_id == app_id,
    ).first()
    if not j:
        raise HTTPException(404, "jira integration not found")

    db.delete(j)
    db.commit()


# ===== Application Stakeholders Endpoints =====

@router.get("/{app_id}/stakeholders", response_model=List[ApplicationStakeholderOut])
def list_application_stakeholders(app_id: str, db: Session = Depends(get_db)):
    """List all stakeholders linked to an application."""
    # Check app exists
    _get_app_or_404(db, app_id)

    # Get all stakeholders linked to this app
    links = db.query(ApplicationStakeholderORM).filter(
        ApplicationStakeholderORM.application_id == app_id
    ).all()

    result = []
    for link in links:
        stakeholder = db.query(StakeholderORM).filter(
            StakeholderORM.stakeholder_id == link.stakeholder_id
        ).first()
        if stakeholder:
            result.append(_stakeholder_to_out(stakeholder))

    return result


@router.post("/{app_id}/stakeholders", response_model=ApplicationStakeholderOut, status_code=201)
def link_stakeholder_to_application(
    app_id: str, body: ApplicationStakeholderIn, db: Session = Depends(get_db)
):
    """Link a stakeholder to an application."""
    # Check app exists
    _get_app_or_404(db, app_id)

    # Check stakeholder exists
    stakeholder = db.query(StakeholderORM).filter(
        StakeholderORM.stakeholder_id == body.stakeholder_id
    ).first()
    if not stakeholder:
        raise HTTPException(404, "stakeholder not found")

    # Check if already linked (unique constraint)
    existing = db.query(ApplicationStakeholderORM).filter(
        ApplicationStakeholderORM.application_id == app_id,
        ApplicationStakeholderORM.stakeholder_id == body.stakeholder_id,
    ).first()
    if existing:
        raise HTTPException(409, "stakeholder already linked to this application")

    # Create link
    link = ApplicationStakeholderORM(
        application_id=app_id,
        stakeholder_id=body.stakeholder_id,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    # Return stakeholder info
    return _stakeholder_to_out(stakeholder)


@router.delete("/{app_id}/stakeholders/{stakeholder_id}", status_code=204)
def unlink_stakeholder_from_application(
    app_id: str, stakeholder_id: str, db: Session = Depends(get_db)
):
    """Unlink a stakeholder from an application."""
    # Check app exists
    _get_app_or_404(db, app_id)

    # Get link
    link = db.query(ApplicationStakeholderORM).filter(
        ApplicationStakeholderORM.application_id == app_id,
        ApplicationStakeholderORM.stakeholder_id == stakeholder_id,
    ).first()
    if not link:
        raise HTTPException(404, "stakeholder not linked to this application")

    db.delete(link)
    db.commit()
