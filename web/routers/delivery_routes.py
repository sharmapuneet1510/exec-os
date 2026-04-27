"""Delivery Management — templates + releases with per-item tracking."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import get_db
from db.models import DeliveryTemplateORM, DeliveryTemplateItemORM, DeliveryReleaseORM, DeliveryReleaseItemORM

router = APIRouter(prefix="/api/delivery", tags=["delivery"])

CATEGORIES = ("pre_release", "release", "post_release")
ITEM_STATUSES = ("pending", "in_progress", "done", "skipped", "blocked")
RELEASE_STATUSES = ("planned", "in_progress", "released", "rollback")


# ── Schemas ───────────────────────────────────────────────────────────────────

class TemplateIn(BaseModel):
    name: str
    description: Optional[str] = ""
    is_default: bool = False


class TemplateItemIn(BaseModel):
    title: str
    description: Optional[str] = ""
    category: str = "pre_release"
    responsible_role: Optional[str] = ""
    is_required: bool = True
    order: Optional[int] = None


class ReleaseIn(BaseModel):
    name: str
    version: Optional[str] = ""
    project_id: Optional[str] = None
    template_id: Optional[str] = None
    release_manager: Optional[str] = ""
    target_date: Optional[str] = None   # ISO date string
    status: str = "planned"
    description: Optional[str] = ""


class ReleaseItemPatch(BaseModel):
    status: Optional[str] = None
    assignee: Optional[str] = None
    notes: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    responsible_role: Optional[str] = None


# ── Serialisers ───────────────────────────────────────────────────────────────

def _tmpl_out(t: DeliveryTemplateORM) -> dict:
    return {
        "template_id": t.template_id,
        "name":        t.name,
        "description": t.description or "",
        "is_default":  t.is_default,
        "created_at":  t.created_at,
        "updated_at":  t.updated_at,
    }


def _item_out(i: DeliveryTemplateItemORM) -> dict:
    return {
        "item_id":          i.item_id,
        "template_id":      i.template_id,
        "order":            i.order,
        "title":            i.title,
        "description":      i.description or "",
        "category":         i.category,
        "responsible_role": i.responsible_role or "",
        "is_required":      i.is_required,
    }


def _rel_out(r: DeliveryReleaseORM) -> dict:
    return {
        "release_id":      r.release_id,
        "name":            r.name,
        "version":         r.version or "",
        "project_id":      r.project_id,
        "template_id":     r.template_id,
        "release_manager": r.release_manager or "",
        "target_date":     r.target_date.isoformat() if r.target_date else None,
        "status":          r.status,
        "description":     r.description or "",
        "created_at":      r.created_at,
        "updated_at":      r.updated_at,
    }


def _rel_item_out(i: DeliveryReleaseItemORM) -> dict:
    return {
        "item_id":          i.item_id,
        "release_id":       i.release_id,
        "order":            i.order,
        "title":            i.title,
        "description":      i.description or "",
        "category":         i.category,
        "responsible_role": i.responsible_role or "",
        "status":           i.status,
        "assignee":         i.assignee or "",
        "notes":            i.notes or "",
        "is_required":      i.is_required,
        "completed_at":     i.completed_at.isoformat() if i.completed_at else None,
    }


# ── Template endpoints ────────────────────────────────────────────────────────

@router.get("/templates")
def list_templates(db: Session = Depends(get_db)):
    rows = db.query(DeliveryTemplateORM).order_by(DeliveryTemplateORM.created_at.desc()).all()
    result = []
    for t in rows:
        d = _tmpl_out(t)
        d["item_count"] = db.query(DeliveryTemplateItemORM).filter(DeliveryTemplateItemORM.template_id == t.template_id).count()
        result.append(d)
    return result


@router.post("/templates", status_code=201)
def create_template(body: TemplateIn, db: Session = Depends(get_db)):
    if not body.name.strip():
        raise HTTPException(400, "name required")
    if body.is_default:
        db.query(DeliveryTemplateORM).update({DeliveryTemplateORM.is_default: False})
    t = DeliveryTemplateORM(name=body.name.strip(), description=body.description, is_default=body.is_default)
    db.add(t)
    db.commit()
    db.refresh(t)
    return _tmpl_out(t)


@router.get("/templates/{template_id}")
def get_template(template_id: str, db: Session = Depends(get_db)):
    t = db.query(DeliveryTemplateORM).filter(DeliveryTemplateORM.template_id == template_id).first()
    if not t:
        raise HTTPException(404, "not found")
    items = db.query(DeliveryTemplateItemORM).filter(DeliveryTemplateItemORM.template_id == template_id).order_by(DeliveryTemplateItemORM.order, DeliveryTemplateItemORM.category).all()
    d = _tmpl_out(t)
    d["items"] = [_item_out(i) for i in items]
    return d


@router.patch("/templates/{template_id}")
def update_template(template_id: str, body: TemplateIn, db: Session = Depends(get_db)):
    t = db.query(DeliveryTemplateORM).filter(DeliveryTemplateORM.template_id == template_id).first()
    if not t:
        raise HTTPException(404, "not found")
    if body.is_default and not t.is_default:
        db.query(DeliveryTemplateORM).update({DeliveryTemplateORM.is_default: False})
    t.name = body.name.strip()
    if body.description is not None:
        t.description = body.description
    t.is_default = body.is_default
    db.commit()
    db.refresh(t)
    return _tmpl_out(t)


@router.delete("/templates/{template_id}", status_code=204)
def delete_template(template_id: str, db: Session = Depends(get_db)):
    t = db.query(DeliveryTemplateORM).filter(DeliveryTemplateORM.template_id == template_id).first()
    if not t:
        raise HTTPException(404, "not found")
    db.delete(t)
    db.commit()


@router.post("/templates/{template_id}/items", status_code=201)
def add_template_item(template_id: str, body: TemplateItemIn, db: Session = Depends(get_db)):
    if not db.query(DeliveryTemplateORM).filter(DeliveryTemplateORM.template_id == template_id).first():
        raise HTTPException(404, "template not found")
    if body.category not in CATEGORIES:
        raise HTTPException(400, f"category must be one of {CATEGORIES}")
    if body.order is None:
        count = db.query(DeliveryTemplateItemORM).filter(DeliveryTemplateItemORM.template_id == template_id).count()
        body.order = count
    i = DeliveryTemplateItemORM(
        template_id=template_id,
        title=body.title.strip(),
        description=body.description,
        category=body.category,
        responsible_role=body.responsible_role or "",
        is_required=body.is_required,
        order=body.order,
    )
    db.add(i)
    db.commit()
    db.refresh(i)
    return _item_out(i)


@router.patch("/templates/{template_id}/items/{item_id}")
def update_template_item(template_id: str, item_id: str, body: TemplateItemIn, db: Session = Depends(get_db)):
    i = db.query(DeliveryTemplateItemORM).filter(
        DeliveryTemplateItemORM.item_id == item_id,
        DeliveryTemplateItemORM.template_id == template_id,
    ).first()
    if not i:
        raise HTTPException(404, "item not found")
    if body.title:
        i.title = body.title.strip()
    if body.description is not None:
        i.description = body.description
    if body.category:
        i.category = body.category
    if body.responsible_role is not None:
        i.responsible_role = body.responsible_role
    i.is_required = body.is_required
    if body.order is not None:
        i.order = body.order
    db.commit()
    db.refresh(i)
    return _item_out(i)


@router.delete("/templates/{template_id}/items/{item_id}", status_code=204)
def delete_template_item(template_id: str, item_id: str, db: Session = Depends(get_db)):
    i = db.query(DeliveryTemplateItemORM).filter(
        DeliveryTemplateItemORM.item_id == item_id,
        DeliveryTemplateItemORM.template_id == template_id,
    ).first()
    if not i:
        raise HTTPException(404, "item not found")
    db.delete(i)
    db.commit()


# ── Release endpoints ─────────────────────────────────────────────────────────

@router.get("/releases")
def list_releases(db: Session = Depends(get_db)):
    rows = db.query(DeliveryReleaseORM).order_by(DeliveryReleaseORM.created_at.desc()).all()
    result = []
    for r in rows:
        d = _rel_out(r)
        items = db.query(DeliveryReleaseItemORM).filter(DeliveryReleaseItemORM.release_id == r.release_id).all()
        d["total_items"] = len(items)
        d["done_items"]  = sum(1 for i in items if i.status == "done")
        result.append(d)
    return result


@router.post("/releases", status_code=201)
def create_release(body: ReleaseIn, db: Session = Depends(get_db)):
    if not body.name.strip():
        raise HTTPException(400, "name required")
    from datetime import date as dt_date
    td = dt_date.fromisoformat(body.target_date) if body.target_date else None

    r = DeliveryReleaseORM(
        name=body.name.strip(),
        version=body.version or "",
        project_id=body.project_id,
        template_id=body.template_id,
        release_manager=body.release_manager or "",
        target_date=td,
        status=body.status,
        description=body.description or "",
    )
    db.add(r)
    db.commit()
    db.refresh(r)

    # Copy template items if template provided
    if body.template_id:
        tmpl_items = db.query(DeliveryTemplateItemORM).filter(
            DeliveryTemplateItemORM.template_id == body.template_id
        ).order_by(DeliveryTemplateItemORM.order).all()
        for ti in tmpl_items:
            ri = DeliveryReleaseItemORM(
                release_id=r.release_id,
                order=ti.order,
                title=ti.title,
                description=ti.description or "",
                category=ti.category,
                responsible_role=ti.responsible_role or "",
                is_required=ti.is_required,
            )
            db.add(ri)
        db.commit()

    return _rel_out(r)


@router.get("/releases/{release_id}")
def get_release(release_id: str, db: Session = Depends(get_db)):
    r = db.query(DeliveryReleaseORM).filter(DeliveryReleaseORM.release_id == release_id).first()
    if not r:
        raise HTTPException(404, "not found")
    items = db.query(DeliveryReleaseItemORM).filter(DeliveryReleaseItemORM.release_id == release_id).order_by(DeliveryReleaseItemORM.category, DeliveryReleaseItemORM.order).all()
    d = _rel_out(r)
    d["items"] = [_rel_item_out(i) for i in items]
    return d


@router.patch("/releases/{release_id}")
def update_release(release_id: str, body: ReleaseIn, db: Session = Depends(get_db)):
    r = db.query(DeliveryReleaseORM).filter(DeliveryReleaseORM.release_id == release_id).first()
    if not r:
        raise HTTPException(404, "not found")
    from datetime import date as dt_date
    r.name        = body.name.strip()
    r.version     = body.version or ""
    r.project_id  = body.project_id
    r.release_manager = body.release_manager or ""
    r.target_date = dt_date.fromisoformat(body.target_date) if body.target_date else None
    r.status      = body.status
    r.description = body.description or ""
    db.commit()
    db.refresh(r)
    return _rel_out(r)


@router.delete("/releases/{release_id}", status_code=204)
def delete_release(release_id: str, db: Session = Depends(get_db)):
    r = db.query(DeliveryReleaseORM).filter(DeliveryReleaseORM.release_id == release_id).first()
    if not r:
        raise HTTPException(404, "not found")
    db.delete(r)
    db.commit()


@router.patch("/releases/{release_id}/items/{item_id}")
def update_release_item(release_id: str, item_id: str, body: ReleaseItemPatch, db: Session = Depends(get_db)):
    i = db.query(DeliveryReleaseItemORM).filter(
        DeliveryReleaseItemORM.item_id == item_id,
        DeliveryReleaseItemORM.release_id == release_id,
    ).first()
    if not i:
        raise HTTPException(404, "item not found")
    if body.status is not None:
        if body.status not in ITEM_STATUSES:
            raise HTTPException(400, f"status must be one of {ITEM_STATUSES}")
        i.status = body.status
        if body.status == "done":
            i.completed_at = datetime.utcnow()
        elif i.completed_at and body.status != "done":
            i.completed_at = None
    if body.assignee is not None:
        i.assignee = body.assignee
    if body.notes is not None:
        i.notes = body.notes
    if body.title is not None:
        i.title = body.title
    if body.description is not None:
        i.description = body.description
    if body.responsible_role is not None:
        i.responsible_role = body.responsible_role
    db.commit()
    db.refresh(i)
    return _rel_item_out(i)


@router.post("/releases/{release_id}/items", status_code=201)
def add_release_item(release_id: str, body: TemplateItemIn, db: Session = Depends(get_db)):
    if not db.query(DeliveryReleaseORM).filter(DeliveryReleaseORM.release_id == release_id).first():
        raise HTTPException(404, "release not found")
    if body.order is None:
        count = db.query(DeliveryReleaseItemORM).filter(DeliveryReleaseItemORM.release_id == release_id).count()
        body.order = count
    i = DeliveryReleaseItemORM(
        release_id=release_id,
        title=body.title.strip(),
        description=body.description or "",
        category=body.category,
        responsible_role=body.responsible_role or "",
        is_required=body.is_required,
        order=body.order,
    )
    db.add(i)
    db.commit()
    db.refresh(i)
    return _rel_item_out(i)


@router.delete("/releases/{release_id}/items/{item_id}", status_code=204)
def delete_release_item(release_id: str, item_id: str, db: Session = Depends(get_db)):
    i = db.query(DeliveryReleaseItemORM).filter(
        DeliveryReleaseItemORM.item_id == item_id,
        DeliveryReleaseItemORM.release_id == release_id,
    ).first()
    if not i:
        raise HTTPException(404, "item not found")
    db.delete(i)
    db.commit()
