"""Delivery Management — templates + releases with per-item tracking."""

from datetime import datetime, date as _date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import get_db
from db.models import (DeliveryTemplateORM, DeliveryTemplateItemORM, DeliveryReleaseORM,
                       DeliveryReleaseItemORM, DeliveryReleaseSprintORM, SprintConfigORM)
from services.release_health import release_health
from services.jira_service import get_jira_service

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
    application_id: Optional[str] = None
    project_id: Optional[str] = None
    template_id: Optional[str] = None
    release_manager: Optional[str] = ""
    target_date: Optional[str] = None   # ISO date string
    start_date: Optional[str] = None
    release_date: Optional[str] = None
    uat_date: Optional[str] = None
    sign_off_date: Optional[str] = None
    jira_project_key: Optional[str] = ""
    status: str = "planned"
    description: Optional[str] = ""


class ReleaseItemPatch(BaseModel):
    status: Optional[str] = None
    assignee: Optional[str] = None
    notes: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    responsible_role: Optional[str] = None
    planned_date: Optional[str] = None
    stage: Optional[str] = None


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
        "application_id":  r.application_id,
        "project_id":      r.project_id,
        "template_id":     r.template_id,
        "release_manager": r.release_manager or "",
        "target_date":     r.target_date.isoformat() if r.target_date else None,
        "start_date":      r.start_date.isoformat() if r.start_date else None,
        "release_date":    r.release_date.isoformat() if r.release_date else None,
        "uat_date":        r.uat_date.isoformat() if r.uat_date else None,
        "sign_off_date":   r.sign_off_date.isoformat() if r.sign_off_date else None,
        "jira_project_key": r.jira_project_key or "",
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
        "stage":            i.stage,
        "planned_date":     i.planned_date.isoformat() if i.planned_date else None,
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

    def parse_date(d):
        return dt_date.fromisoformat(d) if d else None

    r = DeliveryReleaseORM(
        name=body.name.strip(),
        version=body.version or "",
        application_id=body.application_id,
        project_id=body.project_id,
        template_id=body.template_id,
        release_manager=body.release_manager or "",
        target_date=parse_date(body.target_date),
        start_date=parse_date(body.start_date),
        release_date=parse_date(body.release_date),
        uat_date=parse_date(body.uat_date),
        sign_off_date=parse_date(body.sign_off_date),
        jira_project_key=body.jira_project_key or "",
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
                stage=ti.stage,
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
    d["health"] = release_health(items, _date.today())
    return d


@router.patch("/releases/{release_id}")
def update_release(release_id: str, body: ReleaseIn, db: Session = Depends(get_db)):
    r = db.query(DeliveryReleaseORM).filter(DeliveryReleaseORM.release_id == release_id).first()
    if not r:
        raise HTTPException(404, "not found")
    from datetime import date as dt_date

    def parse_date(d):
        return dt_date.fromisoformat(d) if d else None

    r.name        = body.name.strip()
    r.version     = body.version or ""
    r.application_id = body.application_id
    r.project_id  = body.project_id
    r.release_manager = body.release_manager or ""
    r.target_date = parse_date(body.target_date)
    r.start_date  = parse_date(body.start_date)
    r.release_date = parse_date(body.release_date)
    r.uat_date    = parse_date(body.uat_date)
    r.sign_off_date = parse_date(body.sign_off_date)
    r.jira_project_key = body.jira_project_key or ""
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
    if body.planned_date is not None:
        i.planned_date = _date.fromisoformat(body.planned_date) if body.planned_date else None
    if body.stage is not None:
        i.stage = body.stage
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


# ── Jira sprint attachment (curated, multiple per release) ──────────────────

class SprintAttachIn(BaseModel):
    board_id: str = ""
    sprint_id: str
    sprint_name: str = ""


def _my_jira_email(db) -> str:
    cfg = db.query(SprintConfigORM).first()
    return (cfg.my_jira_email or "").lower() if cfg else ""


@router.post("/releases/{release_id}/sprints", status_code=201)
def attach_sprint(release_id: str, body: SprintAttachIn, db: Session = Depends(get_db)):
    if not db.query(DeliveryReleaseORM).filter(DeliveryReleaseORM.release_id == release_id).first():
        raise HTTPException(404, "release not found")
    row = DeliveryReleaseSprintORM(release_id=release_id, board_id=body.board_id,
                                   sprint_id=body.sprint_id, sprint_name=body.sprint_name)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"attach_id": row.attach_id, "sprint_id": row.sprint_id, "sprint_name": row.sprint_name}


@router.get("/releases/{release_id}/sprints")
def list_sprints(release_id: str, db: Session = Depends(get_db)):
    release = db.query(DeliveryReleaseORM).filter(DeliveryReleaseORM.release_id == release_id).first()
    if not release:
        raise HTTPException(404, "release not found")
    my_email = _my_jira_email(db)
    jira = get_jira_service(release.application_id, db) if release.application_id else None
    out = []
    rows = db.query(DeliveryReleaseSprintORM).filter(
        DeliveryReleaseSprintORM.release_id == release_id).all()
    for s in rows:
        issues = []
        if jira and release.jira_project_key and s.sprint_id:
            try:
                raw = jira.get_sprint_issues(release.jira_project_key, int(s.sprint_id))
            except Exception:
                raw = []
            for it in raw:
                f = it.get("fields", {})
                ass = (f.get("assignee") or {}).get("emailAddress", "") or ""
                issues.append({
                    "key": it.get("key", ""),
                    "summary": f.get("summary", ""),
                    "status": (f.get("status") or {}).get("name", ""),
                    "mine": bool(my_email) and ass.lower() == my_email,
                })
        out.append({"attach_id": s.attach_id, "board_id": s.board_id, "sprint_id": s.sprint_id,
                    "sprint_name": s.sprint_name, "issues": issues})
    return {"release_id": release_id, "sprints": out}


@router.delete("/releases/{release_id}/sprints/{attach_id}", status_code=204)
def detach_sprint(release_id: str, attach_id: str, db: Session = Depends(get_db)):
    row = db.query(DeliveryReleaseSprintORM).filter(
        DeliveryReleaseSprintORM.attach_id == attach_id,
        DeliveryReleaseSprintORM.release_id == release_id).first()
    if not row:
        raise HTTPException(404, "attachment not found")
    db.delete(row)
    db.commit()
    return None
