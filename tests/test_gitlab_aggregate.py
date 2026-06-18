import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from web.app import app
import web.routers.gitlab_routes as _gitlab_routes

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_gitlab_cache():
    """Clear the gitlab in-memory cache before each test to avoid cross-test pollution."""
    _gitlab_routes._cache.clear()
    yield
    _gitlab_routes._cache.clear()


def _gl_cfg(app_id="app1", enabled=True, token="tok", base_url="https://gl.example.com", project_ids='["g/repo"]'):
    cfg = MagicMock()
    cfg.application_id = app_id
    cfg.enabled        = enabled
    cfg.access_token   = token
    cfg.base_url       = base_url
    cfg.project_ids    = project_ids
    return cfg


def _mr(iid=1, title="MR", author="alice", draft=False):
    return {
        "iid":              iid,
        "title":            title,
        "state":            "opened",
        "draft":            draft,
        "work_in_progress": draft,
        "author":           {"name": author, "username": author, "avatar_url": None},
        "target_branch":    "main",
        "source_branch":    "feature",
        "created_at":       "2026-06-01T10:00:00.000Z",
        "updated_at":       "2026-06-17T10:00:00.000Z",
        "web_url":          f"https://gl.example.com/-/merge_requests/{iid}",
        "project_id":       1,
        "has_conflicts":    False,
        "reviewers":        [],
        "upvotes":          0,
        "downvotes":        0,
        "changes_count":    "3",
    }


@patch("web.routers.gitlab_routes.SessionLocal")
def test_all_mrs_returns_empty_when_no_configs(mock_session):
    db = MagicMock()
    mock_session.return_value = db
    db.query.return_value.filter.return_value.all.return_value = []

    resp = client.get("/api/gitlab/all-mrs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_mrs"] == 0
    assert data["all_mrs"] == []
    assert "last_fetched" in data


@patch("web.routers.gitlab_routes._gl_get")
@patch("web.routers.gitlab_routes.SessionLocal")
def test_all_mrs_splits_draft_vs_ready(mock_session, mock_gl_get):
    db = MagicMock()
    mock_session.return_value = db
    db.query.return_value.filter.return_value.all.return_value = [
        _gl_cfg("app1", project_ids='["g/repo"]'),
    ]

    call_count = {"n": 0}

    def gl_side(cfg, path, params=None):
        call_count["n"] += 1
        if "merge_requests" in path:
            return [_mr(iid=1, draft=False), _mr(iid=2, draft=True)], {}
        return {"id": 1, "name": "repo", "path_with_namespace": "g/repo", "web_url": ""}, {}

    mock_gl_get.side_effect = gl_side

    resp = client.get("/api/gitlab/all-mrs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ready_mrs"] == 1
    assert data["draft_mrs"] == 1
    assert data["total_mrs"] == 2


@patch("web.routers.gitlab_routes._gl_get")
@patch("web.routers.gitlab_routes.SessionLocal")
def test_all_mrs_groups_by_author(mock_session, mock_gl_get):
    db = MagicMock()
    mock_session.return_value = db
    db.query.return_value.filter.return_value.all.return_value = [
        _gl_cfg("app1", project_ids='["g/repo"]'),
    ]

    def gl_side(cfg, path, params=None):
        if "merge_requests" in path:
            return [
                _mr(iid=1, author="alice"),
                _mr(iid=2, author="alice"),
                _mr(iid=3, author="bob"),
            ], {}
        return {"id": 1, "name": "repo", "path_with_namespace": "g/repo", "web_url": ""}, {}

    mock_gl_get.side_effect = gl_side

    resp = client.get("/api/gitlab/all-mrs")
    assert resp.status_code == 200
    data = resp.json()
    authors = {a["name"]: a["total"] for a in data["authors"]}
    assert authors["alice"] == 2
    assert authors["bob"] == 1
    # sorted by total desc — alice first
    assert data["authors"][0]["name"] == "alice"


@patch("web.routers.gitlab_routes._gl_get")
@patch("web.routers.gitlab_routes.SessionLocal")
def test_all_mrs_tolerates_one_bad_project(mock_session, mock_gl_get):
    """A 401 on one project should not kill the entire aggregate."""
    from fastapi import HTTPException as FE
    db = MagicMock()
    mock_session.return_value = db
    db.query.return_value.filter.return_value.all.return_value = [
        _gl_cfg("app1", project_ids='["g/good","g/bad"]'),
    ]

    call_args = {"n": 0}

    def gl_side(cfg, path, params=None):
        call_args["n"] += 1
        if "g%2Fbad" in path or "bad" in path:
            raise FE(401, "Unauthorized")
        if "merge_requests" in path:
            return [_mr(iid=1, author="alice")], {}
        return {"id": 1, "name": "good", "path_with_namespace": "g/good", "web_url": ""}, {}

    mock_gl_get.side_effect = gl_side

    resp = client.get("/api/gitlab/all-mrs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_mrs"] == 1
    assert data["all_mrs"][0]["author"] == "alice"


@patch("web.routers.gitlab_routes._gl_get")
@patch("web.routers.gitlab_routes.SessionLocal")
def test_all_mrs_merges_multiple_configs(mock_session, mock_gl_get):
    """MRs from two different app configs must both appear in all_mrs."""
    db = MagicMock()
    mock_session.return_value = db
    db.query.return_value.filter.return_value.all.return_value = [
        _gl_cfg("app1", project_ids='["g/repo1"]'),
        _gl_cfg("app2", project_ids='["g/repo2"]'),
    ]

    proj_ids = {"g/repo1": 10, "g/repo2": 20}

    def gl_side(cfg, path, params=None):
        for pid_str, proj_id in proj_ids.items():
            encoded = pid_str.replace("/", "%2F")
            if encoded in path and "merge_requests" not in path:
                return {"id": proj_id, "name": pid_str.split("/")[1],
                        "path_with_namespace": pid_str, "web_url": ""}, {}
            if encoded in path and "merge_requests" in path:
                return [_mr(iid=proj_id, author=f"user_{proj_id}")], {}
        return {}, {}

    mock_gl_get.side_effect = gl_side

    resp = client.get("/api/gitlab/all-mrs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_mrs"] == 2
    app_ids = {m["app_id"] for m in data["all_mrs"]}
    assert "app1" in app_ids
    assert "app2" in app_ids
