import logging
import sys
import traceback
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ErrorReporter:
    """Captures and logs exceptions with structured context."""

    def capture_exception(
        self,
        exc: BaseException,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        logger.error(
            "Unhandled exception: %s\nContext: %s\nTraceback:\n%s",
            repr(exc),
            context or {},
            tb,
        )

    def install_global_handler(self) -> None:
        """Replace sys.excepthook so all uncaught exceptions are logged."""
        reporter = self

        def handler(exc_type, exc_value, exc_tb):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_tb)
                return
            reporter.capture_exception(exc_value, context={"source": "uncaught"})

        sys.excepthook = handler

    def uninstall_global_handler(self) -> None:
        sys.excepthook = sys.__excepthook__
