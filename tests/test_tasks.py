from datetime import date
import pytest
from tasks.model import Task
from tasks.store import JSONTaskStore
from tasks.service import TaskService


@pytest.fixture
def svc(tmp_path):
    return TaskService(store=JSONTaskStore(tmp_path))


# Model
def test_task_defaults():
    t = Task(title="Do something")
    assert t.status == "todo"
    assert t.priority == "medium"
    assert t.tags == []


def test_task_round_trip():
    t = Task(title="X", due_date=date(2026, 5, 1), priority="high", tags=["a"])
    t2 = Task.from_dict(t.to_dict())
    assert t2.title == "X"
    assert t2.due_date == date(2026, 5, 1)
    assert t2.priority == "high"
    assert t2.tags == ["a"]


def test_task_round_trip_no_due_date():
    t = Task(title="No date")
    assert Task.from_dict(t.to_dict()).due_date is None


# Store
def test_store_save_load(tmp_path):
    store = JSONTaskStore(tmp_path)
    t = Task(title="Test")
    store.save(t)
    loaded = store.load(t.task_id)
    assert loaded is not None and loaded.title == "Test"


def test_store_load_missing(tmp_path):
    assert JSONTaskStore(tmp_path).load("nonexistent") is None


def test_store_delete(tmp_path):
    store = JSONTaskStore(tmp_path)
    t = Task(title="Del")
    store.save(t)
    assert store.delete(t.task_id) is True
    assert store.load(t.task_id) is None


def test_store_delete_missing(tmp_path):
    assert JSONTaskStore(tmp_path).delete("ghost") is False


def test_store_all(tmp_path):
    store = JSONTaskStore(tmp_path)
    store.save(Task(title="A"))
    store.save(Task(title="B"))
    assert len(store.all()) == 2


# Service — create
def test_create(svc):
    t = svc.create("Buy milk")
    assert t.title == "Buy milk"
    assert t.task_id


def test_create_strips_whitespace(svc):
    t = svc.create("  hello  ")
    assert t.title == "hello"


def test_create_empty_title_raises(svc):
    with pytest.raises(ValueError):
        svc.create("")


def test_create_blank_title_raises(svc):
    with pytest.raises(ValueError):
        svc.create("   ")


def test_create_with_all_fields(svc):
    t = svc.create("Task", description="desc", due_date=date(2026, 6, 1),
                   priority="high", project_id="p1", tags=["x"])
    assert t.description == "desc"
    assert t.due_date == date(2026, 6, 1)
    assert t.priority == "high"
    assert t.project_id == "p1"
    assert "x" in t.tags


# Service — get
def test_get_existing(svc):
    t = svc.create("Find me")
    assert svc.get(t.task_id).title == "Find me"


def test_get_missing(svc):
    assert svc.get("nope") is None


# Service — update
def test_update_title(svc):
    t = svc.create("Old")
    svc.update(t.task_id, title="New")
    assert svc.get(t.task_id).title == "New"


def test_update_status(svc):
    t = svc.create("Task")
    svc.update(t.task_id, status="done")
    assert svc.get(t.task_id).status == "done"


def test_update_empty_title_raises(svc):
    t = svc.create("Task")
    with pytest.raises(ValueError):
        svc.update(t.task_id, title="")


def test_update_unknown_field_raises(svc):
    t = svc.create("Task")
    with pytest.raises(ValueError):
        svc.update(t.task_id, bogus="x")


def test_update_missing_task_raises(svc):
    with pytest.raises(KeyError):
        svc.update("ghost", title="X")


# Service — delete
def test_delete(svc):
    t = svc.create("Gone")
    assert svc.delete(t.task_id) is True
    assert svc.get(t.task_id) is None


def test_delete_missing(svc):
    assert svc.delete("nope") is False


# Service — list
def test_list_all(svc):
    svc.create("A")
    svc.create("B")
    assert len(svc.list_all()) == 2


def test_list_by_status(svc):
    t = svc.create("Done task")
    svc.update(t.task_id, status="done")
    svc.create("Todo task")
    assert len(svc.list_by_status("done")) == 1
    assert len(svc.list_by_status("todo")) == 1


def test_list_by_project(svc):
    svc.create("P1 task", project_id="p1")
    svc.create("P2 task", project_id="p2")
    svc.create("No project")
    assert len(svc.list_by_project("p1")) == 1
