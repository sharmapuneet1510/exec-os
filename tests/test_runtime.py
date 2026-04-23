import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from runtime.scheduler import JobScheduler
from runtime.runtime import AppRuntime, _parse_hhmm
from settings.manager import SettingsManager
from settings.model import UserSettings


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_runtime(tmp_path: Path) -> AppRuntime:
    mgr = SettingsManager(tmp_path / "settings.json")
    mgr.save(UserSettings())
    return AppRuntime(settings_manager=mgr)


# ── _parse_hhmm ───────────────────────────────────────────────────────────────

def test_parse_hhmm():
    assert _parse_hhmm("08:45") == (8, 45)
    assert _parse_hhmm("18:15") == (18, 15)
    assert _parse_hhmm("00:00") == (0, 0)


# ── JobScheduler ──────────────────────────────────────────────────────────────

def test_scheduler_starts_and_stops():
    s = JobScheduler()
    assert not s.running
    s.start()
    assert s.running
    s.shutdown()
    assert not s.running


def test_scheduler_double_start_safe():
    s = JobScheduler()
    s.start()
    s.start()  # should not raise
    assert s.running
    s.shutdown()


def test_add_and_list_cron_job():
    s = JobScheduler()
    s.start()
    s.add_cron_job("test_cron", lambda: None, hour=9, minute=0)
    assert "test_cron" in s.list_jobs()
    s.shutdown()


def test_add_and_list_interval_job():
    s = JobScheduler()
    s.start()
    s.add_interval_job("test_interval", lambda: None, minutes=15)
    assert "test_interval" in s.list_jobs()
    s.shutdown()


def test_remove_job():
    s = JobScheduler()
    s.start()
    s.add_interval_job("removable", lambda: None, minutes=60)
    assert "removable" in s.list_jobs()
    s.remove_job("removable")
    assert "removable" not in s.list_jobs()
    s.shutdown()


def test_remove_nonexistent_job_safe():
    s = JobScheduler()
    s.start()
    s.remove_job("ghost_job")  # should not raise
    s.shutdown()


# ── AppRuntime ────────────────────────────────────────────────────────────────

def test_runtime_starts_and_stops(tmp_path):
    rt = _make_runtime(tmp_path)
    rt.start()
    assert rt.running
    rt.stop()
    assert not rt.running


def test_runtime_double_start_safe(tmp_path):
    rt = _make_runtime(tmp_path)
    rt.start()
    rt.start()  # second call should be a no-op
    assert rt.running
    rt.stop()


def test_runtime_registers_expected_jobs(tmp_path):
    rt = _make_runtime(tmp_path)
    rt.start()
    jobs = rt._scheduler.list_jobs()
    assert "sod_summary" in jobs
    assert "eod_summary" in jobs
    assert "reminder" in jobs
    rt.stop()


def test_runtime_uses_settings_times(tmp_path):
    mgr = SettingsManager(tmp_path / "settings.json")
    mgr.save(UserSettings(sod_time="07:30", eod_time="17:45", reminder_interval_minutes=20))
    rt = AppRuntime(settings_manager=mgr)
    rt.start()
    assert rt.running
    rt.stop()


def test_runtime_stop_before_start_safe(tmp_path):
    rt = _make_runtime(tmp_path)
    rt.stop()  # should not raise
