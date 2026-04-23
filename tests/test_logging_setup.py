import logging
import sys
from pathlib import Path
import pytest
from logging_setup.setup import configure_logging, get_logger, reset_logging
from logging_setup.error_reporter import ErrorReporter

@pytest.fixture(autouse=True)
def clean_logging():
    reset_logging()
    yield
    reset_logging()

# configure_logging
def test_creates_log_file(tmp_path):
    configure_logging(log_dir=tmp_path / "logs")
    assert (tmp_path / "logs" / "commanddesk.log").exists()

def test_idempotent_second_call(tmp_path):
    configure_logging(log_dir=tmp_path / "logs")
    handlers_before = len(logging.getLogger().handlers)
    configure_logging(log_dir=tmp_path / "logs")
    assert len(logging.getLogger().handlers) == handlers_before

def test_log_level_respected(tmp_path):
    configure_logging(log_dir=tmp_path / "logs", level=logging.DEBUG)
    assert logging.getLogger().level == logging.DEBUG

def test_get_logger_returns_named_logger(tmp_path):
    configure_logging(log_dir=tmp_path / "logs")
    lg = get_logger("mymodule")
    assert lg.name == "mymodule"

def test_log_message_written_to_file(tmp_path):
    log_dir = tmp_path / "logs"
    configure_logging(log_dir=log_dir)
    get_logger("test").warning("hello from test")
    content = (log_dir / "commanddesk.log").read_text()
    assert "hello from test" in content

def test_reset_logging_removes_handlers(tmp_path):
    configure_logging(log_dir=tmp_path / "logs")
    reset_logging()
    assert logging.getLogger().handlers == []

# ErrorReporter
def test_capture_exception_logs_error(tmp_path, caplog):
    configure_logging(log_dir=tmp_path / "logs")
    reporter = ErrorReporter()
    with caplog.at_level(logging.ERROR):
        try:
            raise ValueError("boom")
        except ValueError as e:
            reporter.capture_exception(e, context={"user": "test"})
    assert "boom" in caplog.text

def test_capture_exception_with_context(tmp_path, caplog):
    configure_logging(log_dir=tmp_path / "logs")
    reporter = ErrorReporter()
    with caplog.at_level(logging.ERROR):
        reporter.capture_exception(RuntimeError("ctx test"), context={"task_id": "t42"})
    assert "t42" in caplog.text

def test_install_global_handler_replaces_excepthook():
    reporter = ErrorReporter()
    original = sys.excepthook
    reporter.install_global_handler()
    assert sys.excepthook is not original
    reporter.uninstall_global_handler()
    assert sys.excepthook is sys.__excepthook__

def test_keyboard_interrupt_not_swallowed():
    reporter = ErrorReporter()
    reporter.install_global_handler()
    # KeyboardInterrupt should delegate to original hook, not our handler
    assert sys.excepthook is not sys.__excepthook__
    reporter.uninstall_global_handler()
