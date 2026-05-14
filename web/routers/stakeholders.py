from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import get_db
from db.models import StakeholderORM


router = APIRouter(prefix="/api/stakeholders", tags=["stakeholders"])


class StakeholderIn(BaseModel):
    name: str
    email: str
    role: str = ""


class StakeholderOut(BaseModel):
    stakeholder_id: str
    name: str
    email: str
    role: str
    created_at: str
    updated_at: str


def _to_out(s: StakeholderORM) -> dict:
    """Convert StakeholderORM to output dict with string timestamps."""
    return {
        "stakeholder_id": s.stakeholder_id,
        "name": s.name,
        "email": s.email,
        "role": s.role,
        "created_at": str(s.created_at),
        "updated_at": str(s.updated_at),
    }


@router.get("", response_model=List[StakeholderOut])
def list_stakeholders(db: Session = Depends(get_db)):
    """List all stakeholders ordered by name."""
    return [
        _to_out(s)
        for s in db.query(StakeholderORM).order_by(StakeholderORM.name).all()
    ]


@router.post("", response_model=StakeholderOut, status_code=201)
def create_stakeholder(body: StakeholderIn, db: Session = Depends(get_db)):
    """
    Create a new stakeholder.

    Validates:
    - name and email are not empty
    - email is unique (normalized to lowercase)
    """
    if not body.name.strip():
        raise HTTPException(400, "name must not be empty")
    if not body.email.strip():
        raise HTTPException(400, "email must not be empty")

    email_lower = body.email.strip().lower()

    # Check for duplicate email
    existing = db.query(StakeholderORM).filter(
        StakeholderORM.email == email_lower
    ).first()
    if existing:
        raise HTTPException(409, "email already exists")

    s = StakeholderORM(
        name=body.name.strip(),
        email=email_lower,
        role=body.role.strip() if body.role else "",
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _to_out(s)


@router.get("/{stakeholder_id}", response_model=StakeholderOut)
def get_stakeholder(stakeholder_id: str, db: Session = Depends(get_db)):
    """Get a single stakeholder by ID."""
    s = db.query(StakeholderORM).filter(
        StakeholderORM.stakeholder_id == stakeholder_id
    ).first()
    if not s:
        raise HTTPException(404, "stakeholder not found")
    return _to_out(s)


@router.patch("/{stakeholder_id}", response_model=StakeholderOut)
def update_stakeholder(
    stakeholder_id: str, body: dict, db: Session = Depends(get_db)
):
    """
    Update a stakeholder.

    Validates email uniqueness if changed.
    """
    s = db.query(StakeholderORM).filter(
        StakeholderORM.stakeholder_id == stakeholder_id
    ).first()
    if not s:
        raise HTTPException(404, "stakeholder not found")

    # Update allowed fields
    if "name" in body:
        s.name = body["name"].strip() if isinstance(body["name"], str) else body["name"]
    if "email" in body:
        email_lower = body["email"].strip().lower() if isinstance(body["email"], str) else body["email"]
        # Check for duplicate email (excluding current stakeholder)
        existing = db.query(StakeholderORM).filter(
            StakeholderORM.email == email_lower,
            StakeholderORM.stakeholder_id != stakeholder_id,
        ).first()
        if existing:
            raise HTTPException(409, "email already exists")
        s.email = email_lower
    if "role" in body:
        s.role = body["role"].strip() if isinstance(body["role"], str) else body["role"]

    s.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    return _to_out(s)


@router.delete("/{stakeholder_id}", status_code=204)
def delete_stakeholder(stakeholder_id: str, db: Session = Depends(get_db)):
    """Delete a stakeholder."""
    s = db.query(StakeholderORM).filter(
        StakeholderORM.stakeholder_id == stakeholder_id
    ).first()
    if not s:
        raise HTTPException(404, "stakeholder not found")
    db.delete(s)
    db.commit()
