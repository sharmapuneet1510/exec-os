from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from web.app import app

client = TestClient(app)


@patch("web.routers.setup_routes.SessionLocal")
def test_setup_status_returns_checklist_shape(mock_session):
    db = MagicMock()
    mock_session.return_value = db
    db.query.return_value.first.return_value        = None
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.count.return_value = 0

    resp = client.get("/api/setup/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "complete"    in data
    assert "done_count"  in data
    assert "total_count" in data
    assert "checks"      in data
    keys = {c["key"] for c in data["checks"]}
    assert {"jira", "gitlab", "identity", "has_app", "email"} == keys


@patch("web.routers.setup_routes.SessionLocal")
def test_setup_status_complete_when_all_configured(mock_session):
    db = MagicMock()
    mock_session.return_value = db

    jira_cfg = MagicMock()
    jira_cfg.enabled  = True
    jira_cfg.base_url = "https://jira.example.com"
    jira_cfg.pat      = "tok"

    sprint_cfg = MagicMock()
    sprint_cfg.my_jira_email      = "pm@example.com"
    sprint_cfg.my_gitlab_username = "pm_gl"

    email_cfg = MagicMock()
    email_cfg.smtp_host = "smtp.example.com"
    email_cfg.enabled   = True

    def query_side(model):
        from db.models import JiraConfigORM, SprintConfigORM, AppGitLabConfigORM, ApplicationORM, EmailConfigORM
        mock = MagicMock()
        if model is JiraConfigORM:
            mock.first.return_value = jira_cfg
        elif model is SprintConfigORM:
            mock.first.return_value = sprint_cfg
        elif model is EmailConfigORM:
            mock.first.return_value = email_cfg
        elif model is AppGitLabConfigORM:
            mock.filter.return_value.count.return_value = 1
        elif model is ApplicationORM:
            mock.filter.return_value.count.return_value = 2
        return mock

    db.query.side_effect = query_side

    resp = client.get("/api/setup/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["complete"] is True
    assert data["done_count"] == 5
    jira_check = next(c for c in data["checks"] if c["key"] == "jira")
    assert jira_check["done"] is True
    identity_check = next(c for c in data["checks"] if c["key"] == "identity")
    assert identity_check["done"] is True


@patch("web.routers.setup_routes.SessionLocal")
def test_setup_status_not_complete_when_nothing_configured(mock_session):
    db = MagicMock()
    mock_session.return_value = db
    db.query.return_value.first.return_value                     = None
    db.query.return_value.filter.return_value.count.return_value = 0

    resp = client.get("/api/setup/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["complete"]   is False
    assert data["done_count"] == 0
