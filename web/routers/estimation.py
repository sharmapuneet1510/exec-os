import json
import math
from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.base import get_db
from db.models import EstimationORM

router = APIRouter(prefix="/api/estimations", tags=["estimations"])

# ── constants ────────────────────────────────────────────────────────────────

COMPLEXITY_MULT = {"low": 0.8, "medium": 1.0, "high": 1.3, "very_high": 1.8}
TESTING_MULT    = {"none": 1.0, "light": 1.2, "moderate": 1.5, "thorough": 2.0}
PAPERWORK_DAYS  = 2   # fixed overhead for release docs / sign-offs


# ── calculator ───────────────────────────────────────────────────────────────

def _add_working_days(start: date, working_days: int, holiday_set: set) -> tuple[date, int]:
    """Advance `start` by `working_days` working days, skipping weekends + holidays.
    Returns (end_date, actual_holiday_days_skipped)."""
    current = start
    remaining = working_days
    holidays_hit = 0
    while remaining > 0:
        current += timedelta(days=1)
        if current.weekday() >= 5:          # Saturday / Sunday
            continue
        if current in holiday_set:
            holidays_hit += 1
            continue
        remaining -= 1
    return current, holidays_hit


def calculate(
    story_points: int,
    complexity: str,
    testing_effort: str,
    has_release_paperwork: bool,
    velocity: int,
    start: date,
    holidays: List[str],
) -> dict:
    velocity = max(velocity, 1)

    c_mult = COMPLEXITY_MULT.get(complexity, 1.0)
    t_mult = TESTING_MULT.get(testing_effort, 1.0)

    raw_dev   = story_points / velocity                  # raw working days for dev
    dev_days  = math.ceil(raw_dev * c_mult)              # complexity-adjusted
    test_days = math.ceil(dev_days * (t_mult - 1))       # testing is additive
    paper_days = PAPERWORK_DAYS if has_release_paperwork else 0

    total_working = dev_days + test_days + paper_days

    holiday_set = set()
    for h in holidays:
        try:
            holiday_set.add(date.fromisoformat(h))
        except ValueError:
            pass

    end_date, holidays_skipped = _add_working_days(start, total_working, holiday_set)

    return {
        "dev_days": dev_days,
        "testing_days": test_days,
        "paperwork_days": paper_days,
        "holiday_buffer_days": holidays_skipped,
        "total_working_days": total_working,
        "total_calendar_days": (end_date - start).days,
        "estimated_end_date": end_date.isoformat(),
    }


# ── schemas ──────────────────────────────────────────────────────────────────

class EstimationIn(BaseModel):
    title: str
    story_points: int = Field(default=3, ge=1, le=100)
    complexity: str = "medium"
    testing_effort: str = "moderate"
    has_release_paperwork: bool = False
    velocity: int = Field(default=2, ge=1)
    start_date: Optional[date] = None
    holidays: List[str] = []
    task_id: Optional[str] = None
    project_id: Optional[str] = None


class EstimationCalcIn(BaseModel):
    story_points: int = Field(default=3, ge=1, le=100)
    complexity: str = "medium"
    testing_effort: str = "moderate"
    has_release_paperwork: bool = False
    velocity: int = Field(default=2, ge=1)
    start_date: Optional[date] = None
    holidays: List[str] = []


def _to_out(e: EstimationORM) -> dict:
    return {
        "estimation_id": e.estimation_id,
        "title": e.title,
        "task_id": e.task_id,
        "project_id": e.project_id,
        "story_points": e.story_points,
        "complexity": e.complexity,
        "testing_effort": e.testing_effort,
        "has_release_paperwork": e.has_release_paperwork,
        "velocity": e.velocity,
        "start_date": e.start_date,
        "holidays": json.loads(e.holidays or "[]"),
        "dev_days": e.dev_days,
        "testing_days": e.testing_days,
        "paperwork_days": e.paperwork_days,
        "holiday_buffer_days": e.holiday_buffer_days,
        "total_working_days": e.total_working_days,
        "estimated_end_date": e.estimated_end_date,
        "created_at": e.created_at,
    }


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/calculate")
def calculate_estimate(body: EstimationCalcIn):
    """Live calculator — computes estimate without saving."""
    start = body.start_date or date.today()
    return calculate(
        story_points=body.story_points,
        complexity=body.complexity,
        testing_effort=body.testing_effort,
        has_release_paperwork=body.has_release_paperwork,
        velocity=body.velocity,
        start=start,
        holidays=body.holidays,
    )


@router.get("")
def list_estimations(project_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(EstimationORM)
    if project_id:
        q = q.filter(EstimationORM.project_id == project_id)
    return [_to_out(e) for e in q.order_by(EstimationORM.created_at.desc()).all()]


@router.post("", status_code=201)
def create_estimation(body: EstimationIn, db: Session = Depends(get_db)):
    if not body.title.strip():
        raise HTTPException(400, "title required")

    start = body.start_date or date.today()
    result = calculate(
        story_points=body.story_points,
        complexity=body.complexity,
        testing_effort=body.testing_effort,
        has_release_paperwork=body.has_release_paperwork,
        velocity=body.velocity,
        start=start,
        holidays=body.holidays,
    )

    e = EstimationORM(
        title=body.title.strip(),
        task_id=body.task_id,
        project_id=body.project_id,
        story_points=body.story_points,
        complexity=body.complexity,
        testing_effort=body.testing_effort,
        has_release_paperwork=body.has_release_paperwork,
        velocity=body.velocity,
        start_date=start,
        holidays=json.dumps(body.holidays),
        dev_days=result["dev_days"],
        testing_days=result["testing_days"],
        paperwork_days=result["paperwork_days"],
        holiday_buffer_days=result["holiday_buffer_days"],
        total_working_days=result["total_working_days"],
        estimated_end_date=date.fromisoformat(result["estimated_end_date"]),
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return _to_out(e)


@router.delete("/{estimation_id}", status_code=204)
def delete_estimation(estimation_id: str, db: Session = Depends(get_db)):
    e = db.query(EstimationORM).filter(EstimationORM.estimation_id == estimation_id).first()
    if not e:
        raise HTTPException(404, "not found")
    db.delete(e)
    db.commit()
