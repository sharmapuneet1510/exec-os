"""Resource Allocation — assign team members to projects with % allocation and date ranges."""
import json
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import get_db
from db.models import ResourceAllocationORM, TeamMemberORM, ProjectORM

router = APIRouter(prefix="/api/resource-allocations", tags=["resource-allocations"])


class AllocationIn(BaseModel):
    member_id: str
    project_id: str
    start_date: date
    end_date: date
    allocation_pct: int = 100
    role: Optional[str] = None
    notes: str = ""


def _to_out(a: ResourceAllocationORM, db: Session) -> dict:
    member  = db.query(TeamMemberORM).filter(TeamMemberORM.member_id == a.member_id).first()
    project = db.query(ProjectORM).filter(ProjectORM.project_id == a.project_id).first()
    return {
        "allocation_id":  a.allocation_id,
        "member_id":      a.member_id,
        "member_name":    member.name if member else "",
        "member_role":    member.role if member else "",
        "project_id":     a.project_id,
        "project_name":   project.name if project else "",
        "start_date":     str(a.start_date),
        "end_date":       str(a.end_date),
        "allocation_pct": a.allocation_pct,
        "role":           a.role,
        "notes":          a.notes or "",
        "created_at":     a.created_at.isoformat() if a.created_at else None,
    }


@router.get("")
def list_allocations(db: Session = Depends(get_db)):
    rows = db.query(ResourceAllocationORM).order_by(ResourceAllocationORM.start_date).all()
    return [_to_out(r, db) for r in rows]


@router.post("", status_code=201)
def create_allocation(body: AllocationIn, db: Session = Depends(get_db)):
    if body.start_date > body.end_date:
        raise HTTPException(400, "start_date must be before end_date")
    if not 0 <= body.allocation_pct <= 200:
        raise HTTPException(400, "allocation_pct must be 0–200")
    a = ResourceAllocationORM(**body.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return _to_out(a, db)


@router.patch("/{allocation_id}")
def update_allocation(allocation_id: str, body: dict, db: Session = Depends(get_db)):
    a = db.query(ResourceAllocationORM).filter(ResourceAllocationORM.allocation_id == allocation_id).first()
    if not a:
        raise HTTPException(404, "Allocation not found")
    allowed = {"start_date", "end_date", "allocation_pct", "role", "notes"}
    for k, v in body.items():
        if k not in allowed:
            continue
        if k in ("start_date", "end_date") and isinstance(v, str):
            v = date.fromisoformat(v)
        setattr(a, k, v)
    a.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(a)
    return _to_out(a, db)


@router.delete("/{allocation_id}", status_code=204)
def delete_allocation(allocation_id: str, db: Session = Depends(get_db)):
    a = db.query(ResourceAllocationORM).filter(ResourceAllocationORM.allocation_id == allocation_id).first()
    if not a:
        raise HTTPException(404, "Allocation not found")
    db.delete(a)
    db.commit()


@router.get("/forecast")
def get_forecast(db: Session = Depends(get_db)):
    """Return monthly allocation summary for heat-map rendering."""
    today = date.today().replace(day=1)
    months = [(today + relativedelta(months=i)).strftime("%Y-%m") for i in range(12)]

    allocations = db.query(ResourceAllocationORM).all()
    members  = {m.member_id:  m for m in db.query(TeamMemberORM).all()}
    projects = {p.project_id: p for p in db.query(ProjectORM).all()}

    proj_data:   dict = {}
    member_data: dict = {}

    for a in allocations:
        # Expand date range into overlapping months
        cur = a.start_date.replace(day=1)
        end = a.end_date.replace(day=1)
        while cur <= end:
            ym = cur.strftime("%Y-%m")
            if ym in months:
                # by project
                pid = a.project_id
                if pid not in proj_data:
                    p = projects.get(pid)
                    proj_data[pid] = {"project_id": pid, "name": p.name if p else "", "months": {m: {"total_pct": 0, "member_count": 0, "over": False} for m in months}}
                proj_data[pid]["months"][ym]["total_pct"]    += a.allocation_pct
                proj_data[pid]["months"][ym]["member_count"] += 1
                proj_data[pid]["months"][ym]["over"] = proj_data[pid]["months"][ym]["total_pct"] > 100

                # by member
                mid = a.member_id
                if mid not in member_data:
                    m = members.get(mid)
                    member_data[mid] = {"member_id": mid, "name": m.name if m else "", "months": {mo: {"total_pct": 0, "project_count": 0, "over": False} for mo in months}}
                member_data[mid]["months"][ym]["total_pct"]     += a.allocation_pct
                member_data[mid]["months"][ym]["project_count"] += 1
                member_data[mid]["months"][ym]["over"] = member_data[mid]["months"][ym]["total_pct"] > 100

            cur += relativedelta(months=1)

    return {
        "months": months,
        "by_project": sorted(proj_data.values(), key=lambda x: x["name"]),
        "by_member":  sorted(member_data.values(), key=lambda x: x["name"]),
    }
