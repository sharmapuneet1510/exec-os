"""Pure derivation of release status, current stage, and gate breach health."""
from datetime import date
from typing import Optional

RISK_WINDOW = 3
STAGES = ["requirement_gathering", "development", "qa", "uat", "in_prod"]


def _stage_index(stage: Optional[str]) -> int:
    try:
        return STAGES.index(stage)
    except (ValueError, TypeError):
        return len(STAGES)


def derive_status(items) -> str:
    items = list(items)
    if not items:
        return "TODO"
    required = [i for i in items if i.is_required]
    if required and all(i.status in ("done", "skipped") for i in required):
        return "COMPLETED"
    if any(i.status in ("in_progress", "done") for i in items):
        return "IN_PROGRESS"
    return "TODO"


def current_stage(items) -> str:
    pending = [i for i in items if i.is_required and i.status not in ("done", "skipped")]
    if not pending:
        return "in_prod"
    pending.sort(key=lambda i: _stage_index(i.stage))
    return pending[0].stage or "development"


def item_health(item, today: date, risk_window: int = RISK_WINDOW) -> dict:
    if item.status in ("done", "skipped"):
        return {"state": "done", "days": 0}
    planned = item.planned_date
    if planned is None:
        return {"state": "unset", "days": 0}
    if planned < today:
        return {"state": "breached", "days": (today - planned).days}
    delta = (planned - today).days
    if 0 <= delta <= risk_window and item.status == "pending":
        return {"state": "at_risk", "days": delta}
    return {"state": "upcoming", "days": delta}


def release_health(items, today: date, risk_window: int = RISK_WINDOW) -> dict:
    items = sorted(items, key=lambda i: (_stage_index(i.stage), i.order))
    gates, any_breach, any_risk = [], False, False
    for i in items:
        h = item_health(i, today, risk_window)
        any_breach = any_breach or h["state"] == "breached"
        any_risk = any_risk or h["state"] == "at_risk"
        gates.append({
            "item_id": i.item_id, "title": i.title, "stage": i.stage,
            "planned_date": i.planned_date.isoformat() if i.planned_date else None,
            "completed_at": i.completed_at.isoformat() if i.completed_at else None,
            "state": h["state"], "days": h["days"],
        })
    level = "breached" if any_breach else "at_risk" if any_risk else "on_track"
    return {"level": level, "derived_status": derive_status(items),
            "current_stage": current_stage(items), "items": gates}
