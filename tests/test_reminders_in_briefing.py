import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session


def _reminder(title="Submit timesheet", sod=True, eod=False):
    r = MagicMock()
    r.title = title
    r.description = ""
    r.priority = "medium"
    r.trigger_type = "fixed_time"
    r.trigger_value = "09:00"
    r.include_in_sod = sod
    r.include_in_eod = eod
    r.is_active = True
    return r


@patch("web.email_sender._get_active_reminders")
@patch("web.email_sender._fetch_open_mrs_for_email")
@patch("web.email_sender._fetch_my_jira_issues")
def test_sod_includes_reminders_flagged_for_sod(mock_jira, mock_mrs, mock_rem):
    mock_jira.return_value = []
    mock_mrs.return_value = []
    mock_rem.return_value = [_reminder("Submit timesheet", sod=True)]

    from web.email_sender import build_sod_html
    db = MagicMock(spec=Session)
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.filter.return_value.all.return_value = []
    db.query.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.all.return_value = []

    html = build_sod_html(db)
    assert "Submit timesheet" in html


@patch("web.email_sender._get_active_reminders")
@patch("web.email_sender._fetch_my_jira_issues")
def test_eod_excludes_sod_only_reminders(mock_jira, mock_rem):
    mock_jira.return_value = []
    mock_rem.return_value = [_reminder("Morning only", sod=True, eod=False)]

    from web.email_sender import build_eod_html
    db = MagicMock(spec=Session)
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.filter.return_value.all.return_value = []
    db.query.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.all.return_value = []

    html = build_eod_html(db)
    assert "Morning only" not in html


@patch("web.email_sender._get_active_reminders")
@patch("web.email_sender._fetch_my_jira_issues")
def test_eod_includes_eod_flagged_reminders(mock_jira, mock_rem):
    mock_jira.return_value = []
    mock_rem.return_value = [_reminder("Wrap up", sod=False, eod=True)]

    from web.email_sender import build_eod_html
    db = MagicMock(spec=Session)
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.filter.return_value.all.return_value = []
    db.query.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.all.return_value = []

    html = build_eod_html(db)
    assert "Wrap up" in html
