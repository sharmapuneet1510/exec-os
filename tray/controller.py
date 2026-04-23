import logging
from typing import Callable, Optional

from settings.manager import SettingsManager
from .manager import TrayManager, TrayState

logger = logging.getLogger(__name__)


class TrayController:
    """Wires TrayManager to user settings."""

    def __init__(self, tray_manager: TrayManager, settings_manager: SettingsManager):
        self._tray = tray_manager
        self._settings = settings_manager

    def handle_window_close(self) -> None:
        minimize = self._settings.get().minimize_to_tray
        self._tray.on_close_requested(minimize_to_tray=minimize)

    def toggle_visibility(self) -> None:
        self._tray.toggle_visibility()

    def show(self) -> None:
        self._tray.show()

    @property
    def state(self) -> TrayState:
        return self._tray.state
