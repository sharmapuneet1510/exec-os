from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from escalation.model import DelayThreshold, EscalationRecord, boost_priority, PRIORITY_ORDER
from escalation.store import JSONEscalationStore
from escalation.service import EscalationService


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def store(tmp_path):
    return JSONEscalationStore(store_dir=tmp_path / "escalations")


@pytest.fixture
def svc(store):
    return EscalationService(store, threshold=DelayThreshold(days_delayed=7))


def delayed_since(days_ago: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


# ── Model tests ───────────────────────────────────────────────────────────────

def test_boost_priority_increments():
    assert boost_priority("low") == "medium"
    assert boost_priority("medium") == "high"
    assert boost_priority("high") == "critical"


def test_boost_priority_capped_at_critical():
    assert boost_priority("critical") == "critical"


def test_escalation_record_round_trip():
    r = EscalationRecord(
        task_id="t1",
        delayed_since=delayed_since(10),
        days_delayed=10,
        original_priority="medium",
        current_priority="high",
        visibility_level="high",
        priority_boosted=True,
    )
    restored = EscalationRecord.from_dict(r.to_dict())
    assert restored.task_id == "t1"
    assert restored.priority_boosted is True
    assert restored.visibility_level == "high"


# ── Store tests ───────────────────────────────────────────────────────────────

def test_store_load_missing_returns_none(store):
    assert store.load("ghost") is None


def test_store_save_and_load(store):
    r = EscalationRecord(
        task_id="t1", delayed_since=delayed_since(8),
        days_delayed=8, original_priority="medium", current_priority="high",
    )
    store.save(r)
    loaded = store.load("t1")
    assert loaded.task_id == "t1"
    assert loaded.days_delayed == 8


def test_store_delete(store):
    r = EscalationRecord(
        task_id="t2", delayed_since=delayed_since(8),
        days_delayed=8, original_priority="low", current_priority="medium",
    )
    store.save(r)
    store.delete("t2")
    assert store.load("t2") is None


def test_store_all(store):
    for i in range(3):
        store.save(EscalationRecord(
            task_id=f"t{i}", delayed_since=delayed_since(8),
            days_delayed=8, original_priority="low", current_priority="medium",
        ))
    assert len(store.all()) == 3


# ── Service tests ─────────────────────────────────────────────────────────────

def test_evaluate_below_threshold_returns_false(svc):
    assert svc.evaluate("t1", delayed_since(3), "medium") is False


def test_evaluate_at_threshold_returns_true(svc):
    assert svc.evaluate("t1", delayed_since(7), "medium") is True


def test_evaluate_above_threshold_returns_true(svc):
    assert svc.evaluate("t1", delayed_since(15), "low") is True


def test_escalate_sets_visibility_and_boosts_priority(store, svc):
    record = svc.escalate("t1", delayed_since(8), "medium")
    assert record.visibility_level == "high"
    assert record.current_priority == "high"
    assert record.priority_boosted is True
    assert store.load("t1") is not None


def test_escalate_idempotent_no_duplicate(store, svc):
    svc.escalate("t1", delayed_since(8), "medium")
    svc.escalate("t1", delayed_since(9), "medium")  # second call
    assert len(store.all()) == 1


def test_escalate_no_priority_boost_when_disabled(store):
    svc = EscalationService(store, threshold=DelayThreshold(days_delayed=7, boost_priority=False))
    record = svc.escalate("t1", delayed_since(8), "medium")
    assert record.priority_boosted is False
    assert record.current_priority == "medium"


def test_notify_sets_notified_at(store, svc):
    record = svc.escalate("t1", delayed_since(8), "medium")
    assert record.notified_at is None
    svc.notify(record, assignee="dev@example.com")
    assert record.notified_at is not None
    assert store.load("t1").notified_at is not None


def test_notify_idempotent(store, svc):
    record = svc.escalate("t1", delayed_since(8), "medium")
    svc.notify(record)
    first_notified = record.notified_at
    svc.notify(record)
    assert record.notified_at == first_notified


def test_resolve_removes_record(store, svc):
    svc.escalate("t1", delayed_since(8), "medium")
    svc.resolve("t1")
    assert store.load("t1") is None
