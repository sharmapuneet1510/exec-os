"""Team members management."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from db.base import get_db
from db.models import TeamMemberORM

router = APIRouter(prefix="/api/members", tags=["members"])


class MemberIn(BaseModel):
    name: str
    email: Optional[str] = ""
    role: Optional[str] = ""
    is_team_member: Optional[bool] = False


def _out(m: TeamMemberORM) -> dict:
    return {
        "member_id": m.member_id,
        "name": m.name,
        "email": m.email or "",
        "role": m.role or "",
        "is_active": m.is_active,
        "is_team_member": m.is_team_member,
        "created_at": m.created_at,
        "updated_at": m.updated_at,
    }


@router.get("")
def list_members(db: Session = Depends(get_db)):
    members = db.query(TeamMemberORM).order_by(TeamMemberORM.name).all()
    return [_out(m) for m in members]


@router.get("/team")
def list_team_members(db: Session = Depends(get_db)):
    """List only members marked as team members."""
    members = db.query(TeamMemberORM).filter(TeamMemberORM.is_team_member == True).order_by(TeamMemberORM.name).all()
    return [_out(m) for m in members]


@router.post("", status_code=201)
def create_member(body: MemberIn, db: Session = Depends(get_db)):
    if not body.name.strip():
        raise HTTPException(400, "name required")

    # Check if member with this email already exists
    if body.email:
        existing = db.query(TeamMemberORM).filter(TeamMemberORM.email == body.email.lower()).first()
        if existing:
            raise HTTPException(409, "member with this email already exists")

    m = TeamMemberORM(
        name=body.name.strip(),
        email=body.email.lower() if body.email else "",
        role=body.role or "",
        is_team_member=body.is_team_member or False,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return _out(m)


@router.get("/{member_id}")
def get_member(member_id: str, db: Session = Depends(get_db)):
    m = db.query(TeamMemberORM).filter(TeamMemberORM.member_id == member_id).first()
    if not m:
        raise HTTPException(404, "not found")
    return _out(m)


@router.patch("/{member_id}")
def update_member(member_id: str, body: MemberIn, db: Session = Depends(get_db)):
    m = db.query(TeamMemberORM).filter(TeamMemberORM.member_id == member_id).first()
    if not m:
        raise HTTPException(404, "not found")

    m.name = body.name.strip()
    m.email = body.email.lower() if body.email else ""
    m.role = body.role or ""
    m.is_team_member = body.is_team_member or False
    db.commit()
    db.refresh(m)
    return _out(m)


@router.delete("/{member_id}", status_code=204)
def delete_member(member_id: str, db: Session = Depends(get_db)):
    m = db.query(TeamMemberORM).filter(TeamMemberORM.member_id == member_id).first()
    if not m:
        raise HTTPException(404, "not found")
    db.delete(m)
    db.commit()
