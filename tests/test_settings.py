import json
import tempfile
from pathlib import Path

import pytest

from settings.model import UserSettings
from settings.manager import SettingsManager


# ── Model tests ───────────────────────────────────────────────────────────────

def test_default_values():
    s = UserSettings()
    assert s.work_hours_start == "09:00"
    assert s.work_hours_end == "18:00"
    assert s.sod_time == "08:45"
    assert s.eod_time == "18:15"
    assert s.reminder_interval_minutes == 30
    assert s.default_view == "tasks"
    assert s.desktop_notifications_enabled is True
    assert s.email_notifications_enabled is False
    assert s.startup_on_boot is False
    assert s.minimize_to_tray is True


def test_round_trip_dict():
    s = UserSettings(work_hours_start="08:00", default_view="dashboard", startup_on_boot=True)
    restored = UserSettings.from_dict(s.to_dict())
    assert restored.work_hours_start == "08:00"
    assert restored.default_view == "dashboard"
    assert restored.startup_on_boot is True


def test_from_dict_with_missing_keys_uses_defaults():
    s = UserSettings.from_dict({})
    assert s == UserSettings()


# ── Manager tests ──────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_settings_path(tmp_path):
    return tmp_path / "settings.json"


def test_is_first_run_when_no_file(tmp_settings_path):
    mgr = SettingsManager(tmp_settings_path)
    assert mgr.is_first_run() is True


def test_is_first_run_false_after_save(tmp_settings_path):
    mgr = SettingsManager(tmp_settings_path)
    mgr.save(UserSettings())
    assert mgr.is_first_run() is False


def test_save_and_load(tmp_settings_path):
    mgr = SettingsManager(tmp_settings_path)
    original = UserSettings(work_hours_start="07:30", reminder_interval_minutes=15)
    mgr.save(original)

    mgr2 = SettingsManager(tmp_settings_path)
    loaded = mgr2.load()
    assert loaded.work_hours_start == "07:30"
    assert loaded.reminder_interval_minutes == 15


def test_update_single_field(tmp_settings_path):
    mgr = SettingsManager(tmp_settings_path)
    mgr.save(UserSettings())
    mgr.update(default_view="projects")
    assert mgr.get().default_view == "projects"


def test_update_unknown_key_raises(tmp_settings_path):
    mgr = SettingsManager(tmp_settings_path)
    mgr.save(UserSettings())
    with pytest.raises(ValueError, match="Unknown setting"):
        mgr.update(nonexistent_key="value")


def test_reset_to_defaults(tmp_settings_path):
    mgr = SettingsManager(tmp_settings_path)
    mgr.save(UserSettings(startup_on_boot=True, default_view="dashboard"))
    mgr.reset_to_defaults()
    assert mgr.get().startup_on_boot is False
    assert mgr.get().default_view == "tasks"


def test_settings_file_is_valid_json(tmp_settings_path):
    mgr = SettingsManager(tmp_settings_path)
    mgr.save(UserSettings())
    with open(tmp_settings_path) as f:
        data = json.load(f)
    assert "work_hours_start" in data
