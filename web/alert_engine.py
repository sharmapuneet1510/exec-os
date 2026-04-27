"""Auto-alert engine — runs on a schedule, creates alerts for actionable conditions."""

import logging
from datetime import date, datetime

from db.base import SessionLocal
from db.models import AlertORM, TaskORM, CommitmentORM, ProjectORM

log = logging.getLogger("execos.alerts")

# Severities
_CRITICAL = "critical"
_WARNING  = "warning"
_INFO     = "info"


def _exists(db, source_key: str) -> bool:
    """Return True if ANY auto-alert with this source key was created today (read or unread)."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return db.query(AlertORM).filter(
        AlertORM.source == source_key,
        AlertORM.created_at >= today_start,
    ).first() is not None


def _create(db, title: str, message: str, severity: str, source_key: str):
    if _exists(db, source_key):
        return
    db.add(AlertORM(title=title, message=message, severity=severity, source=source_key))


def run():
    """Scan DB for conditions and insert alert records. Idempotent — won't duplicate within same day."""
    db = SessionLocal()
    try:
        today = date.today()
        today_str = today.isoformat()

        # ── Overdue tasks ────────────────────────────────────────────────────
        overdue = db.query(TaskORM).filter(
            TaskORM.status.in_(["todo", "in_progress"]),
            TaskORM.due_date < today,
        ).all()
        for t in overdue:
            days = (today - t.due_date).days
            _create(db,
                title=f"Overdue: {t.title}",
                message=f"Due {t.due_date} — {days} day{'s' if days!=1 else ''} overdue",
                severity=_CRITICAL if days > 2 else _WARNING,
                source_key=f"auto:overdue:{t.task_id}:{today_str}",
            )

        # ── Tasks due today ───────────────────────────────────────────────────
        due_today = db.query(TaskORM).filter(
            TaskORM.status.in_(["todo", "in_progress"]),
            TaskORM.due_date == today,
        ).all()
        for t in due_today:
            _create(db,
                title=f"Due today: {t.title}",
                message=f"Priority: {t.priority}",
                severity=_WARNING if t.priority in ("high", "critical") else _INFO,
                source_key=f"auto:due_today:{t.task_id}:{today_str}",
            )

        # ── Missed commitments ────────────────────────────────────────────────
        missed = db.query(CommitmentORM).filter(
            CommitmentORM.status == "pending",
            CommitmentORM.due_date < today,
        ).all()
        for c in missed:
            _create(db,
                title=f"Missed commitment: {c.title}",
                message=f"Was due {c.due_date}",
                severity=_CRITICAL,
                source_key=f"auto:commitment_missed:{c.commitment_id}:{today_str}",
            )

        # ── Commitments due today ─────────────────────────────────────────────
        commit_today = db.query(CommitmentORM).filter(
            CommitmentORM.status == "pending",
            CommitmentORM.due_date == today,
        ).all()
        for c in commit_today:
            _create(db,
                title=f"Commitment due today: {c.title}",
                message="Mark as fulfilled once done",
                severity=_WARNING,
                source_key=f"auto:commitment_due:{c.commitment_id}:{today_str}",
            )

        # ── Projects with no activity and overdue milestones ──────────────────
        projects = db.query(ProjectORM).filter(ProjectORM.status == "active").all()
        from db.models import MilestoneORM
        for p in projects:
            overdue_ms = db.query(MilestoneORM).filter(
                MilestoneORM.project_id == p.project_id,
                MilestoneORM.status.in_(["pending", "in_progress"]),
                MilestoneORM.due_date < today,
            ).all()
            for m in overdue_ms:
                _create(db,
                    title=f"Milestone overdue: {m.title}",
                    message=f"Project: {p.name} — due {m.due_date}",
                    severity=_WARNING,
                    source_key=f"auto:milestone_overdue:{m.milestone_id}:{today_str}",
                )

        db.commit()
        log.info("Alert engine run complete")
    except Exception as e:
        log.error("Alert engine error: %s", e)
        db.rollback()
    finally:
        db.close()
