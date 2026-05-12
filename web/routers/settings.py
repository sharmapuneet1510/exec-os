"""Global settings and integration token management."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
import requests

from db.base import SessionLocal
from db.models import IntegrationTokenORM

router = APIRouter(prefix="/api/settings", tags=["settings"])

VALIDATE_TIMEOUT = 5  # seconds


def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_or_create_tokens(db: Session) -> IntegrationTokenORM:
    """Get or create the singleton token config (id=1)."""
    tokens = db.query(IntegrationTokenORM).filter(IntegrationTokenORM.id == 1).first()
    if not tokens:
        tokens = IntegrationTokenORM(id=1)
        db.add(tokens)
        db.commit()
        db.refresh(tokens)
    return tokens


class TokensOut(BaseModel):
    gitlab_base_url: str
    gitlab_token: str
    jira_base_url: str
    jira_token: str


class TokensUpdate(BaseModel):
    gitlab_base_url: Optional[str] = None
    gitlab_token: Optional[str] = None
    jira_base_url: Optional[str] = None
    jira_token: Optional[str] = None


class ValidationRequest(BaseModel):
    gitlab_base_url: Optional[str] = None
    gitlab_token: Optional[str] = None
    jira_base_url: Optional[str] = None
    jira_token: Optional[str] = None


class ValidationResult(BaseModel):
    valid: bool
    errors: List[str]


@router.get("/tokens", response_model=TokensOut)
def get_tokens(db: Session = Depends(_db)):
    """Get current global integration tokens.

    If no config exists, creates a default one (singleton with id=1).
    Returns all 4 token fields (even if empty strings).
    """
    tokens = _get_or_create_tokens(db)
    return TokensOut(
        gitlab_base_url=tokens.gitlab_base_url or "",
        gitlab_token=tokens.gitlab_token or "",
        jira_base_url=tokens.jira_base_url or "",
        jira_token=tokens.jira_token or "",
    )


@router.patch("/tokens", response_model=TokensOut)
def update_tokens(body: TokensUpdate, db: Session = Depends(_db)):
    """Update global integration tokens.

    Body: {gitlab_base_url?, gitlab_token?, jira_base_url?, jira_token?} (all optional)
    Creates singleton if it doesn't exist.
    Returns: updated config with all 4 fields.
    """
    tokens = _get_or_create_tokens(db)

    # Update only provided fields
    if body.gitlab_base_url is not None:
        tokens.gitlab_base_url = body.gitlab_base_url
    if body.gitlab_token is not None:
        tokens.gitlab_token = body.gitlab_token
    if body.jira_base_url is not None:
        tokens.jira_base_url = body.jira_base_url
    if body.jira_token is not None:
        tokens.jira_token = body.jira_token

    db.commit()
    db.refresh(tokens)

    return TokensOut(
        gitlab_base_url=tokens.gitlab_base_url or "",
        gitlab_token=tokens.gitlab_token or "",
        jira_base_url=tokens.jira_base_url or "",
        jira_token=tokens.jira_token or "",
    )


@router.post("/tokens/validate", response_model=ValidationResult)
def validate_tokens(body: ValidationRequest):
    """Validate integration tokens work.

    Body: {gitlab_base_url?, gitlab_token?, jira_base_url?, jira_token?}

    For GitLab: if both base_url and token provided, makes GET to "{base_url}/api/v4/user"
    with header {"PRIVATE-TOKEN": token}

    For Jira: if both base_url and token provided, makes GET to "{base_url}/rest/api/3/myself"
    with header {"Authorization": f"Bearer {token}"}

    Returns: {valid: bool, errors: [list of error messages]}
    Uses timeout of 5 seconds on requests.
    Does not save on validation, just tests.
    """
    errors = []

    # Validate GitLab
    if body.gitlab_base_url and body.gitlab_token:
        try:
            url = body.gitlab_base_url.rstrip("/") + "/api/v4/user"
            headers = {"PRIVATE-TOKEN": body.gitlab_token}
            response = requests.get(url, headers=headers, timeout=VALIDATE_TIMEOUT)
            if response.status_code != 200:
                errors.append(f"GitLab validation failed: HTTP {response.status_code}")
        except requests.exceptions.Timeout:
            errors.append("GitLab request timed out (5s timeout)")
        except requests.exceptions.ConnectionError as e:
            errors.append(f"GitLab connection error: {str(e)}")
        except Exception as e:
            errors.append(f"GitLab validation error: {str(e)}")

    # Validate Jira
    if body.jira_base_url and body.jira_token:
        try:
            url = body.jira_base_url.rstrip("/") + "/rest/api/3/myself"
            headers = {"Authorization": f"Bearer {body.jira_token}"}
            response = requests.get(url, headers=headers, timeout=VALIDATE_TIMEOUT)
            if response.status_code != 200:
                errors.append(f"Jira validation failed: HTTP {response.status_code}")
        except requests.exceptions.Timeout:
            errors.append("Jira request timed out (5s timeout)")
        except requests.exceptions.ConnectionError as e:
            errors.append(f"Jira connection error: {str(e)}")
        except Exception as e:
            errors.append(f"Jira validation error: {str(e)}")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
    )
