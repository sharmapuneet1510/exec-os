import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from web.app import app

client = TestClient(app)

APP_ID = "test-app-123"


def _mock_jira_cfg(enabled=True, pat="pat", base_url="https://jira.example.com"):
    cfg = MagicMock()
    cfg.enabled  = enabled
    cfg.pat      = pat
    cfg.base_url = base_url
    return cfg


def _mock_sprint_cfg():
    cfg = MagicMock()
    cfg.board_id  = ""
    cfg.sprint_id = ""
    return cfg


@patch("web.routers.sprint_routes._jira_get")
@patch("web.routers.sprint_routes._get_jira_cfg")
@patch("web.routers.sprint_routes._get_cfg")
def test_active_sprint_found(mock_get_cfg, mock_jira_cfg, mock_jira_get):
    mock_get_cfg.return_value  = _mock_sprint_cfg()
    mock_jira_cfg.return_value = _mock_jira_cfg()
    mock_jira_get.return_value = {
        "values": [{
            "id":        42,
            "name":      "Sprint 5",
            "state":     "active",
            "startDate": "2026-06-01T00:00:00.000Z",
            "endDate":   "2026-06-14T00:00:00.000Z",
        }]
    }

    resp = client.get(f"/api/sprint/{APP_ID}/active-sprint?board_id=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is True
    assert data["sprint"]["id"] == 42
    assert data["sprint"]["name"] == "Sprint 5"
    assert data["sprint"]["state"] == "active"
    assert data["sprint"]["start_date"] == "2026-06-01"
    assert data["sprint"]["end_date"] == "2026-06-14"


@patch("web.routers.sprint_routes._jira_get")
@patch("web.routers.sprint_routes._get_jira_cfg")
@patch("web.routers.sprint_routes._get_cfg")
def test_no_active_sprint_returns_found_false(mock_get_cfg, mock_jira_cfg, mock_jira_get):
    mock_get_cfg.return_value  = _mock_sprint_cfg()
    mock_jira_cfg.return_value = _mock_jira_cfg()
    mock_jira_get.return_value = {"values": []}

    resp = client.get(f"/api/sprint/{APP_ID}/active-sprint?board_id=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is False
    assert data["sprint"] is None


@patch("web.routers.sprint_routes._jira_get")
@patch("web.routers.sprint_routes._get_jira_cfg")
@patch("web.routers.sprint_routes._get_cfg")
def test_boards_endpoint_returns_list(mock_get_cfg, mock_jira_cfg, mock_jira_get):
    mock_get_cfg.return_value  = _mock_sprint_cfg()
    mock_jira_cfg.return_value = _mock_jira_cfg()
    mock_jira_get.return_value = {
        "values": [
            {"id": 1, "name": "PROJ board",  "type": "scrum",  "location": {"projectKey": "PROJ"}},
            {"id": 2, "name": "OPS board",   "type": "kanban", "location": {"projectKey": "OPS"}},
        ]
    }

    resp = client.get(f"/api/sprint/{APP_ID}/boards")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["boards"]) == 2
    assert data["boards"][0]["id"] == 1
    assert data["boards"][0]["name"] == "PROJ board"
    assert data["boards"][0]["project_key"] == "PROJ"
    assert data["boards"][1]["type"] == "kanban"


@patch("web.routers.sprint_routes._get_jira_cfg")
@patch("web.routers.sprint_routes._get_cfg")
def test_active_sprint_requires_board_id(mock_get_cfg, mock_jira_cfg):
    mock_get_cfg.return_value  = _mock_sprint_cfg()
    mock_jira_cfg.return_value = _mock_jira_cfg()

    resp = client.get(f"/api/sprint/{APP_ID}/active-sprint")  # missing board_id
    assert resp.status_code == 422
