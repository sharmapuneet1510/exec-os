"""
Tests for TaskDetailScreen data logic (note service integration).
UI layout is not tested headlessly.
"""
from datetime import date
import pytest
from tasks.model import Task
from tasks.store import JSONTaskStore
from tasks.service import TaskService
from tasks.notes import TaskHistoryStore, TaskNoteService, TaskNoteStore

TODAY = date(2026, 4, 22)


@pytest.fixture
def svc(tmp_path):
    return TaskService(store=JSONTaskStore(tmp_path / "tasks"))


@pytest.fixture
def ns(svc, tmp_path):
    return TaskNoteService(
        svc,
        note_store=TaskNoteStore(tmp_path / "notes"),
        history_store=TaskHistoryStore(tmp_path / "history"),
    )


def test_detail_shows_notes(svc, ns):
    t = svc.create("My task")
    ns.add_note(t.task_id, "First note")
    ns.add_note(t.task_id, "Second note")
    notes = ns.get_notes(t.task_id)
    assert len(notes) == 2
    assert notes[0].content == "First note"
    assert notes[1].content == "Second note"


def test_detail_shows_history(svc, ns):
    t = svc.create("My task")
    ns.add_note(t.task_id, "A note")
    ns.record_event(t.task_id, "status_changed", "todo -> in_progress")
    history = ns.get_history(t.task_id)
    types = [e.event_type for e in history]
    assert "note_added" in types
    assert "status_changed" in types


def test_detail_empty_notes(svc, ns):
    t = svc.create("Empty task")
    assert ns.get_notes(t.task_id) == []


def test_detail_empty_history(svc, ns):
    t = svc.create("Empty task")
    assert ns.get_history(t.task_id) == []


def test_note_created_at_is_set(svc, ns):
    t = svc.create("Task")
    n = ns.add_note(t.task_id, "check time")
    assert n.created_at and len(n.created_at) > 0


def test_history_event_actor(svc, ns):
    t = svc.create("Task")
    ns.record_event(t.task_id, "field_updated", "priority: medium -> high", actor="user")
    h = ns.get_history(t.task_id)
    assert h[0].actor == "user"


def test_reminder_date_accessible(svc):
    t = svc.create("Task with reminder", due_date=TODAY)
    svc.update(t.task_id, reminder_date=TODAY)
    loaded = svc.get(t.task_id)
    assert loaded.reminder_date == TODAY


def test_no_reminder_date(svc):
    t = svc.create("No reminder")
    assert svc.get(t.task_id).reminder_date is None
