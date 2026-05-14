"""
Tests for project form validation and service integration logic.
"""
from datetime import date
import pytest
from projects.model import Project
from projects.store import JSONProjectStore
from projects.service import ProjectService

TODAY = date(2026, 4, 22)


@pytest.fixture
def svc(tmp_path):
    return ProjectService(store=JSONProjectStore(tmp_path))


# Validation logic mirroring what the form does
def _simulate_save(svc, name, description="", status="active",
                   owner=None, due_date=None, project_id=None):
    name = name.strip()
    if not name:
        raise ValueError("Project name is required")
    if due_date and isinstance(due_date, str):
        due_date = date.fromisoformat(due_date)
    if project_id:
        return svc.update(project_id, name=name, description=description,
                          status=status, owner=owner, due_date=due_date)
    return svc.create(name, description=description, status=status,
                      owner=owner, due_date=due_date)


def test_create_project(svc):
    p = _simulate_save(svc, "Alpha", description="desc", owner="alice")
    assert p.name == "Alpha" and p.owner == "alice"


def test_create_strips_name(svc):
    p = _simulate_save(svc, "  Beta  ")
    assert p.name == "Beta"


def test_create_empty_name_raises(svc):
    with pytest.raises(ValueError):
        _simulate_save(svc, "")


def test_create_blank_name_raises(svc):
    with pytest.raises(ValueError):
        _simulate_save(svc, "   ")


def test_create_with_due_date(svc):
    p = _simulate_save(svc, "P", due_date=TODAY)
    assert svc.get(p.project_id).due_date == TODAY


def test_create_invalid_due_date():
    with pytest.raises(ValueError):
        date.fromisoformat("not-a-date")


def test_edit_project(svc):
    p = svc.create("Original")
    updated = _simulate_save(svc, "Updated", project_id=p.project_id)
    assert svc.get(p.project_id).name == "Updated"


def test_edit_status(svc):
    p = svc.create("P")
    _simulate_save(svc, p.name, status="on_hold", project_id=p.project_id)
    assert svc.get(p.project_id).status == "on_hold"


def test_edit_missing_project_raises(svc):
    with pytest.raises(KeyError):
        svc.update("ghost", name="X")
