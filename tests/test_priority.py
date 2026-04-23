from datetime import date, timedelta
import pytest
from tasks.model import Task
from tasks.store import JSONTaskStore
from tasks.service import TaskService
from tasks.priority import (
    DueDateService, boost_priority, compare_priority,
    days_until_due, is_due_soon, is_overdue, lower_priority,
)

TODAY = date(2026, 4, 22)


@pytest.fixture
def svc(tmp_path):
    return TaskService(store=JSONTaskStore(tmp_path))


@pytest.fixture
def dd(svc):
    return DueDateService(svc)


def task(title="T", due=None, status="todo", priority="medium"):
    t = Task(title=title, due_date=due, status=status, priority=priority)
    return t


# is_overdue
def test_overdue_past_due():
    assert is_overdue(task(due=TODAY - timedelta(days=1)), TODAY) is True


def test_overdue_today_not_overdue():
    assert is_overdue(task(due=TODAY), TODAY) is False


def test_overdue_future_not_overdue():
    assert is_overdue(task(due=TODAY + timedelta(days=1)), TODAY) is False


def test_overdue_no_due_date():
    assert is_overdue(task(), TODAY) is False


def test_overdue_done_not_overdue():
    assert is_overdue(task(due=TODAY - timedelta(days=5), status="done"), TODAY) is False


def test_overdue_cancelled_not_overdue():
    assert is_overdue(task(due=TODAY - timedelta(days=5), status="cancelled"), TODAY) is False


# is_due_soon
def test_due_soon_today():
    assert is_due_soon(task(due=TODAY), TODAY) is True


def test_due_soon_within_window():
    assert is_due_soon(task(due=TODAY + timedelta(days=2)), TODAY, window_days=3) is True


def test_due_soon_outside_window():
    assert is_due_soon(task(due=TODAY + timedelta(days=5)), TODAY, window_days=3) is False


def test_due_soon_past_not_soon():
    assert is_due_soon(task(due=TODAY - timedelta(days=1)), TODAY) is False


def test_due_soon_done_not_soon():
    assert is_due_soon(task(due=TODAY, status="done"), TODAY) is False


# days_until_due
def test_days_until_future():
    assert days_until_due(task(due=TODAY + timedelta(days=7)), TODAY) == 7


def test_days_until_overdue():
    assert days_until_due(task(due=TODAY - timedelta(days=2)), TODAY) == -2


def test_days_until_no_due_date():
    assert days_until_due(task(), TODAY) is None


# compare_priority
def test_compare_higher():
    assert compare_priority("high", "low") > 0


def test_compare_lower():
    assert compare_priority("low", "high") < 0


def test_compare_equal():
    assert compare_priority("medium", "medium") == 0


# boost / lower
def test_boost_priority():
    assert boost_priority("low") == "medium"
    assert boost_priority("medium") == "high"
    assert boost_priority("high") == "critical"
    assert boost_priority("critical") == "critical"  # capped


def test_lower_priority():
    assert lower_priority("critical") == "high"
    assert lower_priority("high") == "medium"
    assert lower_priority("medium") == "low"
    assert lower_priority("low") == "low"  # floored


# DueDateService
def test_set_due_date(svc, dd):
    t = svc.create("Task")
    dd.set_due_date(t.task_id, TODAY)
    assert svc.get(t.task_id).due_date == TODAY


def test_set_due_date_clear(svc, dd):
    t = svc.create("Task", due_date=TODAY)
    dd.set_due_date(t.task_id, None)
    assert svc.get(t.task_id).due_date is None


def test_set_due_date_missing_raises(dd):
    with pytest.raises(KeyError):
        dd.set_due_date("nope", TODAY)


def test_set_priority(svc, dd):
    t = svc.create("Task")
    dd.set_priority(t.task_id, "critical")
    assert svc.get(t.task_id).priority == "critical"


def test_set_invalid_priority_raises(svc, dd):
    t = svc.create("Task")
    with pytest.raises(ValueError):
        dd.set_priority(t.task_id, "extreme")


def test_set_priority_missing_raises(dd):
    with pytest.raises(KeyError):
        dd.set_priority("ghost", "high")


def test_overdue_tasks(svc, dd):
    svc.create("Past", due_date=TODAY - timedelta(days=1))
    svc.create("Future", due_date=TODAY + timedelta(days=1))
    assert len(dd.overdue_tasks(TODAY)) == 1


def test_due_soon_tasks(svc, dd):
    svc.create("Soon", due_date=TODAY + timedelta(days=2))
    svc.create("Far", due_date=TODAY + timedelta(days=10))
    assert len(dd.due_soon_tasks(TODAY, window_days=3)) == 1


def test_sorted_by_priority(svc, dd):
    svc.create("Low", priority="low")
    svc.create("Critical", priority="critical")
    svc.create("Medium", priority="medium")
    sorted_tasks = dd.sorted_by_priority()
    priorities = [t.priority for t in sorted_tasks]
    assert priorities == ["critical", "medium", "low"]
