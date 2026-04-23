import pytest
from tasks.model import Task
from tasks.store import JSONTaskStore
from tasks.service import TaskService
from tasks.notes import HistoryEvent, TaskHistoryStore, TaskNote, TaskNoteService, TaskNoteStore


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


# TaskNote
def test_note_round_trip():
    n = TaskNote(task_id="t1", content="hello")
    n2 = TaskNote.from_dict(n.to_dict())
    assert n2.note_id == n.note_id and n2.content == "hello"


def test_note_has_created_at():
    n = TaskNote(task_id="t1", content="x")
    assert n.created_at


# HistoryEvent
def test_history_event_round_trip():
    e = HistoryEvent(task_id="t1", event_type="status_changed", description="todo->done")
    e2 = HistoryEvent.from_dict(e.to_dict())
    assert e2.event_type == "status_changed" and e2.description == "todo->done"


# TaskNoteStore
def test_note_store_add_and_list(tmp_path):
    store = TaskNoteStore(tmp_path)
    n = TaskNote(task_id="t1", content="first note")
    store.add(n)
    notes = store.all_for_task("t1")
    assert len(notes) == 1 and notes[0].content == "first note"


def test_note_store_empty(tmp_path):
    assert TaskNoteStore(tmp_path).all_for_task("missing") == []


def test_note_store_delete(tmp_path):
    store = TaskNoteStore(tmp_path)
    n = TaskNote(task_id="t1", content="del me")
    store.add(n)
    assert store.delete("t1", n.note_id) is True
    assert store.all_for_task("t1") == []


def test_note_store_delete_missing(tmp_path):
    assert TaskNoteStore(tmp_path).delete("t1", "ghost") is False


def test_note_store_multiple(tmp_path):
    store = TaskNoteStore(tmp_path)
    store.add(TaskNote(task_id="t1", content="A"))
    store.add(TaskNote(task_id="t1", content="B"))
    assert len(store.all_for_task("t1")) == 2


# TaskHistoryStore
def test_history_store_append_and_list(tmp_path):
    store = TaskHistoryStore(tmp_path)
    e = HistoryEvent(task_id="t1", event_type="status_changed", description="x")
    store.append(e)
    events = store.all_for_task("t1")
    assert len(events) == 1 and events[0].event_type == "status_changed"


def test_history_store_empty(tmp_path):
    assert TaskHistoryStore(tmp_path).all_for_task("none") == []


def test_history_store_multiple(tmp_path):
    store = TaskHistoryStore(tmp_path)
    store.append(HistoryEvent(task_id="t1", event_type="a", description="x"))
    store.append(HistoryEvent(task_id="t1", event_type="b", description="y"))
    assert len(store.all_for_task("t1")) == 2


# TaskNoteService
def test_add_note(svc, ns):
    t = svc.create("Task")
    note = ns.add_note(t.task_id, "Remember this")
    assert note.content == "Remember this"


def test_add_note_strips(svc, ns):
    t = svc.create("Task")
    note = ns.add_note(t.task_id, "  hello  ")
    assert note.content == "hello"


def test_add_note_empty_raises(svc, ns):
    t = svc.create("Task")
    with pytest.raises(ValueError):
        ns.add_note(t.task_id, "")


def test_add_note_blank_raises(svc, ns):
    t = svc.create("Task")
    with pytest.raises(ValueError):
        ns.add_note(t.task_id, "   ")


def test_add_note_missing_task_raises(ns):
    with pytest.raises(KeyError):
        ns.add_note("ghost", "note")


def test_get_notes(svc, ns):
    t = svc.create("Task")
    ns.add_note(t.task_id, "Note 1")
    ns.add_note(t.task_id, "Note 2")
    assert len(ns.get_notes(t.task_id)) == 2


def test_delete_note(svc, ns):
    t = svc.create("Task")
    n = ns.add_note(t.task_id, "Delete me")
    assert ns.delete_note(t.task_id, n.note_id) is True
    assert ns.get_notes(t.task_id) == []


def test_add_note_creates_history_event(svc, ns):
    t = svc.create("Task")
    ns.add_note(t.task_id, "My note")
    history = ns.get_history(t.task_id)
    assert any(e.event_type == "note_added" for e in history)


def test_record_event(svc, ns):
    t = svc.create("Task")
    ns.record_event(t.task_id, "status_changed", "todo -> in_progress", actor="user")
    history = ns.get_history(t.task_id)
    assert len(history) == 1 and history[0].event_type == "status_changed"


def test_history_empty(svc, ns):
    t = svc.create("Task")
    assert ns.get_history(t.task_id) == []
