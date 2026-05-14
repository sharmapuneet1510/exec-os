from datetime import datetime, timedelta, timezone
import pytest
from audit.model import AuditEvent, EventType
from audit.store import JSONAuditStore
from audit.service import AuditService

@pytest.fixture
def store(tmp_path): return JSONAuditStore(tmp_path / "audit_log.jsonl")
@pytest.fixture
def svc(store): return AuditService(store)

def now(): return datetime.now(timezone.utc)

# Model
def test_event_round_trip():
    e = AuditEvent(EventType.TASK_CREATED, "Task foo created", actor="user1", metadata={"id":"t1"})
    restored = AuditEvent.from_dict(e.to_dict())
    assert restored.event_type == EventType.TASK_CREATED
    assert restored.actor == "user1"
    assert restored.metadata == {"id":"t1"}

def test_event_has_unique_ids():
    e1 = AuditEvent(EventType.SYSTEM_STARTUP, "started")
    e2 = AuditEvent(EventType.SYSTEM_STARTUP, "started")
    assert e1.event_id != e2.event_id

# Store
def test_store_empty_when_no_file(store): assert store.all() == []

def test_store_append_and_all(store):
    store.append(AuditEvent(EventType.BACKUP_CREATED, "backup done"))
    store.append(AuditEvent(EventType.SETTINGS_CHANGED, "theme changed"))
    assert len(store.all()) == 2

def test_store_query_by_event_type(store):
    store.append(AuditEvent(EventType.BACKUP_CREATED, "backup"))
    store.append(AuditEvent(EventType.TASK_CREATED, "task"))
    results = store.query(event_type=EventType.BACKUP_CREATED)
    assert len(results) == 1 and results[0].event_type == EventType.BACKUP_CREATED

def test_store_query_by_actor(store):
    store.append(AuditEvent(EventType.TASK_CREATED, "t1", actor="alice"))
    store.append(AuditEvent(EventType.TASK_CREATED, "t2", actor="system"))
    assert len(store.query(actor="alice")) == 1

def test_store_query_by_time_range(store):
    base = now()
    e1 = AuditEvent(EventType.TASK_CREATED, "old", timestamp=base - timedelta(hours=2))
    e2 = AuditEvent(EventType.TASK_CREATED, "recent", timestamp=base - timedelta(minutes=10))
    store.append(e1); store.append(e2)
    results = store.query(start=base - timedelta(hours=1))
    assert len(results) == 1 and results[0].description == "recent"

# Service
def test_log_creates_event(svc):
    e = svc.log(EventType.SETTINGS_CHANGED, "dark mode on", actor="user")
    assert e.event_type == EventType.SETTINGS_CHANGED

def test_log_persists(store, svc):
    svc.log(EventType.RESTORE_PERFORMED, "restored from 2026-04-20")
    assert len(store.all()) == 1

def test_recent_returns_newest_first(svc):
    svc.log(EventType.SYSTEM_STARTUP, "boot")
    svc.log(EventType.BACKUP_CREATED, "backup")
    svc.log(EventType.TASK_COMPLETED, "done")
    events = svc.recent(2)
    assert len(events) == 2
    assert events[0].timestamp >= events[1].timestamp

def test_query_delegation(svc):
    svc.log(EventType.FOCUS_TOGGLED, "focus on")
    svc.log(EventType.TASK_CREATED, "new task")
    results = svc.query(event_type=EventType.FOCUS_TOGGLED)
    assert len(results) == 1
