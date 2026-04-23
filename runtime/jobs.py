import logging

logger = logging.getLogger(__name__)


def sod_summary_job() -> None:
    """Generate and display the start-of-day summary."""
    logger.info("SOD summary job triggered")


def eod_summary_job() -> None:
    """Generate and store the end-of-day summary."""
    logger.info("EOD summary job triggered")


def reminder_job() -> None:
    """Fire periodic progress reminder notifications."""
    logger.info("Reminder job triggered")
