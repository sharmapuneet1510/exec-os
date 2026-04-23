from datetime import date, timedelta
import pytest
from tasks.model import Task
from projects.health import ProjectHealth, ProjectHealthService

TODAY = date(2026, 4, 22)
svc = ProjectHealthService()


def make_task(pid="p1", status="todo", priority="medium", due=None):
    return Task(title="T", project_id=pid, status=status, priority=priority, due_date=due)


# ProjectHealth
def test_completion_rate_zero():
    assert ProjectHealth("p1").completion_rate == 0.0


def test_completion_rate():
    h = ProjectHealth("p1", total_tasks=10, completed_tasks=7)
    assert h.completion_rate == 0.7


def test_completion_rate_all():
    h = ProjectHealth("p1", total_tasks=5, completed_tasks=5)
    assert h.completion_rate == 1.0


def test_is_at_risk_overdue_pct():
    h = ProjectHealth("p1", total_tasks=5, overdue_tasks=1)  # 20%
    assert h.is_at_risk is True


def test_is_at_risk_blocked():
    h = ProjectHealth("p1", total_tasks=10, blocked_tasks=3)
    assert h.is_at_risk is True


def test_not_at_risk():
    h = ProjectHealth("p1", total_tasks=10, overdue_tasks=1, blocked_tasks=1)
    assert h.is_at_risk is False


def test_health_label_healthy():
    h = ProjectHealth("p1", total_tasks=10, completed_tasks=9)
    assert h.health_label == "healthy"


def test_health_label_moderate():
    h = ProjectHealth("p1", total_tasks=10, completed_tasks=6)
    assert h.health_label == "moderate"


def test_health_label_poor():
    h = ProjectHealth("p1", total_tasks=10, completed_tasks=2)
    assert h.health_label == "poor"


def test_health_label_at_risk():
    h = ProjectHealth("p1", total_tasks=5, overdue_tasks=1)
    assert h.health_label == "at_risk"


def test_to_dict_keys():
    keys = ProjectHealth("p1").to_dict().keys()
    assert "completion_rate" in keys and "health_label" in keys and "is_at_risk" in keys


# ProjectHealthService
def test_compute_empty():
    h = svc.compute("p1", [], as_of=TODAY)
    assert h.total_tasks == 0


def test_compute_filters_by_project():
    tasks = [make_task("p1"), make_task("p2"), make_task("p1")]
    h = svc.compute("p1", tasks, as_of=TODAY)
    assert h.total_tasks == 2


def test_compute_completed_count():
    tasks = [make_task("p1", status="done"), make_task("p1", status="todo")]
    h = svc.compute("p1", tasks, as_of=TODAY)
    assert h.completed_tasks == 1


def test_compute_overdue_count():
    tasks = [
        make_task("p1", due=TODAY - timedelta(days=1)),
        make_task("p1", due=TODAY + timedelta(days=1)),
        make_task("p1", status="done", due=TODAY - timedelta(days=1)),
    ]
    h = svc.compute("p1", tasks, as_of=TODAY)
    assert h.overdue_tasks == 1


def test_compute_overdue_excludes_done():
    tasks = [make_task("p1", status="done", due=TODAY - timedelta(days=1))]
    h = svc.compute("p1", tasks, as_of=TODAY)
    assert h.overdue_tasks == 0


def test_compute_blocked_critical_in_progress():
    tasks = [make_task("p1", status="in_progress", priority="critical")]
    h = svc.compute("p1", tasks, as_of=TODAY)
    assert h.blocked_tasks == 1


def test_compute_all():
    tasks = [make_task("p1"), make_task("p2")]
    results = svc.compute_all(["p1", "p2"], tasks, as_of=TODAY)
    assert len(results) == 2
    assert {r.project_id for r in results} == {"p1", "p2"}
