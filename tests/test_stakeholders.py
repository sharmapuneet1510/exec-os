import pytest
from projects.stakeholders import (
    ProjectNote, ProjectNoteStore, Stakeholder,
    StakeholderService, StakeholderStore,
)


@pytest.fixture
def svc(tmp_path):
    return StakeholderService(
        stakeholder_store=StakeholderStore(tmp_path / "stakeholders"),
        note_store=ProjectNoteStore(tmp_path / "notes"),
    )


# Stakeholder model
def test_stakeholder_defaults():
    s = Stakeholder(project_id="p1", name="Alice", email="a@b.com")
    assert s.role == "contributor"


def test_stakeholder_round_trip():
    s = Stakeholder(project_id="p1", name="Bob", email="b@c.com", role="owner")
    s2 = Stakeholder.from_dict(s.to_dict())
    assert s2.name == "Bob" and s2.role == "owner" and s2.email == "b@c.com"


# ProjectNote model
def test_note_round_trip():
    n = ProjectNote(project_id="p1", content="meeting notes")
    n2 = ProjectNote.from_dict(n.to_dict())
    assert n2.content == "meeting notes" and n2.note_id == n.note_id


# StakeholderStore
def test_store_add_and_list(tmp_path):
    store = StakeholderStore(tmp_path)
    store.add(Stakeholder(project_id="p1", name="A", email="a@x.com"))
    assert len(store.all_for_project("p1")) == 1


def test_store_empty(tmp_path):
    assert StakeholderStore(tmp_path).all_for_project("none") == []


def test_store_remove(tmp_path):
    store = StakeholderStore(tmp_path)
    s = Stakeholder(project_id="p1", name="A", email="a@x.com")
    store.add(s)
    assert store.remove("p1", s.stakeholder_id) is True
    assert store.all_for_project("p1") == []


def test_store_remove_missing(tmp_path):
    assert StakeholderStore(tmp_path).remove("p1", "ghost") is False


def test_store_update_role(tmp_path):
    store = StakeholderStore(tmp_path)
    s = Stakeholder(project_id="p1", name="A", email="a@x.com")
    store.add(s)
    assert store.update_role("p1", s.stakeholder_id, "owner") is True
    assert store.all_for_project("p1")[0].role == "owner"


def test_store_update_role_missing(tmp_path):
    assert StakeholderStore(tmp_path).update_role("p1", "ghost", "owner") is False


# StakeholderService — add
def test_add_stakeholder(svc):
    s = svc.add_stakeholder("p1", "Alice", "alice@x.com")
    assert s.name == "Alice" and s.role == "contributor"


def test_add_stakeholder_strips_name(svc):
    s = svc.add_stakeholder("p1", "  Bob  ", "bob@x.com", role="owner")
    assert s.name == "Bob"


def test_add_stakeholder_empty_name_raises(svc):
    with pytest.raises(ValueError):
        svc.add_stakeholder("p1", "", "x@x.com")


def test_add_stakeholder_invalid_email_raises(svc):
    with pytest.raises(ValueError):
        svc.add_stakeholder("p1", "Name", "notanemail")


def test_list_stakeholders(svc):
    svc.add_stakeholder("p1", "A", "a@x.com")
    svc.add_stakeholder("p1", "B", "b@x.com")
    assert len(svc.list_stakeholders("p1")) == 2


def test_remove_stakeholder(svc):
    s = svc.add_stakeholder("p1", "A", "a@x.com")
    assert svc.remove_stakeholder("p1", s.stakeholder_id) is True
    assert svc.list_stakeholders("p1") == []


def test_update_role(svc):
    s = svc.add_stakeholder("p1", "A", "a@x.com")
    assert svc.update_role("p1", s.stakeholder_id, "reviewer") is True


# StakeholderService — notes
def test_add_note(svc):
    n = svc.add_note("p1", "Kick-off meeting notes")
    assert n.content == "Kick-off meeting notes"


def test_add_note_strips(svc):
    n = svc.add_note("p1", "  trimmed  ")
    assert n.content == "trimmed"


def test_add_note_empty_raises(svc):
    with pytest.raises(ValueError):
        svc.add_note("p1", "")


def test_get_notes(svc):
    svc.add_note("p1", "Note A")
    svc.add_note("p1", "Note B")
    assert len(svc.get_notes("p1")) == 2


def test_delete_note(svc):
    n = svc.add_note("p1", "Delete me")
    assert svc.delete_note("p1", n.note_id) is True
    assert svc.get_notes("p1") == []


def test_note_author(svc):
    n = svc.add_note("p1", "Alice's note", author="alice")
    assert svc.get_notes("p1")[0].author == "alice"
