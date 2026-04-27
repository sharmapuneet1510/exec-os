"""Project Planner — hierarchy-based estimation: Estimate → Milestones → Tasks."""

import json
from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import get_db
from db.models import ProjEstimateORM, ProjEstMilestoneORM, ProjEstTaskORM

router = APIRouter(prefix="/api/proj-estimates", tags=["proj-estimates"])


# ── Calculation ───────────────────────────────────────────────────────────────

def _phase_duration(items_sorted, get_dur):
    """Sequential items start a new phase; parallel items join current phase.
    Phase duration = max of items in that phase. Total = sum of all phases."""
    phases = []
    current_max = 0
    for i, item in enumerate(items_sorted):
        d = get_dur(item)
        if i == 0 or item.execution_type == "sequential":
            if i > 0:
                phases.append(current_max)
            current_max = d
        else:
            current_max = max(current_max, d)
    phases.append(current_max)
    return sum(phases)


def _build_timeline(estimate: ProjEstimateORM, milestones: list, tasks_by_ms: dict) -> dict:
    start = estimate.start_date or date.today()
    ms_sorted = sorted(milestones, key=lambda m: m.order)

    ms_results = []
    project_end_day = 0
    current_phase_start = 0
    current_phase_end = 0

    for i, ms in enumerate(ms_sorted):
        tasks = sorted(tasks_by_ms.get(ms.ms_id, []), key=lambda t: t.order)
        ms_dur = _phase_duration(tasks, lambda t: t.duration_days) if tasks else 0

        if i == 0 or ms.execution_type == "sequential":
            ms_start_day = current_phase_end
            current_phase_start = ms_start_day
            current_phase_end = ms_start_day + ms_dur
            project_end_day = current_phase_end
        else:
            ms_start_day = current_phase_start
            current_phase_end = max(current_phase_end, ms_start_day + ms_dur)
            project_end_day = max(project_end_day, current_phase_end)

        # Build task-level timeline within this milestone
        task_results = []
        t_phase_start = 0
        t_phase_end = 0

        for j, task in enumerate(tasks):
            if j == 0 or task.execution_type == "sequential":
                t_start = t_phase_end
                t_phase_start = t_start
                t_phase_end = t_start + task.duration_days
            else:
                t_start = t_phase_start
                t_phase_end = max(t_phase_end, t_start + task.duration_days)

            task_results.append({
                "task_id":    task.task_id,
                "start_day":  ms_start_day + t_start,
                "end_day":    ms_start_day + t_start + task.duration_days,
                "start_date": (start + timedelta(days=ms_start_day + t_start)).isoformat(),
                "end_date":   (start + timedelta(days=ms_start_day + t_start + task.duration_days)).isoformat(),
            })

        ms_results.append({
            "ms_id":      ms.ms_id,
            "start_day":  ms_start_day,
            "end_day":    ms_start_day + ms_dur,
            "duration":   ms_dur,
            "start_date": (start + timedelta(days=ms_start_day)).isoformat(),
            "end_date":   (start + timedelta(days=ms_start_day + ms_dur)).isoformat(),
            "tasks":      task_results,
        })

    end_date = start + timedelta(days=project_end_day)
    exceeds = False
    days_over = 0
    if estimate.end_date_constraint:
        exceeds = end_date > estimate.end_date_constraint
        days_over = (end_date - estimate.end_date_constraint).days if exceeds else 0

    return {
        "milestones":            ms_results,
        "total_days":            project_end_day,
        "start_date":            start.isoformat(),
        "end_date":              end_date.isoformat(),
        "exceeds_constraint":    exceeds,
        "days_over":             days_over,
        "end_date_constraint":   estimate.end_date_constraint.isoformat() if estimate.end_date_constraint else None,
    }


# ── Schemas ───────────────────────────────────────────────────────────────────

class EstimateIn(BaseModel):
    name: str
    description: Optional[str] = ""
    start_date: Optional[date] = None
    end_date_constraint: Optional[date] = None
    jira_project_key: Optional[str] = ""
    application_id: Optional[str] = None


class MilestoneIn(BaseModel):
    name: str
    description: Optional[str] = ""
    order: int = 0
    execution_type: str = "sequential"  # sequential | parallel


class TaskIn(BaseModel):
    name: str
    description: Optional[str] = ""
    duration_days: int = 1
    execution_type: str = "sequential"
    order: int = 0
    assignee: Optional[str] = ""
    jira_key: Optional[str] = ""


def _est_out(e: ProjEstimateORM) -> dict:
    return {
        "est_id":              e.est_id,
        "name":                e.name,
        "description":         e.description or "",
        "start_date":          e.start_date.isoformat() if e.start_date else None,
        "end_date_constraint": e.end_date_constraint.isoformat() if e.end_date_constraint else None,
        "jira_project_key":    e.jira_project_key or "",
        "application_id":      e.application_id,
        "created_at":          e.created_at,
        "updated_at":          e.updated_at,
    }


