import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from web.app import app

client = TestClient(app)


def _sprint_cfg(email="alice@example.com", gitlab="alice_gl"):
    cfg = MagicMock()
    cfg.my_jira_email      = email
    cfg.my_gitlab_username = gitlab
    return cfg


def _jira_cfg(enabled=True, pat="pat", base_url="https://jira.example.com"):
    cfg = MagicMock()
    cfg.enabled  = enabled
    cfg.pat      = pat
    cfg.base_url = base_url
    return cfg


def _gl_cfg(enabled=True, token="gltoken", base_url="https://gitlab.example.com", project_ids='["mygroup/myrepo"]'):
    cfg = MagicMock()
    cfg.enabled       = enabled
    cfg.access_token  = token
    cfg.base_url      = base_url
    cfg.project_ids   = project_ids
    return cfg


@patch("web.routers.my_work_routes.requests")
@patch("web.routers.my_work_routes._get_gl_configs")
@patch("web.routers.my_work_routes._get_jira_cfg")
@patch("web.routers.my_work_routes._get_sprint_cfg")
def test_my_work_returns_real_jira_issues(mock_sprint, mock_jira, mock_gl, mock_req):
    mock_sprint.return_value = _sprint_cfg()
    mock_jira.return_value   = _jira_cfg()
    mock_gl.return_value     = []

    jira_resp = MagicMock()
    jira_resp.ok = True
    jira_resp.json.return_value = {
        "issues": [{
            "key": "PROJ-42",
            "fields": {
                "summary": "Real Jira issue",
                "status":    {"name": "In Progress"},
                "priority":  {"name": "High"},
                "issuetype": {"name": "Story"},
                "project":   {"key": "PROJ"},
                "duedate":   "2026-07-10",
                "updated":   "2026-06-15T10:00:00.000+0000",
            }
        }]
    }
    mock_req.get.return_value = jira_resp

    resp = client.get("/api/my-work")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["jira"]) == 1
    assert data["jira"][0]["key"] == "PROJ-42"
    assert data["jira"][0]["web_url"] == "https://jira.example.com/browse/PROJ-42"


@patch("web.routers.my_work_routes.requests")
@patch("web.routers.my_work_routes._get_gl_configs")
@patch("web.routers.my_work_routes._get_jira_cfg")
@patch("web.routers.my_work_routes._get_sprint_cfg")
def test_my_work_returns_real_gitlab_mrs(mock_sprint, mock_jira, mock_gl, mock_req):
    mock_sprint.return_value = _sprint_cfg(gitlab="alice_gl")
    mock_jira.return_value   = _jira_cfg(enabled=False)
    mock_gl.return_value     = [_gl_cfg()]

    mr_resp = MagicMock()
    mr_resp.ok = True
    mr_resp.json.return_value = [{
        "iid": 7,
        "title": "My feature MR",
        "state": "opened",
        "draft": False,
        "target_branch": "main",
        "web_url": "https://gitlab.example.com/mygroup/myrepo/-/merge_requests/7",
        "updated_at": "2026-06-16T12:00:00.000Z",
        "has_conflicts": False,
    }]
    mock_req.get.return_value = mr_resp

    resp = client.get("/api/my-work")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["mrs"]) == 1
    assert data["mrs"][0]["iid"] == 7
    assert data["mrs"][0]["title"] == "My feature MR"


@patch("web.routers.my_work_routes._get_gl_configs")
@patch("web.routers.my_work_routes._get_jira_cfg")
@patch("web.routers.my_work_routes._get_sprint_cfg")
def test_my_work_returns_empty_jira_when_disabled(mock_sprint, mock_jira, mock_gl):
    mock_sprint.return_value = _sprint_cfg()
    mock_jira.return_value   = _jira_cfg(enabled=False)
    mock_gl.return_value     = []

    resp = client.get("/api/my-work")
    assert resp.status_code == 200
    data = resp.json()
    assert data["jira"] == []


@patch("web.routers.my_work_routes.requests")
@patch("web.routers.my_work_routes._get_gl_configs")
@patch("web.routers.my_work_routes._get_jira_cfg")
@patch("web.routers.my_work_routes._get_sprint_cfg")
def test_my_work_jira_failure_returns_empty_not_500(mock_sprint, mock_jira, mock_gl, mock_req):
    """Jira API failure must not crash the endpoint — return empty list + error key."""
    mock_sprint.return_value = _sprint_cfg()
    mock_jira.return_value   = _jira_cfg()
    mock_gl.return_value     = []
    mock_req.get.side_effect = Exception("Connection timeout")

    resp = client.get("/api/my-work")
    assert resp.status_code == 200
    data = resp.json()
    assert data["jira"] == []
    assert "error" in data


@patch("web.routers.my_work_routes.requests")
@patch("web.routers.my_work_routes._get_gl_configs")
@patch("web.routers.my_work_routes._get_jira_cfg")
@patch("web.routers.my_work_routes._get_sprint_cfg")
def test_my_work_gitlab_failure_surfaces_gl_errors(mock_sprint, mock_jira, mock_gl, mock_req):
    """GitLab project fetch failure must not 500 — surface via gl_errors key."""
    mock_sprint.return_value = _sprint_cfg(gitlab="alice_gl")
    mock_jira.return_value   = _jira_cfg(enabled=False)
    mock_gl.return_value     = [_gl_cfg()]
    mock_req.get.side_effect = Exception("GitLab connection refused")

    resp = client.get("/api/my-work")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mrs"] == []
    assert "gl_errors" in data
    assert len(data["gl_errors"]) > 0


@patch("web.routers.my_work_routes.requests")
@patch("web.routers.my_work_routes._get_gl_configs")
@patch("web.routers.my_work_routes._get_jira_cfg")
@patch("web.routers.my_work_routes._get_sprint_cfg")
def test_my_work_gitlab_multiple_project_ids(mock_sprint, mock_jira, mock_gl, mock_req):
    """Each project ID in gl_cfg triggers a separate requests.get call."""
    mock_sprint.return_value = _sprint_cfg(gitlab="alice_gl")
    mock_jira.return_value   = _jira_cfg(enabled=False)
    # Two project IDs in one GL config
    mock_gl.return_value = [_gl_cfg(project_ids='["proj/one", "proj/two"]')]

    mr_resp = MagicMock()
    mr_resp.ok = True
    mr_resp.json.return_value = [{
        "iid": 1, "title": "MR", "state": "opened", "draft": False,
        "target_branch": "main", "web_url": "https://gl.example.com/mr/1",
        "updated_at": "2026-06-16T12:00:00.000Z", "has_conflicts": False,
    }]
    mock_req.get.return_value = mr_resp

    resp = client.get("/api/my-work")
    assert resp.status_code == 200
    # requests.get called once per project ID
    assert mock_req.get.call_count == 2
    data = resp.json()
    # Both project MRs are collected (one MR per project = 2 total)
    assert len(data["mrs"]) == 2
