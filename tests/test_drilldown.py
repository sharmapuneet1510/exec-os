from datetime import date
from dashboard.drilldown import DrillDownFilter, DrillDownService
from dashboard.operational import TaskSummary
TODAY = date(2026,4,22)
svc = DrillDownService()
tasks = [
    TaskSummary("t1","Fix login",TODAY,is_overdue=True),
    TaskSummary("t2","Build API",TODAY,is_blocked=True),
    TaskSummary("t3","Write docs",TODAY,is_completed=True),
    TaskSummary("t4","Deploy app",TODAY),
]
def test_all(): assert len(svc.filtered_tasks(tasks, DrillDownFilter("all"))) == 4
def test_overdue(): r = svc.filtered_tasks(tasks, DrillDownFilter("overdue")); assert len(r)==1 and r[0].task_id=="t1"
def test_blocked(): r = svc.filtered_tasks(tasks, DrillDownFilter("blocked")); assert len(r)==1 and r[0].task_id=="t2"
def test_completed(): r = svc.filtered_tasks(tasks, DrillDownFilter("completed")); assert len(r)==1 and r[0].task_id=="t3"
def test_search(): r = svc.filtered_tasks(tasks, DrillDownFilter("all",search_text="login")); assert len(r)==1
def test_search_case_insensitive(): r = svc.filtered_tasks(tasks, DrillDownFilter("all",search_text="API")); assert len(r)==1
def test_overdue_excludes_completed():
    t = [TaskSummary("t5","Old",TODAY,is_overdue=True,is_completed=True)]
    assert svc.filtered_tasks(t, DrillDownFilter("overdue")) == []
def test_empty_input(): assert svc.filtered_tasks([], DrillDownFilter("overdue")) == []
