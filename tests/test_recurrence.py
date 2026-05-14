from datetime import date, timedelta
import pytest
from tasks.model import Task
from tasks.store import JSONTaskStore
from tasks.service import TaskService
from tasks.recurrence import PostponeRecord, PostponeService, RecurrenceRule

TODAY = date(2026, 4, 22)


@pytest.fixture
def svc(tmp_path):
    return TaskService(store=JSONTaskStore(tmp_path))


@pytest.fixture
def ps(svc):
    return PostponeService(svc)


# PostponeRecord
def test_postpone_record_round_trip():
    r = PostponeRecord(from_date=TODAY, to_date=TODAY + timedelta(days=3), reason="sick")
    r2 = PostponeRecord.from_dict(r.to_dict())
    assert r2.from_date == TODAY
    assert r2.to_date == TODAY + timedelta(days=3)
    assert r2.reason == "sick"


def test_postpone_record_no_reason():
    r = PostponeRecord(from_date=TODAY, to_date=TODAY + timedelta(days=1))
    assert r.reason == ""


# RecurrenceRule — next_occurrence
def test_daily():
    rule = RecurrenceRule("daily")
    assert rule.next_occurrence(TODAY) == TODAY + timedelta(days=1)


def test_daily_interval():
    rule = RecurrenceRule("daily", interval=3)
    assert rule.next_occurrence(TODAY) == TODAY + timedelta(days=3)


def test_weekly():
    rule = RecurrenceRule("weekly")
    assert rule.next_occurrence(TODAY) == TODAY + timedelta(weeks=1)


def test_biweekly():
    rule = RecurrenceRule("biweekly")
    assert rule.next_occurrence(TODAY) == TODAY + timedelta(weeks=2)


def test_monthly():
    rule = RecurrenceRule("monthly")
    d = date(2026, 1, 31)
    nxt = rule.next_occurrence(d)
    assert nxt == date(2026, 2, 28)  # clamped to last day of Feb


def test_monthly_normal():
    rule = RecurrenceRule("monthly")
    assert rule.next_occurrence(date(2026, 3, 15)) == date(2026, 4, 15)


def test_end_date_respected():
    rule = RecurrenceRule("daily", end_date=TODAY)
    assert rule.next_occurrence(TODAY) is None


def test_end_date_boundary():
    rule = RecurrenceRule("daily", end_date=TODAY + timedelta(days=1))
    assert rule.next_occurrence(TODAY) == TODAY + timedelta(days=1)


def test_recurrence_round_trip():
    rule = RecurrenceRule("weekly", interval=2, end_date=TODAY)
    rule2 = RecurrenceRule.from_dict(rule.to_dict())
    assert rule2.frequency == "weekly"
    assert rule2.interval == 2
    assert rule2.end_date == TODAY


def test_recurrence_round_trip_no_end():
    rule = RecurrenceRule("monthly")
    assert RecurrenceRule.from_dict(rule.to_dict()).end_date is None


# PostponeService
def test_postpone(svc, ps):
    t = svc.create("Task", due_date=TODAY)
    ps.postpone(t.task_id, TODAY + timedelta(days=3), "need more time")
    assert svc.get(t.task_id).due_date == TODAY + timedelta(days=3)


def test_postpone_updates_due_date(svc, ps):
    t = svc.create("Task", due_date=TODAY)
    ps.postpone(t.task_id, TODAY + timedelta(days=7))
    assert svc.get(t.task_id).due_date == TODAY + timedelta(days=7)


def test_postpone_no_due_date_raises(svc, ps):
    t = svc.create("No due")
    with pytest.raises(ValueError):
        ps.postpone(t.task_id, TODAY)


def test_postpone_missing_task_raises(ps):
    with pytest.raises(KeyError):
        ps.postpone("ghost", TODAY)


def test_postpone_count(svc, ps):
    t = svc.create("Task", due_date=TODAY)
    ps.postpone(t.task_id, TODAY + timedelta(days=1))
    ps.postpone(t.task_id, TODAY + timedelta(days=2))
    assert ps.postpone_count(t.task_id) == 2


def test_postpone_history(svc, ps):
    t = svc.create("Task", due_date=TODAY)
    ps.postpone(t.task_id, TODAY + timedelta(days=1), "reason A")
    history = ps.postpone_history(t.task_id)
    assert len(history) == 1
    assert history[0].reason == "reason A"
    assert history[0].from_date == TODAY


def test_postpone_history_empty(svc, ps):
    t = svc.create("Task", due_date=TODAY)
    assert ps.postpone_history(t.task_id) == []


def test_multiple_postpones_tracked(svc, ps):
    t = svc.create("Task", due_date=TODAY)
    ps.postpone(t.task_id, TODAY + timedelta(days=2))
    ps.postpone(t.task_id, TODAY + timedelta(days=5))
    history = ps.postpone_history(t.task_id)
    assert len(history) == 2
    assert history[0].from_date == TODAY
    assert history[1].from_date == TODAY + timedelta(days=2)
