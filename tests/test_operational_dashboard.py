from datetime import date, timedelta
import pytest
from dashboard.operational import (
    CommitmentSummary, MilestoneSummary, OperationalDashboard,
    OperationalDashboardService, TaskSummary,
)

TODAY = date(2026, 4, 22)
svc = OperationalDashboardService()

def task(tid, due=TODAY, overdue=False, blocked=False, completed=False):
    return TaskSummary(tid, f"Task {tid}", due_date=due, is_overdue=overdue,
                       is_blocked=blocked, is_completed=completed)

def commit(cid, days_ahead=3):
    return CommitmentSummary(cid, f"Commit {cid}", due_date=TODAY + timedelta(days=days_ahead))

def mile(mid, days_ahead=5):
    return MilestoneSummary(mid, f"Mile {mid}", due_date=TODAY + timedelta(days=days_ahead))

# OperationalDashboard model
def test_completion_rate_zero(): assert OperationalDashboard(TODAY).completion_rate == 0.0
def test_completion_rate(): d = OperationalDashboard(TODAY, 10, 7); assert d.completion_rate == 0.7
def test_overdue_count(): d = OperationalDashboard(TODAY, overdue_tasks=[task("t1"), task("t2")]); assert d.overdue_count == 2
def test_blocked_count(): d = OperationalDashboard(TODAY, blocked_tasks=[task("t1")]); assert d.blocked_count == 1
def test_to_dict_keys():
    d = OperationalDashboard(TODAY, 5, 3)
    keys = d.to_dict().keys()
    assert "completion_rate" in keys and "overdue_count" in keys

# Service
def test_build_empty():
    d = svc.build(TODAY, [])
    assert d.total_tasks_today == 0 and d.overdue_count == 0

def test_build_counts_today_tasks():
    tasks = [task("t1"), task("t2"), task("t3", due=TODAY - timedelta(days=1))]
    d = svc.build(TODAY, tasks)
    assert d.total_tasks_today == 3  # t3 is past-due so still included

def test_build_overdue_excluded_if_completed():
    tasks = [task("t1", overdue=True, completed=True), task("t2", overdue=True)]
    d = svc.build(TODAY, tasks)
    assert d.overdue_count == 1

def test_build_blocked():
    tasks = [task("t1", blocked=True), task("t2", blocked=True, completed=True)]
    d = svc.build(TODAY, tasks)
    assert d.blocked_count == 1

def test_build_upcoming_commitments():
    commits = [commit("c1", 3), commit("c2", 10)]  # c2 outside 7-day window
    d = svc.build(TODAY, [], commitments=commits)
    assert len(d.upcoming_commitments) == 1

def test_build_upcoming_milestones():
    miles = [mile("m1", 5), mile("m2", 8)]
    d = svc.build(TODAY, [], milestones=miles)
    assert len(d.upcoming_milestones) == 1

def test_build_as_of_date():
    d = svc.build(TODAY, [])
    assert d.as_of_date == TODAY
