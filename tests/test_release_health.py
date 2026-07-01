from datetime import date
from types import SimpleNamespace
from services.release_health import derive_status, current_stage, item_health, release_health


def _item(stage, status, planned=None, order=0, required=True):
    return SimpleNamespace(item_id="i", title=stage, stage=stage, status=status,
                           is_required=required, order=order, planned_date=planned, completed_at=None)


TODAY = date(2026, 6, 29)


def test_item_breached():
    assert item_health(_item("development", "pending", date(2026, 6, 20)), TODAY)["state"] == "breached"


def test_item_at_risk_within_window():
    h = item_health(_item("qa", "pending", date(2026, 7, 1)), TODAY)  # +2 days
    assert h["state"] == "at_risk" and h["days"] == 2


def test_item_done_never_breached():
    assert item_health(_item("development", "done", date(2026, 6, 20)), TODAY)["state"] == "done"


def test_item_boundary_today_is_at_risk():
    assert item_health(_item("qa", "pending", TODAY), TODAY)["state"] == "at_risk"


def test_derive_status():
    assert derive_status([_item("requirement_gathering", "pending")]) == "TODO"
    assert derive_status([_item("development", "in_progress")]) == "IN_PROGRESS"
    assert derive_status([_item("in_prod", "done")]) == "COMPLETED"


def test_current_stage_first_pending():
    items = [_item("requirement_gathering", "done"), _item("development", "pending"), _item("qa", "pending")]
    assert current_stage(items) == "development"


def test_release_health_rollup_breached():
    items = [_item("requirement_gathering", "done", date(2026, 6, 2)),
             _item("development", "pending", date(2026, 6, 20))]
    h = release_health(items, TODAY)
    assert h["level"] == "breached"
    assert h["derived_status"] == "IN_PROGRESS"
    assert h["current_stage"] == "development"
    assert any(g["state"] == "breached" for g in h["items"])
