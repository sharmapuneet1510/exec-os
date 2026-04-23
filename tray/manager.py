import logging
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class TrayState(Enum):
    VISIBLE   = "visible"
    HIDDEN    = "hidden"
    MINIMIZED = "minimized"


class TrayManager:
    """
    Manages window visibility and tray behaviour.
    The actual OS window/tray widget is injected via callbacks so this
    class remains testable without a display.
    """

    def __init__(
        self,
        show_window_fn: Optional[Callable] = None,
        hide_window_fn: Optional[Callable] = None,
        quit_fn: Optional[Callable] = None,
    ):
        self._show_fn = show_window_fn or (lambda: None)
        self._hide_fn = hide_window_fn or (lambda: None)
        self._quit_fn = quit_fn or (lambda: None)
        self._state = TrayState.VISIBLE

    @property
    def state(self) -> TrayState:
        return self._state

    def show(self) -> None:
        self._show_fn()
        self._state = TrayState.VISIBLE
        logger.info("Window shown")

    def hide(self) -> None:
        self._hide_fn()
        self._state = TrayState.HIDDEN
        logger.info("Window hidden to tray")

    def minimize_to_tray(self) -> None:
        self._hide_fn()
        self._state = TrayState.MINIMIZED
        logger.info("Window minimized to tray")

    def restore(self) -> None:
        self._show_fn()
        self._state = TrayState.VISIBLE
        logger.info("Window restored from tray")

    def on_close_requested(self, minimize_to_tray: bool) -> None:
        """
        Called when the user clicks the window close button.
        If minimize_to_tray is True, hides instead of quitting.
        """
        if minimize_to_tray:
            self.minimize_to_tray()
        else:
            self.quit()

    def quit(self) -> None:
        self._quit_fn()
        self._state = TrayState.HIDDEN
        logger.info("Application quit")

    def toggle_visibility(self) -> None:
        if self._state == TrayState.VISIBLE:
            self.hide()
        else:
            self.restore()
