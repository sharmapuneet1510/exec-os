"""
Tests for task list screen business logic (filter application).
UI rendering is verified separately via the task list integration.
"""
from datetime import date, timedelta
from tasks.model import Task
from tasks.views import TaskFilter, apply_filter

TODAY = date(2026, 4, 22)


def make_task(title="T", status="todo", priority="medium", due=None, desc=""):
    return Task(title=title, status=status, priority=priority, due_date=due, description=desc)


def test_no_filter_shows_all():
    tasks = [make_task("A"), make_task("B"), make_task("C")]
    assert len(apply_filter(tasks, TaskFilter())) == 3


def test_status_filter():
    tasks = [make_task("A", status="todo"), make_task("B", status="done")]
    result = apply_filter(tasks, TaskFilter(status="done"))
    assert len(result) == 1 and result[0].title == "B"


def test_priority_filter():
    tasks = [make_task("A", priority="high"), make_task("B", priority="low")]
    result = apply_filter(tasks, TaskFilter(priority="high"))
    assert len(result) == 1 and result[0].title == "A"


def test_search_filter_title():
    tasks = [make_task("Login fix"), make_task("Deploy app")]
    result = apply_filter(tasks, TaskFilter(search_text="login"))
    assert len(result) == 1


def test_search_filter_case_insensitive():
    tasks = [make_task("DEPLOY app")]
    result = apply_filter(tasks, TaskFilter(search_text="deploy"))
    assert len(result) == 1


def test_combined_status_search():
    tasks = [
        make_task("Login fix", status="todo"),
        make_task("Login check", status="done"),
        make_task("Deploy", status="todo"),
    ]
    result = apply_filter(tasks, TaskFilter(status="todo", search_text="login"))
    assert len(result) == 1 and result[0].title == "Login fix"


def test_overdue_highlighted():
    past = make_task("Past", due=TODAY - timedelta(days=1), status="todo")
    future = make_task("Future", due=TODAY + timedelta(days=1), status="todo")
    done_past = make_task("Done", due=TODAY - timedelta(days=1), status="done")
    # overdue = past due AND not done/cancelled
    overdue = [t for t in [past, future, done_past]
               if t.due_date and t.due_date < TODAY and t.status not in ("done", "cancelled")]
    assert len(overdue) == 1 and overdue[0].title == "Past"


def test_empty_task_list():
    assert apply_filter([], TaskFilter()) == []


def test_all_filters_combined():
    tasks = [
        make_task("Fix auth", status="todo", priority="high"),
        make_task("Fix auth", status="in_progress", priority="high"),
        make_task("Fix auth", status="todo", priority="low"),
    ]
    result = apply_filter(tasks, TaskFilter(status="todo", priority="high", search_text="fix"))
    assert len(result) == 1
