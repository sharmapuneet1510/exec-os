import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from web.app import app
import web.routers.jira_routes as jira_routes

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_jira_cache():
    """Bust the in-process Jira cache before every test to prevent cross-test pollution."""
    jira_routes._cache_bust()
    yield
    jira_routes._cache_bust()


def _mock_jira_cfg(enabled=True, pat="testpat", base_url="https://jira.example.com"):
    cfg = MagicMock()
    cfg.enabled = enabled
    cfg.pat = pat
    cfg.base_url = base_url
    return cfg


def _sample_issues():
    return [
        {
            "key": "PROJ-1",
            "fields": {
                "summary": "Fix login bug",
                "assignee": {
                    "accountId": "user1",
                    "displayName": "Alice",
                    "avatarUrls": {"48x48": "https://example.com/alice.png"},
                    "emailAddress": "alice@example.com",
                },
                "status": {"name": "In Progress"},
                "priority": {"name": "High"},
                "issuetype": {"name": "Bug"},
                "project": {"key": "PROJ"},
                "duedate": "2026-07-01",
                "updated": "2026-06-15T10:00:00.000+0000",
            },
        },
        {
            "key": "PROJ-2",
            "fields": {
                "summary": "Add new feature",
                "assignee": {
                    "accountId": "user2",
                    "displayName": "Bob",
                    "avatarUrls": {"48x48": "https://example.com/bob.png"},
                    "emailAddress": "bob@example.com",
                },
                "status": {"name": "To Do"},
                "priority": {"name": "Medium"},
                "issuetype": {"name": "Story"},
                "project": {"key": "PROJ"},
                "duedate": None,
                "updated": "2026-06-14T10:00:00.000+0000",
            },
        },
    ]


@patch("web.routers.jira_routes._jira_search_all")
@patch("web.routers.jira_routes._get_cfg")
def test_filter_returns_issues_grouped_by_assignee(mock_get_cfg, mock_search):
    mock_get_cfg.return_value = _mock_jira_cfg()
    mock_search.return_value = _sample_issues()

    resp = client.get("/api/jira/filter?jql=project%3DPROJ&app_id=app1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["by_assignee"]) == 2
    alice = next(a for a in data["by_assignee"] if a["display_name"] == "Alice")
    assert alice["total"] == 1
    assert alice["issues"][0]["key"] == "PROJ-1"


@patch("web.routers.jira_routes._get_cfg")
def test_filter_requires_jql_param(mock_get_cfg):
    mock_get_cfg.return_value = _mock_jira_cfg()
    resp = client.get("/api/jira/filter?app_id=app1")
    assert resp.status_code == 422


@patch("web.routers.jira_routes._jira_search_all")
@patch("web.routers.jira_routes._get_cfg")
def test_filter_returns_400_when_jira_disabled(mock_get_cfg, mock_search):
    mock_get_cfg.return_value = _mock_jira_cfg(enabled=False)
    mock_search.side_effect = AssertionError("search should not be called when Jira is disabled")
    resp = client.get("/api/jira/filter?jql=project%3DPROJ&app_id=app1")
    assert resp.status_code == 400


@patch("web.routers.jira_routes._jira_search_all")
@patch("web.routers.jira_routes._get_cfg")
def test_filter_unassigned_issues_grouped_correctly(mock_get_cfg, mock_search):
    mock_get_cfg.return_value = _mock_jira_cfg()
    unassigned_issue = {
        "key": "PROJ-3",
        "fields": {
            "summary": "Unowned task",
            "assignee": None,
            "status": {"name": "To Do"},
            "priority": {"name": "Low"},
            "issuetype": {"name": "Task"},
            "project": {"key": "PROJ"},
            "duedate": None,
            "updated": "2026-06-10T00:00:00.000+0000",
        },
    }
    mock_search.return_value = [unassigned_issue]

    resp = client.get("/api/jira/filter?jql=project%3DPROJ&app_id=app1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    unassigned = data["by_assignee"][0]
    assert unassigned["account_id"] == "__unassigned__"
    assert unassigned["display_name"] == "Unassigned"


@patch("web.routers.jira_routes._jira_search_all")
@patch("web.routers.jira_routes._get_cfg")
def test_filter_includes_web_url_for_each_issue(mock_get_cfg, mock_search):
    mock_get_cfg.return_value = _mock_jira_cfg(base_url="https://jira.example.com")
    mock_search.return_value = _sample_issues()

    resp = client.get("/api/jira/filter?jql=project%3DPROJ&app_id=app1")
    data = resp.json()
    alice = next(a for a in data["by_assignee"] if a["display_name"] == "Alice")
    assert alice["issues"][0]["web_url"] == "https://jira.example.com/browse/PROJ-1"
