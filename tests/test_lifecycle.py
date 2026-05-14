import pytest
from tasks.model import Task
from tasks.store import JSONTaskStore
from tasks.service import TaskService
from tasks.lifecycle import (
    InvalidTransitionError, LifecycleService,
    allowed_transitions, validate_transition,
)


@pytest.fixture
def svc(tmp_path):
    return TaskService(store=JSONTaskStore(tmp_path))


@pytest.fixture
def lc(svc):
    return LifecycleService(svc)


# validate_transition
def test_todo_to_in_progress():
    validate_transition("todo", "in_progress")  # no error


def test_todo_to_done_invalid():
    with pytest.raises(InvalidTransitionError):
        validate_transition("todo", "done")


def test_in_progress_to_done():
    validate_transition("in_progress", "done")


def test_in_progress_to_todo():
    validate_transition("in_progress", "todo")


def test_done_to_todo_reopen():
    validate_transition("done", "todo")


def test_done_to_in_progress_invalid():
    with pytest.raises(InvalidTransitionError):
        validate_transition("done", "in_progress")


def test_cancelled_to_todo_reopen():
    validate_transition("cancelled", "todo")


def test_cancelled_to_done_invalid():
    with pytest.raises(InvalidTransitionError):
        validate_transition("cancelled", "done")


def test_same_status_invalid():
    with pytest.raises(InvalidTransitionError):
        validate_transition("todo", "todo")


# allowed_transitions
def test_allowed_from_todo():
    assert set(allowed_transitions("todo")) == {"in_progress", "cancelled"}


def test_allowed_from_in_progress():
    assert set(allowed_transitions("in_progress")) == {"done", "todo", "cancelled"}


def test_allowed_from_done():
    assert allowed_transitions("done") == ["todo"]


def test_allowed_from_cancelled():
    assert allowed_transitions("cancelled") == ["todo"]


# LifecycleService
def test_lifecycle_transition(svc, lc):
    t = svc.create("My task")
    updated = lc.transition(t.task_id, "in_progress")
    assert updated.status == "in_progress"


def test_lifecycle_persists(svc, lc):
    t = svc.create("Persist")
    lc.transition(t.task_id, "in_progress")
    assert svc.get(t.task_id).status == "in_progress"


def test_lifecycle_invalid_raises(svc, lc):
    t = svc.create("Bad")
    with pytest.raises(InvalidTransitionError):
        lc.transition(t.task_id, "done")


def test_lifecycle_missing_task_raises(lc):
    with pytest.raises(KeyError):
        lc.transition("nope", "in_progress")


def test_lifecycle_allowed_transitions(svc, lc):
    t = svc.create("Check allowed")
    assert set(lc.allowed_transitions(t.task_id)) == {"in_progress", "cancelled"}


def test_lifecycle_allowed_missing_raises(lc):
    with pytest.raises(KeyError):
        lc.allowed_transitions("ghost")


def test_full_happy_path(svc, lc):
    t = svc.create("Full path")
    lc.transition(t.task_id, "in_progress")
    lc.transition(t.task_id, "done")
    assert svc.get(t.task_id).status == "done"


def test_reopen_from_done(svc, lc):
    t = svc.create("Reopen")
    lc.transition(t.task_id, "in_progress")
    lc.transition(t.task_id, "done")
    lc.transition(t.task_id, "todo")
    assert svc.get(t.task_id).status == "todo"


def test_cancel_from_todo(svc, lc):
    t = svc.create("Cancel")
    lc.transition(t.task_id, "cancelled")
    assert svc.get(t.task_id).status == "cancelled"
