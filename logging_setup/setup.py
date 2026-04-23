import logging
import logging.handlers
from pathlib import Path

_DEFAULT_LOG_DIR = Path.home() / ".commanddesk" / "logs"
_LOG_FILE = "commanddesk.log"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 3
_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

_configured = False


def configure_logging(
    log_dir: Path = _DEFAULT_LOG_DIR,
    level: int = logging.INFO,
    console: bool = True,
) -> None:
    global _configured
    if _configured:
        return

    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT)

    root = logging.getLogger()
    root.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / _LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.WARNING)
        root.addHandler(console_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def reset_logging() -> None:
    """For testing — tear down configured handlers and allow reconfiguration."""
    global _configured
    root = logging.getLogger()
    for handler in root.handlers[:]:
        handler.close()
        root.removeHandler(handler)
    _configured = False
