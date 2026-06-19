import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from web.app import app
from db.base import get_db

client = TestClient(app)


def _app_orm(app_id="app1", name="TestApp_xyz", status="active"):
    a = MagicMock()
    a.application_id  = app_id
    a.name            = name
    a.status          = status
    a.description     = ""
    a.owner           = ""
    a.code            = ""
    a.jira_projects   = "[]"
    a.gitlab_projects = "[]"
    a.sprints         = "[]"
    a.created_at      = None
    a.updated_at      = None
    a.jira_project_key = ""
    return a


def test_archive_app_sets_status_archived():
    db = MagicMock()
    app_orm = _app_orm("app1", "Real App")
    db.query.return_value.filter.return_value.first.return_value = app_orm

    app.dependency_overrides[get_db] = lambda: db
    try:
        resp = client.post("/api/applications/app1/archive")
        assert resp.status_code == 200
        assert app_orm.status == "archived"
        db.commit.assert_called()
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_archive_returns_404_for_unknown_app():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    app.dependency_overrides[get_db] = lambda: db
    try:
        resp = client.post("/api/applications/nonexistent/archive")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_cleanup_preview_identifies_test_apps():
    db = MagicMock()

    apps = [
        _app_orm("a1", "TestApp_1778565563"),
        _app_orm("a2", "ewe"),
        _app_orm("a3", "Real Production App"),
    ]

    # .all() returns all active apps; .count() returns 0 for task counts
    db.query.return_value.filter.return_value.all.return_value = apps
    db.query.return_value.filter.return_value.count.return_value = 0

    app.dependency_overrides[get_db] = lambda: db
    try:
        resp = client.get("/api/applications/cleanup-preview")
        assert resp.status_code == 200
        data = resp.json()
        assert "candidates" in data
        assert "total_active" in data
        candidate_ids = {c["application_id"] for c in data["candidates"]}
        assert "a3" not in candidate_ids   # "Real Production App" must NOT be a candidate
        assert "a1" in candidate_ids        # "TestApp_xxx" IS a test app
        assert "a2" in candidate_ids        # "ewe" IS a test app (short junk name)
    finally:
        app.dependency_overrides.pop(get_db, None)
