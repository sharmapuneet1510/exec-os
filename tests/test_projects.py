from datetime import date
import pytest
from projects.model import Project
from projects.store import JSONProjectStore
from projects.service import ProjectService

TODAY = date(2026, 4, 22)


@pytest.fixture
def svc(tmp_path):
    return ProjectService(store=JSONProjectStore(tmp_path))


# Model
def test_project_defaults():
    p = Project(name="My Project")
    assert p.status == "active"
    assert p.tags == []
    assert p.owner is None


def test_project_round_trip():
    p = Project(name="X", description="desc", status="on_hold",
                owner="alice", due_date=TODAY, tags=["important"])
    p2 = Project.from_dict(p.to_dict())
    assert p2.name == "X"
    assert p2.description == "desc"
    assert p2.status == "on_hold"
    assert p2.owner == "alice"
    assert p2.due_date == TODAY
    assert p2.tags == ["important"]


def test_project_round_trip_no_due():
    p = Project(name="No date")
    assert Project.from_dict(p.to_dict()).due_date is None


# Store
def test_store_save_load(tmp_path):
    store = JSONProjectStore(tmp_path)
    p = Project(name="Test")
    store.save(p)
    loaded = store.load(p.project_id)
    assert loaded is not None and loaded.name == "Test"


def test_store_load_missing(tmp_path):
    assert JSONProjectStore(tmp_path).load("ghost") is None


def test_store_delete(tmp_path):
    store = JSONProjectStore(tmp_path)
    p = Project(name="Del")
    store.save(p)
    assert store.delete(p.project_id) is True
    assert store.load(p.project_id) is None


def test_store_delete_missing(tmp_path):
    assert JSONProjectStore(tmp_path).delete("nope") is False


def test_store_all(tmp_path):
    store = JSONProjectStore(tmp_path)
    store.save(Project(name="A"))
    store.save(Project(name="B"))
    assert len(store.all()) == 2


# Service — create
def test_create(svc):
    p = svc.create("Alpha")
    assert p.name == "Alpha" and p.project_id


def test_create_strips_whitespace(svc):
    p = svc.create("  Beta  ")
    assert p.name == "Beta"


def test_create_empty_raises(svc):
    with pytest.raises(ValueError):
        svc.create("")


def test_create_blank_raises(svc):
    with pytest.raises(ValueError):
        svc.create("   ")


def test_create_with_all_fields(svc):
    p = svc.create("Full", description="d", status="on_hold",
                   owner="bob", due_date=TODAY, tags=["x"])
    assert p.description == "d"
    assert p.status == "on_hold"
    assert p.owner == "bob"
    assert p.due_date == TODAY
    assert "x" in p.tags


# Service — get / update / delete
def test_get_existing(svc):
    p = svc.create("Find")
    assert svc.get(p.project_id).name == "Find"


def test_get_missing(svc):
    assert svc.get("nope") is None


def test_update_name(svc):
    p = svc.create("Old")
    svc.update(p.project_id, name="New")
    assert svc.get(p.project_id).name == "New"


def test_update_status(svc):
    p = svc.create("P")
    svc.update(p.project_id, status="on_hold")
    assert svc.get(p.project_id).status == "on_hold"


def test_update_empty_name_raises(svc):
    p = svc.create("P")
    with pytest.raises(ValueError):
        svc.update(p.project_id, name="")


def test_update_unknown_field_raises(svc):
    p = svc.create("P")
    with pytest.raises(ValueError):
        svc.update(p.project_id, bogus="x")


def test_update_missing_raises(svc):
    with pytest.raises(KeyError):
        svc.update("ghost", name="X")


def test_delete(svc):
    p = svc.create("Gone")
    assert svc.delete(p.project_id) is True
    assert svc.get(p.project_id) is None


def test_delete_missing(svc):
    assert svc.delete("nope") is False


# Service — list / archive / complete
def test_list_all(svc):
    svc.create("A")
    svc.create("B")
    assert len(svc.list_all()) == 2


def test_list_by_status(svc):
    svc.create("Active 1")
    p = svc.create("Hold")
    svc.update(p.project_id, status="on_hold")
    assert len(svc.list_by_status("active")) == 1
    assert len(svc.list_by_status("on_hold")) == 1


def test_archive(svc):
    p = svc.create("Arch")
    svc.archive(p.project_id)
    assert svc.get(p.project_id).status == "archived"


def test_complete(svc):
    p = svc.create("Done proj")
    svc.complete(p.project_id)
    assert svc.get(p.project_id).status == "completed"
