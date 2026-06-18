import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session


def _jira_cfg(enabled=True, pat="pat", base_url="https://jira.example.com"):
    cfg = MagicMock()
    cfg.enabled  = enabled
    cfg.pat      = pat
    cfg.base_url = base_url
    return cfg


def _gl_cfg(enabled=True, token="tok", base_url="https://gl.example.com", project_ids='["g/repo"]'):
    cfg = MagicMock()
    cfg.enabled      = enabled
    cfg.access_token = token
    cfg.base_url     = base_url
    cfg.project_ids  = project_ids
    return cfg


def _sprint_cfg(email="pm@example.com", gitlab="pm_gl"):
    cfg = MagicMock()
    cfg.my_jira_email      = email
    cfg.my_gitlab_username = gitlab
    return cfg


@patch("web.email_sender.requests")
@patch("web.email_sender._get_sprint_cfg")
@patch("web.email_sender._get_jira_cfg")
@patch("web.email_sender._get_gl_configs")
def test_sod_html_includes_jira_overdue_section(mock_gl, mock_jira, mock_sprint, mock_req):
    mock_gl.return_value     = []
    mock_jira.return_value   = _jira_cfg()
    mock_sprint.return_value = _sprint_cfg()

    jira_resp = MagicMock()
    jira_resp.ok = True
    jira_resp.json.return_value = {"issues": [{
        "key": "PROJ-99",
        "fields": {
            "summary":   "Fix critical auth bug",
            "status":    {"name": "In Progress"},
            "priority":  {"name": "Critical"},
            "issuetype": {"name": "Bug"},
            "project":   {"key": "PROJ"},
            "duedate":   "2026-06-01",
            "updated":   "2026-06-17T10:00:00.000Z",
        }
    }]}
    mock_req.get.return_value = jira_resp

    from web.email_sender import build_sod_html
    db = MagicMock(spec=Session)
    # Make all DB queries return empty lists so we isolate the Jira section
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.filter.return_value.all.return_value = []
    db.query.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.all.return_value = []

    html = build_sod_html(db)
    assert "PROJ-99" in html
    assert "Fix critical auth bug" in html


@patch("web.email_sender.requests")
@patch("web.email_sender._get_sprint_cfg")
@patch("web.email_sender._get_jira_cfg")
@patch("web.email_sender._get_gl_configs")
def test_sod_html_includes_open_mrs_section(mock_gl, mock_jira, mock_sprint, mock_req):
    mock_jira.return_value   = _jira_cfg(enabled=False)
    mock_sprint.return_value = _sprint_cfg(gitlab="pm_gl")
    mock_gl.return_value     = [_gl_cfg()]

    mr_resp = MagicMock()
    mr_resp.ok = True
    mr_resp.json.return_value = [{
        "iid": 5, "title": "Add login feature", "state": "opened",
        "draft": False, "target_branch": "main",
        "web_url": "https://gl.example.com/mr/5",
        "updated_at": "2026-06-17T00:00:00Z", "has_conflicts": False,
        "author": {"name": "Alice", "username": "alice_gl"},
    }]
    mock_req.get.return_value = mr_resp

    from web.email_sender import build_sod_html
    db = MagicMock(spec=Session)
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.filter.return_value.all.return_value = []
    db.query.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.all.return_value = []

    html = build_sod_html(db)
    assert "Add login feature" in html


@patch("web.email_sender.requests")
@patch("web.email_sender._get_sprint_cfg")
@patch("web.email_sender._get_jira_cfg")
@patch("web.email_sender._get_gl_configs")
def test_eod_html_includes_jira_completed_section(mock_gl, mock_jira, mock_sprint, mock_req):
    mock_gl.return_value     = []
    mock_jira.return_value   = _jira_cfg()
    mock_sprint.return_value = _sprint_cfg()

    jira_resp = MagicMock()
    jira_resp.ok = True
    jira_resp.json.return_value = {"issues": [{
        "key": "PROJ-55",
        "fields": {
            "summary":   "Completed today ticket",
            "status":    {"name": "Done"},
            "priority":  {"name": "High"},
            "issuetype": {"name": "Story"},
            "project":   {"key": "PROJ"},
            "duedate":   None,
            "updated":   "2026-06-18T14:00:00.000Z",
        }
    }]}
    mock_req.get.return_value = jira_resp

    from web.email_sender import build_eod_html
    db = MagicMock(spec=Session)
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.filter.return_value.all.return_value = []
    db.query.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.all.return_value = []

    html = build_eod_html(db)
    assert "PROJ-55" in html
    assert "Completed today ticket" in html


@patch("web.email_sender._get_gl_configs")
@patch("web.email_sender._get_jira_cfg")
@patch("web.email_sender._get_sprint_cfg")
def test_sod_html_works_when_jira_disabled(mock_sprint, mock_jira, mock_gl):
    """SOD email must not crash when Jira is disabled."""
    mock_sprint.return_value = _sprint_cfg()
    mock_jira.return_value   = _jira_cfg(enabled=False)
    mock_gl.return_value     = []

    from web.email_sender import build_sod_html
    db = MagicMock(spec=Session)
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.filter.return_value.all.return_value = []
    db.query.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.all.return_value = []

    html = build_sod_html(db)
    assert isinstance(html, str)
    assert len(html) > 200  # still produces a valid HTML email
