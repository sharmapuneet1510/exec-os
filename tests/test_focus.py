from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from focus.model import FocusMode, FocusState, QuietHours, is_non_critical
from focus.service import _in_quiet_window
from focus.store import JSONFocusStore
from focus.service import FocusService


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def store(tmp_path):
    return JSONFocusStore(path=tmp_path / "focus_state.json")

@pytest.fixture
def svc(store):
    return FocusService(store)


# ── Model tests ───────────────────────────────────────────────────────────────

def test_is_non_critical():
    assert not is_non_critical("critical")
    assert not is_non_critical("high")
    assert is_non_critical("normal")
    assert is_non_critical("low")

def test_focus_mode_active_until():
    started = datetime.now(timezone.utc)
    fm = FocusMode(enabled=True, started_at=started, duration_minutes=60)
    until = fm.active_until()
    assert until == started + timedelta(minutes=60)

def test_focus_mode_active_until_indefinite():
    fm = FocusMode(enabled=True, started_at=datetime.now(timezone.utc), duration_minutes=None)
    assert fm.active_until() is None

def test_focus_state_round_trip():
    state = FocusState(
        focus_mode=FocusMode(enabled=True, started_at=datetime.now(timezone.utc), duration_minutes=30),
        quiet_hours=QuietHours(enabled=True, start_time="22:00", end_time="07:00"),
    )
    restored = FocusState.from_dict(state.to_dict())
    assert restored.focus_mode.enabled is True
    assert restored.focus_mode.duration_minutes == 30
    assert restored.quiet_hours.start_time == "22:00"

# ── Quiet window helper tests ─────────────────────────────────────────────────

def _t(h, m=0):
    return datetime(2026, 4, 22, h, m)

def test_quiet_window_same_day():
    assert _in_quiet_window(_t(10), "09:00", "17:00")
    assert not _in_quiet_window(_t(8), "09:00", "17:00")
    assert not _in_quiet_window(_t(17), "09:00", "17:00")

def test_quiet_window_overnight_inside():
    assert _in_quiet_window(_t(23), "22:00", "08:00")
    assert _in_quiet_window(_t(1), "22:00", "08:00")

def test_quiet_window_overnight_outside():
    assert not _in_quiet_window(_t(10), "22:00", "08:00")
    assert not _in_quiet_window(_t(8), "22:00", "08:00")

# ── Store tests ───────────────────────────────────────────────────────────────

def test_store_returns_default_when_missing(store):
    state = store.load()
    assert state.focus_mode.enabled is False
    assert state.quiet_hours.enabled is False

def test_store_save_and_load(store):
    state = FocusState(quiet_hours=QuietHours(enabled=True, start_time="21:00", end_time="07:00"))
    store.save(state)
    loaded = store.load()
    assert loaded.quiet_hours.enabled is True
    assert loaded.quiet_hours.start_time == "21:00"

# ── Service tests ─────────────────────────────────────────────────────────────

def test_enable_focus_indefinite(svc):
    fm = svc.enable_focus()
    assert fm.enabled is True
    assert fm.duration_minutes is None
    assert svc.is_focus_active()

def test_enable_focus_with_duration(svc):
    svc.enable_focus(duration_minutes=90)
    assert svc.is_focus_active()

def test_focus_auto_expires(store):
    svc = FocusService(store)
    svc.enable_focus(duration_minutes=1)
    # Manually backdate started_at to simulate expiry
    svc._state.focus_mode.started_at = datetime.now(timezone.utc) - timedelta(minutes=2)
    assert not svc.is_focus_active()

def test_disable_focus(svc):
    svc.enable_focus()
    svc.disable_focus()
    assert not svc.is_focus_active()

def test_quiet_hours_active(svc):
    svc.set_quiet_hours("22:00", "08:00")
    night = datetime(2026, 4, 22, 23, 0)
    assert svc.is_in_quiet_hours(now=night)

def test_quiet_hours_inactive_outside_window(svc):
    svc.set_quiet_hours("22:00", "08:00")
    midday = datetime(2026, 4, 22, 12, 0)
    assert not svc.is_in_quiet_hours(now=midday)

def test_is_suppressed_normal_during_focus(svc):
    svc.enable_focus()
    assert svc.is_suppressed("normal")
    assert svc.is_suppressed("low")

def test_critical_never_suppressed(svc):
    svc.enable_focus()
    assert not svc.is_suppressed("critical")

def test_is_suppressed_during_quiet_hours(svc):
    svc.set_quiet_hours("22:00", "08:00")
    night = datetime(2026, 4, 22, 23, 30)
    assert svc.is_suppressed("normal", now=night)
    assert not svc.is_suppressed("critical", now=night)

def test_not_suppressed_when_both_inactive(svc):
    assert not svc.is_suppressed("normal")
    assert not svc.is_suppressed("low")
