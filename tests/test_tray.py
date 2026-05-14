from pathlib import Path
import pytest
from tray.manager import TrayManager, TrayState
from tray.controller import TrayController
from settings.manager import SettingsManager
from settings.model import UserSettings

@pytest.fixture
def calls():
    return {"show": 0, "hide": 0, "quit": 0}

@pytest.fixture
def mgr(calls):
    return TrayManager(
        show_window_fn=lambda: calls.__setitem__("show", calls["show"]+1),
        hide_window_fn=lambda: calls.__setitem__("hide", calls["hide"]+1),
        quit_fn=lambda: calls.__setitem__("quit", calls["quit"]+1),
    )

@pytest.fixture
def settings_mgr(tmp_path):
    m = SettingsManager(tmp_path / "settings.json")
    m.save(UserSettings())
    return m

@pytest.fixture
def ctrl(mgr, settings_mgr):
    return TrayController(mgr, settings_mgr)

# TrayManager state transitions
def test_initial_state_visible(mgr): assert mgr.state == TrayState.VISIBLE
def test_hide_changes_state(mgr): mgr.hide(); assert mgr.state == TrayState.HIDDEN
def test_show_changes_state(mgr): mgr.hide(); mgr.show(); assert mgr.state == TrayState.VISIBLE
def test_minimize_to_tray(mgr): mgr.minimize_to_tray(); assert mgr.state == TrayState.MINIMIZED
def test_restore_from_minimized(mgr): mgr.minimize_to_tray(); mgr.restore(); assert mgr.state == TrayState.VISIBLE

def test_toggle_visible_to_hidden(mgr): mgr.toggle_visibility(); assert mgr.state == TrayState.HIDDEN
def test_toggle_hidden_to_visible(mgr): mgr.hide(); mgr.toggle_visibility(); assert mgr.state == TrayState.VISIBLE

def test_on_close_minimize_to_tray(mgr, calls):
    mgr.on_close_requested(minimize_to_tray=True)
    assert mgr.state == TrayState.MINIMIZED
    assert calls["hide"] == 1
    assert calls["quit"] == 0

def test_on_close_quit(mgr, calls):
    mgr.on_close_requested(minimize_to_tray=False)
    assert calls["quit"] == 1

def test_callbacks_called(mgr, calls):
    mgr.show(); mgr.hide()
    assert calls["show"] == 1
    assert calls["hide"] == 1

# TrayController
def test_ctrl_close_minimizes_when_setting_true(ctrl, settings_mgr, mgr):
    settings_mgr.update(minimize_to_tray=True)
    ctrl.handle_window_close()
    assert mgr.state == TrayState.MINIMIZED

def test_ctrl_close_quits_when_setting_false(ctrl, settings_mgr, calls):
    settings_mgr.update(minimize_to_tray=False)
    ctrl.handle_window_close()
    assert calls["quit"] == 1

def test_ctrl_toggle(ctrl, mgr):
    ctrl.toggle_visibility()
    assert mgr.state == TrayState.HIDDEN