def _ms_out(m: ProjEstMilestoneORM) -> dict:
    return {
        "ms_id":          m.ms_id,
        "est_id":         m.est_id,
        "name":           m.name,
        "description":    m.description or "",
        "order":          m.order,
        "execution_type": m.execution_type,
        "created_at":     m.created_at,
    }


def _task_out(t: ProjEstTaskORM) -> dict:
    return {
        "task_id":        t.task_id,
        "ms_id":          t.ms_id,
        "name":           t.name,
        "description":    t.description or "",
        "duration_days":  t.duration_days,
        "execution_type": t.execution_type,
        "order":          t.order,
        "assignee":       t.assignee or "",
        "jira_key":       t.jira_key or "",
        "created_at":     t.created_at,
    }


# ── Estimate endpoints ────────────────────────────────────────────────────────

@router.get("")
def list_estimates(db: Session = Depends(get_db)):
    rows = db.query(ProjEstimateORM).order_by(ProjEstimateORM.created_at.desc()).all()
    return [_est_out(r) for r in rows]


@router.post("", status_code=201)
def create_estimate(body: EstimateIn, db: Session = Depends(get_db)):
    if not body.name.strip():
        raise HTTPException(400, "name required")
    e = ProjEstimateORM(
        name=body.name.strip(),
        description=body.description,
        start_date=body.start_date,
        end_date_constraint=body.end_date_constraint,
        jira_project_key=body.jira_project_key or "",
        application_id=body.application_id,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return _est_out(e)


@router.get("/{est_id}")
def get_estimate(est_id: str, db: Session = Depends(get_db)):
    e = db.query(ProjEstimateORM).filter(ProjEstimateORM.est_id == est_id).first()
    if not e:
        raise HTTPException(404, "not found")
    milestones = db.query(ProjEstMilestoneORM).filter(ProjEstMilestoneORM.est_id == est_id).order_by(ProjEstMilestoneORM.order).all()
    tasks_all  = db.query(ProjEstTaskORM).filter(
        ProjEstTaskORM.ms_id.in_([m.ms_id for m in milestones])
    ).order_by(ProjEstTaskORM.order).all()

    tasks_by_ms: dict = {}
    for t in tasks_all:
        tasks_by_ms.setdefault(t.ms_id, []).append(t)

    timeline = _build_timeline(e, milestones, tasks_by_ms)

    ms_list = []
    for m in milestones:
        md = _ms_out(m)
        tl = next((x for x in timeline["milestones"] if x["ms_id"] == m.ms_id), {})
        md.update({
            "start_date": tl.get("start_date"),
            "end_date":   tl.get("end_date"),
            "duration":   tl.get("duration", 0),
            "tasks": [],
        })
        for t in tasks_by_ms.get(m.ms_id, []):
            td = _task_out(t)
            ttl = next((x for x in tl.get("tasks", []) if x["task_id"] == t.task_id), {})
            td.update({
                "start_date": ttl.get("start_date"),
                "end_date":   ttl.get("end_date"),
            })
            md["tasks"].append(td)
        ms_list.append(md)

    out = _est_out(e)
    out["milestones"] = ms_list
    out["timeline"] = timeline
    return out


@router.patch("/{est_id}")
def update_estimate(est_id: str, body: EstimateIn, db: Session = Depends(get_db)):
    e = db.query(ProjEstimateORM).filter(ProjEstimateORM.est_id == est_id).first()
    if not e:
        raise HTTPException(404, "not found")
    if body.name is not None:
        e.name = body.name.strip()
    if body.description is not None:
        e.description = body.description
    if body.start_date is not None:
        e.start_date = body.start_date
    e.end_date_constraint = body.end_date_constraint
    if body.jira_project_key is not None:
        e.jira_project_key = body.jira_project_key
    e.application_id = body.application_id
    db.commit()
    db.refresh(e)
    return _est_out(e)


@router.delete("/{est_id}", status_code=204)
def delete_estimate(est_id: str, db: Session = Depends(get_db)):
    e = db.query(ProjEstimateORM).filter(ProjEstimateORM.est_id == est_id).first()
    if not e:
        raise HTTPException(404, "not found")
    db.delete(e)
    db.commit()


# ── Milestone endpoints ───────────────────────────────────────────────────────

@router.get("/{est_id}/milestones")
def list_milestones(est_id: str, db: Session = Depends(get_db)):
    rows = db.query(ProjEstMilestoneORM).filter(ProjEstMilestoneORM.est_id == est_id).order_by(ProjEstMilestoneORM.order).all()
    return [_ms_out(r) for r in rows]


@router.post("/{est_id}/milestones", status_code=201)
def create_milestone(est_id: str, body: MilestoneIn, db: Session = Depends(get_db)):
    if not db.query(ProjEstimateORM).filter(ProjEstimateORM.est_id == est_id).first():
        raise HTTPException(404, "estimate not found")
    m = ProjEstMilestoneORM(
        est_id=est_id,
        name=body.name.strip(),
        description=body.description,
        order=body.order,
        execution_type=body.execution_type,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return _ms_out(m)


@router.patch("/{est_id}/milestones/{ms_id}")
def update_milestone(est_id: str, ms_id: str, body: MilestoneIn, db: Session = Depends(get_db)):
    m = db.query(ProjEstMilestoneORM).filter(
        ProjEstMilestoneORM.ms_id == ms_id,
        ProjEstMilestoneORM.est_id == est_id,
    ).first()
    if not m:
        raise HTTPException(404, "milestone not found")
    if body.name:
        m.name = body.name.strip()
    if body.description is not None:
        m.description = body.description
    m.order = body.order
    m.execution_type = body.execution_type
    db.commit()
    db.refresh(m)
    return _ms_out(m)


@router.delete("/{est_id}/milestones/{ms_id}", status_code=204)
def delete_milestone(est_id: str, ms_id: str, db: Session = Depends(get_db)):
    m = db.query(ProjEstMilestoneORM).filter(
        ProjEstMilestoneORM.ms_id == ms_id,
        ProjEstMilestoneORM.est_id == est_id,
    ).first()
    if not m:
        raise HTTPException(404, "milestone not found")
    db.delete(m)
    db.commit()


# ── Task endpoints ────────────────────────────────────────────────────────────

@router.get("/{est_id}/milestones/{ms_id}/tasks")
def list_tasks(ms_id: str, db: Session = Depends(get_db)):
    rows = db.query(ProjEstTaskORM).filter(ProjEstTaskORM.ms_id == ms_id).order_by(ProjEstTaskORM.order).all()
    return [_task_out(r) for r in rows]


@router.post("/{est_id}/milestones/{ms_id}/tasks", status_code=201)
def create_task(est_id: str, ms_id: str, body: TaskIn, db: Session = Depends(get_db)):
    if not db.query(ProjEstMilestoneORM).filter(ProjEstMilestoneORM.ms_id == ms_id, ProjEstMilestoneORM.est_id == est_id).first():
        raise HTTPException(404, "milestone not found")
    t = ProjEstTaskORM(
        ms_id=ms_id,
        name=body.name.strip(),
        description=body.description,
        duration_days=max(1, body.duration_days),
        execution_type=body.execution_type,
        order=body.order,
        assignee=body.assignee or "",
        jira_key=body.jira_key or "",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _task_out(t)


@router.patch("/{est_id}/milestones/{ms_id}/tasks/{task_id}")
def update_task(est_id: str, ms_id: str, task_id: str, body: TaskIn, db: Session = Depends(get_db)):
    t = db.query(ProjEstTaskORM).filter(
        ProjEstTaskORM.task_id == task_id,
        ProjEstTaskORM.ms_id == ms_id,
    ).first()
    if not t:
        raise HTTPException(404, "task not found")
    if body.name:
        t.name = body.name.strip()
    if body.description is not None:
        t.description = body.description
    t.duration_days  = max(1, body.duration_days)
    t.execution_type = body.execution_type
    t.order          = body.order
    if body.assignee is not None:
        t.assignee = body.assignee
    if body.jira_key is not None:
        t.jira_key = body.jira_key
    db.commit()
    db.refresh(t)
    return _task_out(t)


@router.delete("/{est_id}/milestones/{ms_id}/tasks/{task_id}", status_code=204)
def delete_task(est_id: str, ms_id: str, task_id: str, db: Session = Depends(get_db)):
    t = db.query(ProjEstTaskORM).filter(
        ProjEstTaskORM.task_id == task_id,
        ProjEstTaskORM.ms_id == ms_id,
    ).first()
    if not t:
        raise HTTPException(404, "task not found")
    db.delete(t)
    db.commit()


# ── Timeline recalculate ──────────────────────────────────────────────────────

@router.get("/{est_id}/timeline")
def get_timeline(est_id: str, db: Session = Depends(get_db)):
    e = db.query(ProjEstimateORM).filter(ProjEstimateORM.est_id == est_id).first()
    if not e:
        raise HTTPException(404, "not found")
    milestones = db.query(ProjEstMilestoneORM).filter(ProjEstMilestoneORM.est_id == est_id).order_by(ProjEstMilestoneORM.order).all()
    tasks_all = db.query(ProjEstTaskORM).filter(
        ProjEstTaskORM.ms_id.in_([m.ms_id for m in milestones])
    ).order_by(ProjEstTaskORM.order).all()
    tasks_by_ms: dict = {}
    for t in tasks_all:
        tasks_by_ms.setdefault(t.ms_id, []).append(t)
    return _build_timeline(e, milestones, tasks_by_ms)
