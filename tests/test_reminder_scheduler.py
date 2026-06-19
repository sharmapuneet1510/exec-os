"""Pure-logic unit tests for ReminderScheduler (no APScheduler start)."""
from datetime import date, datetime, timedelta
from types import SimpleNamespace

from services.reminder_scheduler import ReminderScheduler


def _sched():
    return ReminderScheduler()


def test_calculate_trigger_date_minus_one_day():
    s = _sched()
    r = SimpleNamespace(due_date=date(2026, 7, 1), trigger_value="-1d")
    assert s._calculate_trigger_date(r) == date(2026, 6, 30)


def test_calculate_trigger_date_plus_one_week():
    s = _sched()
    r = SimpleNamespace(due_date=date(2026, 7, 1), trigger_value="+1w")
    assert s._calculate_trigger_date(r) == date(2026, 7, 8)


def test_calculate_trigger_date_one_month():
    s = _sched()
    r = SimpleNamespace(due_date=date(2026, 7, 1), trigger_value="1m")
    assert s._calculate_trigger_date(r) == date(2026, 8, 1)


def test_calculate_trigger_date_missing_due_date_returns_today():
    s = _sched()
    r = SimpleNamespace(due_date=None, trigger_value="-1d")
    assert s._calculate_trigger_date(r) == date.today()


def test_priority_to_severity_mapping():
    s = _sched()
    assert s._priority_to_severity("low") == "info"
    assert s._priority_to_severity("high") == "warning"
    assert s._priority_to_severity("critical") == "critical"
    assert s._priority_to_severity("unknown") == "info"


def test_should_trigger_blocked_by_snooze():
    s = _sched()
    r = SimpleNamespace(
        snooze_until=datetime.utcnow() + timedelta(minutes=30),
        last_triggered=None, trigger_type="fixed_time",
    )
    assert s._should_trigger(r) is False


def test_should_trigger_blocked_by_recent_fire():
    s = _sched()
    r = SimpleNamespace(
        snooze_until=None,
        last_triggered=datetime.utcnow() - timedelta(seconds=60),  # < 5 min
        trigger_type="fixed_time",
    )
    assert s._should_trigger(r) is False


def test_should_trigger_fixed_time_passes_when_clear():
    s = _sched()
    r = SimpleNamespace(snooze_until=None, last_triggered=None, trigger_type="fixed_time")
    assert s._should_trigger(r) is True


def test_should_trigger_relative_true_when_target_reached():
    s = _sched()
    r = SimpleNamespace(
        snooze_until=None, last_triggered=None, trigger_type="relative_interval",
        due_date=date.today(), trigger_value="-1d",  # target = yesterday → now >= target
    )
    assert s._should_trigger(r) is True
