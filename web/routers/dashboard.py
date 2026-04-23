import json
from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.base import get_db
from db.models import TaskORM, ProjectORM, MilestoneORM, CommitmentORM, AlertORM
from web.deps import get_redis

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

CACHE_TTL = 60  # seconds


@router.get("/operational")
def operational_dashboard(db: Session = Depends(get_db)):
    redis = get_redis()
    cache_key = "dashboard:operational"
    cached = redis.get(cache_key)
    if cached:
        return json.loads(cached)

    today = date.today()
    all_tasks = db.query(TaskORM).all()

    total = len(all_tasks)
    done_today = sum(1 for t in all_tasks if t.status == "done" and t.completed_at and t.completed_at.date() == today)
    overdue = [
        {"task_id": t.task_id, "title": t.title, "due_date": t.due_date.isoformat(), "priority": t.priority}
        for t in all_tasks
        if t.due_date and t.due_date < today and t.status not in ("done", "cancelled")
    ]
    in_progress = [
        {"task_id": t.task_id, "title": t.title, "priority": t.priority}
        for t in all_tasks if t.status == "in_progress"
    ]
    upcoming = [
        {"task_id": t.task_id, "title": t.title, "due_date": t.due_date.isoformat(), "priority": t.priority}
        for t in all_tasks
        if t.due_date and today <= t.due_date <= today + timedelta(days=7) and t.status not in ("done", "cancelled")
    ]

    milestones = db.query(MilestoneORM).filter(
        MilestoneORM.due_date >= today,
        MilestoneORM.due_date <= today + timedelta(days=14),
        MilestoneORM.status == "pending",
    ).all()

    commitments = db.query(CommitmentORM).filter(
        CommitmentORM.status == "pending",
        CommitmentORM.due_date >= today,
        CommitmentORM.due_date <= today + timedelta(days=7),
    ).all()

    unread_alerts = db.query(AlertORM).filter(AlertORM.is_read == False).count()  # noqa: E712

    result = {
        "as_of": today.isoformat(),
        "total_tasks": total,
        "done_today": done_today,
        "completion_rate": round(done_today / total, 2) if total else 0,
        "overdue_count": len(overdue),
        "overdue_tasks": overdue[:10],
        "in_progress_count": len(in_progress),
        "in_progress_tasks": in_progress[:10],
        "upcoming_tasks": upcoming[:10],
        "upcoming_milestones": [
            {"milestone_id": m.milestone_id, "title": m.title, "due_date": m.due_date.isoformat()}
            for m in milestones
        ],
        "upcoming_commitments": [
            {"commitment_id": c.commitment_id, "title": c.title, "due_date": c.due_date.isoformat() if c.due_date else None}
            for c in commitments
        ],
        "unread_alerts": unread_alerts,
    }

    redis.setex(cache_key, CACHE_TTL, json.dumps(result, default=str))
    return result


@router.get("/executive")
def executive_dashboard(db: Session = Depends(get_db)):
    redis = get_redis()
    cache_key = "dashboard:executive"
    cached = redis.get(cache_key)
    if cached:
        return json.loads(cached)

    today = date.today()
    projects = db.query(ProjectORM).filter(ProjectORM.status.in_(["active", "on_hold"])).all()

    project_health = []
    total_overdue = 0
    for p in projects:
        tasks = db.query(TaskORM).filter(TaskORM.project_id == p.project_id).all()
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == "done")
        overdue = sum(1 for t in tasks if t.due_date and t.due_date < today and t.status not in ("done", "cancelled"))
        total_overdue += overdue
        pct = round(completed / total * 100) if total else 0
        health = "green" if overdue == 0 and pct >= 50 else ("yellow" if overdue <= 2 else "red")
        project_health.append({
            "project_id": p.project_id,
            "name": p.name,
            "completion_pct": pct,
            "task_count": total,
            "overdue_count": overdue,
            "health": health,
            "status": p.status,
        })

    commitments = db.query(CommitmentORM).all()
    total_c = len(commitments)
    missed_c = sum(1 for c in commitments if c.status == "missed")
    due_soon_c = sum(1 for c in commitments if c.due_date and today <= c.due_date <= today + timedelta(days=7) and c.status == "pending")

    milestones = db.query(MilestoneORM).all()
    overdue_milestones = sum(1 for m in milestones if m.due_date and m.due_date < today and m.status == "pending")

    result = {
        "as_of": today.isoformat(),
        "projects_total": len(projects),
        "projects_at_risk": sum(1 for p in project_health if p["health"] == "red"),
        "projects_on_track": sum(1 for p in project_health if p["health"] == "green"),
        "project_health": project_health,
        "total_overdue_tasks": total_overdue,
        "overdue_milestones": overdue_milestones,
        "commitment_total": total_c,
        "commitment_missed": missed_c,
        "commitment_due_soon": due_soon_c,
        "commitment_risk_score": round((missed_c + due_soon_c * 0.5) / total_c, 2) if total_c else 0,
    }

    redis.setex(cache_key, CACHE_TTL, json.dumps(result, default=str))
    return result


@router.get("/sod")
def sod_summary(db: Session = Depends(get_db)):
    today = date.today()
    all_tasks = db.query(TaskORM).all()
    overdue = [t for t in all_tasks if t.due_date and t.due_date < today and t.status not in ("done", "cancelled")]
    due_today = [t for t in all_tasks if t.due_date == today and t.status not in ("done", "cancelled")]
    carry_forward = [t for t in all_tasks if t.status == "in_progress"]

    return {
        "date": today.isoformat(),
        "overdue_count": len(overdue),
        "due_today_count": len(due_today),
        "carry_forward_count": len(carry_forward),
        "overdue": [{"task_id": t.task_id, "title": t.title, "priority": t.priority} for t in overdue[:10]],
        "due_today": [{"task_id": t.task_id, "title": t.title, "priority": t.priority} for t in due_today[:10]],
        "carry_forward": [{"task_id": t.task_id, "title": t.title} for t in carry_forward[:10]],
    }


@router.get("/eod")
def eod_summary(db: Session = Depends(get_db)):
    today = date.today()
    all_tasks = db.query(TaskORM).all()
    completed_today = [t for t in all_tasks if t.completed_at and t.completed_at.date() == today]
    pending = [t for t in all_tasks if t.status in ("todo", "in_progress") and t.due_date and t.due_date <= today]

    return {
        "date": today.isoformat(),
        "completed_today": len(completed_today),
        "still_pending": len(pending),
        "completed": [{"task_id": t.task_id, "title": t.title} for t in completed_today[:20]],
        "pending": [{"task_id": t.task_id, "title": t.title, "priority": t.priority} for t in pending[:10]],
    }
