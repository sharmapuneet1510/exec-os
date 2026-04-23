from datetime import date, timedelta
import pytest
from tasks.model import Task
from tasks.store import JSONTaskStore
from tasks.service import TaskService
from tasks.views import SavedViewStore, TaskFilter, TaskViewService, apply_filter

TODAY = date(2026, 4, 22)


@pytest.fixture
def svc(tmp_path):
    return TaskService(store=JSONTaskStore(tmp_path / "tasks"))


@pytest.fixture
def vs(svc, tmp_path):
    return TaskViewService(svc, view_store=SavedViewStore(tmp_path / "views"))


def make_task(**kwargs):
    defaults = dict(title="T", status="todo", priority="medium", due_date=None, description="", tags=[])
    defaults.update(kwargs)
    t = Task(**defaults)
    return t


# apply_filter — pure function tests
def test_filter_by_status():
    tasks = [make_task(title="A", status="todo"), make_task(title="B", status="done")]
    assert len(apply_filter(tasks, TaskFilter(status="done"))) == 1


def test_filter_by_priority():
    tasks = [make_task(priority="high"), make_task(priority="low")]
    assert len(apply_filter(tasks, TaskFilter(priority="high"))) == 1


def test_filter_by_project():
    tasks = [make_task(project_id="p1"), make_task(project_id="p2")]
    assert len(apply_filter(tasks, TaskFilter(project_id="p1"))) == 1


def test_filter_search_title():
    tasks = [make_task(title="Fix login"), make_task(title="Deploy app")]
    assert len(apply_filter(tasks, TaskFilter(search_text="login"))) == 1


def test_filter_search_description():
    tasks = [make_task(title="A", description="refactor auth"), make_task(title="B")]
    assert len(apply_filter(tasks, TaskFilter(search_text="auth"))) == 1


def test_filter_search_case_insensitive():
    tasks = [make_task(title="Fix LOGIN")]
    assert len(apply_filter(tasks, TaskFilter(search_text="login"))) == 1


def test_filter_overdue_only():
    tasks = [
        make_task(due_date=TODAY - timedelta(days=1), status="todo"),
        make_task(due_date=TODAY + timedelta(days=1), status="todo"),
    ]
    assert len(apply_filter(tasks, TaskFilter(overdue_only=True), as_of=TODAY)) == 1


def test_filter_overdue_excludes_done():
    tasks = [make_task(due_date=TODAY - timedelta(days=1), status="done")]
    assert apply_filter(tasks, TaskFilter(overdue_only=True), as_of=TODAY) == []


def test_filter_due_before():
    tasks = [
        make_task(due_date=TODAY + timedelta(days=1)),
        make_task(due_date=TODAY + timedelta(days=10)),
    ]
    assert len(apply_filter(tasks, TaskFilter(due_before=TODAY + timedelta(days=5)))) == 1


def test_filter_tags():
    tasks = [make_task(tags=["urgent"]), make_task(tags=["low"])]
    assert len(apply_filter(tasks, TaskFilter(tags=["urgent"]))) == 1


def test_filter_tags_any_match():
    tasks = [make_task(tags=["a", "b"]), make_task(tags=["c"])]
    assert len(apply_filter(tasks, TaskFilter(tags=["b", "c"]))) == 2


def test_filter_empty_returns_all():
    tasks = [make_task(), make_task(title="X")]
    assert len(apply_filter(tasks, TaskFilter())) == 2


def test_filter_compose_status_and_priority():
    tasks = [
        make_task(status="todo", priority="high"),
        make_task(status="done", priority="high"),
        make_task(status="todo", priority="low"),
    ]
    result = apply_filter(tasks, TaskFilter(status="todo", priority="high"))
    assert len(result) == 1


# TaskFilter round-trip
def test_task_filter_round_trip():
    f = TaskFilter(status="todo", priority="high", search_text="fix", overdue_only=True,
                   due_before=TODAY, tags=["urgent"])
    f2 = TaskFilter.from_dict(f.to_dict())
    assert f2.status == "todo"
    assert f2.priority == "high"
    assert f2.search_text == "fix"
    assert f2.overdue_only is True
    assert f2.due_before == TODAY
    assert f2.tags == ["urgent"]


# TaskViewService
def test_search_returns_filtered(svc, vs):
    svc.create("Login fix", priority="high")
    svc.create("Deploy")
    result = vs.search(TaskFilter(search_text="login"))
    assert len(result) == 1


def test_save_view(svc, vs):
    view = vs.save_view("High priority", TaskFilter(priority="high"))
    assert view.view_id
    assert view.name == "High priority"


def test_save_view_empty_name_raises(vs):
    with pytest.raises(ValueError):
        vs.save_view("", TaskFilter())


def test_save_view_blank_name_raises(vs):
    with pytest.raises(ValueError):
        vs.save_view("   ", TaskFilter())


def test_get_view(vs):
    view = vs.save_view("My view", TaskFilter(status="todo"))
    loaded = vs.get_view(view.view_id)
    assert loaded is not None and loaded.name == "My view"


def test_get_view_missing(vs):
    assert vs.get_view("nope") is None


def test_delete_view(vs):
    view = vs.save_view("Del", TaskFilter())
    assert vs.delete_view(view.view_id) is True
    assert vs.get_view(view.view_id) is None


def test_delete_view_missing(vs):
    assert vs.delete_view("ghost") is False


def test_list_views(vs):
    vs.save_view("V1", TaskFilter())
    vs.save_view("V2", TaskFilter())
    assert len(vs.list_views()) == 2


def test_execute_view(svc, vs):
    svc.create("Critical task", priority="critical")
    svc.create("Low task", priority="low")
    view = vs.save_view("Criticals", TaskFilter(priority="critical"))
    result = vs.execute_view(view.view_id)
    assert len(result) == 1 and result[0].priority == "critical"


def test_execute_view_missing_raises(vs):
    with pytest.raises(KeyError):
        vs.execute_view("ghost")
