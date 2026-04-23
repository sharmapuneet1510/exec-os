from datetime import date
from pathlib import Path

import pytest

from carryforward.model import CarryForwardRecord, DailyPlan
from carryforward.store import JSONPlanStore
from carryforward.service import CarryForwardService


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def store(tmp_path):
    return JSONPlanStore(plans_dir=tmp_path / "plans")


@pytest.fixture
def svc(store):
    return CarryForwardService(store)


D1 = date(2026, 4, 21)
D2 = date(2026, 4, 22)
D3 = date(2026, 4, 23)


# ── Model tests ───────────────────────────────────────────────────────────────

def test_daily_plan_incomplete_task_ids():
    plan = DailyPlan(plan_date=D1, task_ids=["t1", "t2", "t3"], completed_task_ids=["t2"])
    assert plan.incomplete_task_ids() == ["t1", "t3"]


def test_daily_plan_is_complete():
    plan = DailyPlan(plan_date=D1, task_ids=["t1"], completed_task_ids=["t1"])
    assert plan.is_complete("t1")
    assert not plan.is_complete("t2")


def test_daily_plan_round_trip():
    r = CarryForwardRecord(task_id="t1", original_date=D1, carried_date=D2, carry_count=2)
    plan = DailyPlan(plan_date=D2, task_ids=["t1"], carry_forward_records=[r])
    restored = DailyPlan.from_dict(plan.to_dict())
    assert restored.plan_date == D2
    assert restored.carry_forward_records[0].carry_count == 2


# ── Store tests ───────────────────────────────────────────────────────────────

def test_store_load_missing_returns_none(store):
    assert store.load(D1) is None


def test_store_save_and_load(store):
    plan = DailyPlan(plan_date=D1, task_ids=["t1", "t2"])
    store.save(plan)
    loaded = store.load(D1)
    assert loaded.task_ids == ["t1", "t2"]


def test_store_load_or_create_returns_empty_plan(store):
    plan = store.load_or_create(D1)
    assert plan.plan_date == D1
    assert plan.task_ids == []


def test_store_list_dates(store):
    store.save(DailyPlan(plan_date=D1))
    store.save(DailyPlan(plan_date=D3))
    assert store.list_dates() == [D1, D3]


# ── Service tests ─────────────────────────────────────────────────────────────

def test_identify_incomplete_no_plan(svc):
    assert svc.identify_incomplete(D1) == []


def test_identify_incomplete_returns_unfinished(store, svc):
    plan = DailyPlan(plan_date=D1, task_ids=["t1", "t2", "t3"], completed_task_ids=["t2"])
    store.save(plan)
    assert svc.identify_incomplete(D1) == ["t1", "t3"]


def test_carry_forward_adds_tasks_to_next_day(store, svc):
    store.save(DailyPlan(plan_date=D1, task_ids=["t1", "t2"], completed_task_ids=["t1"]))
    next_plan = svc.carry_forward(D1)
    assert "t2" in next_plan.task_ids
    assert "t1" not in next_plan.task_ids


def test_carry_forward_sets_carry_record(store, svc):
    store.save(DailyPlan(plan_date=D1, task_ids=["t1"]))
    next_plan = svc.carry_forward(D1)
    records = {r.task_id: r for r in next_plan.carry_forward_records}
    assert "t1" in records
    assert records["t1"].original_date == D1
    assert records["t1"].carried_date == D2
    assert records["t1"].carry_count == 1


def test_carry_forward_increments_carry_count_on_second_carry(store, svc):
    store.save(DailyPlan(plan_date=D1, task_ids=["t1"]))
    svc.carry_forward(D1)   # D1 → D2, carry_count=1
    svc.carry_forward(D2)   # D2 → D3, carry_count=2
    records = {r.task_id: r for r in svc.get_carried_tasks(D3)}
    assert records["t1"].carry_count == 2
    assert records["t1"].original_date == D1


def test_carry_forward_no_duplicate_task_ids(store, svc):
    store.save(DailyPlan(plan_date=D1, task_ids=["t1"]))
    store.save(DailyPlan(plan_date=D2, task_ids=["t1"]))  # already in next day
    next_plan = svc.carry_forward(D1)
    assert next_plan.task_ids.count("t1") == 1


def test_carry_forward_nothing_to_carry(store, svc):
    store.save(DailyPlan(plan_date=D1, task_ids=["t1"], completed_task_ids=["t1"]))
    next_plan = svc.carry_forward(D1)
    assert next_plan.task_ids == []


def test_get_carried_tasks_empty_for_new_day(svc):
    assert svc.get_carried_tasks(D1) == []
