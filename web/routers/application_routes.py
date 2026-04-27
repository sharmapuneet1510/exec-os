"""Applications — top-level entity above Projects."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from db.base import get_db
from db.models import ApplicationORM

router = APIRouter(prefix="/api/applications", tags=["applications"])


class AppIn(BaseModel):
    name: str
    code: Optional[str] = ""
    description: Optional[str] = ""


def _out(a: ApplicationORM) -> dict:
    return {
        "application_id": a.application_id,
        "name":           a.name,
        "code":           a.code or "",
        "description":    a.description or "",
        "created_at":     a.created_at,
        "updated_at":     a.updated_at,
    }


@router.get("")
def list_apps(db: Session = Depends(get_db)):
    return [_out(a) for a in db.query(ApplicationORM).order_by(ApplicationORM.name).all()]


@router.post("", status_code=201)
def create_app(body: AppIn, db: Session = Depends(get_db)):
    if not body.name.strip():
        raise HTTPException(400, "name required")
    a = ApplicationORM(
        name=body.name.strip(),
        code=body.code.upper().strip() if body.code else "",
        description=body.description or "",
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return _out(a)


@router.patch("/{app_id}")
def update_app(app_id: str, body: AppIn, db: Session = Depends(get_db)):
    a = db.query(ApplicationORM).filter(ApplicationORM.application_id == app_id).first()
    if not a:
        raise HTTPException(404, "not found")
    a.name = body.name.strip()
    a.code = body.code.upper().strip() if body.code else ""
    if body.description is not None:
        a.description = body.description
    db.commit()
    db.refresh(a)
    return _out(a)


@router.delete("/{app_id}", status_code=204)
def delete_app(app_id: str, db: Session = Depends(get_db)):
    a = db.query(ApplicationORM).filter(ApplicationORM.application_id == app_id).first()
    if not a:
        raise HTTPException(404, "not found")
    db.delete(a)
    db.commit()
