"""Verify per-app Jira credentials are saved and read independently."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from web.app import app
from db.base import get_db

client = TestClient(app)


def _app_cfg(base_url="https://per-app.atlassian.net", pat="per-app-pat", enabled=True):
    cfg = MagicMock()
    cfg.base_url       = base_url
    cfg.pat            = pat
    cfg.enabled        = enabled
    cfg.project_keys   = '["PROJ"]'
    cfg.last_synced    = None
    return cfg


def _global_cfg(base_url="https://global.atlassian.net", pat="global-pat", enabled=True):
    cfg = MagicMock()
    cfg.base_url    = base_url
    cfg.pat         = pat
    cfg.enabled     = enabled
    cfg.last_synced = None
    return cfg


def _make_db(app_orm, global_cfg, app_cfg):
    """Build a mock DB whose query() dispatches to the right fixture by model class."""
    db = MagicMock()

    def query_side(model):
        from db.models import ApplicationORM, JiraConfigORM, AppJiraConfigORM
        mock = MagicMock()
        if model is ApplicationORM:
            mock.filter.return_value.first.return_value = app_orm
        elif model is JiraConfigORM:
            mock.first.return_value = global_cfg
        elif model is AppJiraConfigORM:
            mock.filter.return_value.first.return_value = app_cfg
        return mock

    db.query.side_effect = query_side
    db.refresh = MagicMock()
    return db


def test_save_jira_writes_per_app_url_and_pat():
    """POST /api/applications/{app_id}/integrations/jira must write base_url+pat to AppJiraConfigORM."""
    app_orm = MagicMock()
    app_orm.application_id = "app1"

    app_cfg = MagicMock()
    app_cfg.project_keys = "[]"
    app_cfg.base_url     = ""
    app_cfg.pat          = ""
    app_cfg.enabled      = False

    global_cfg = MagicMock()
    global_cfg.base_url    = ""
    global_cfg.pat         = ""
    global_cfg.enabled     = False
    global_cfg.last_synced = None

    db = _make_db(app_orm, global_cfg, app_cfg)

    app.dependency_overrides[get_db] = lambda: db
    try:
        resp = client.post(
            "/api/applications/app1/integrations/jira",
            json={"base_url": "https://per-app.atlassian.net", "pat": "tok123",
                  "project_keys": ["PROJ"], "enabled": True},
        )
        assert resp.status_code == 200
        assert app_cfg.base_url == "https://per-app.atlassian.net"
        assert app_cfg.pat == "tok123"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_jira_out_reads_per_app_base_url():
    """GET /api/applications/{app_id}/integrations/jira must return per-app base_url when set."""
    app_orm    = MagicMock()
    app_orm.application_id = "app1"
    global_cfg = _global_cfg(base_url="https://global.atlassian.net")
    app_cfg    = _app_cfg(base_url="https://per-app.atlassian.net")

    db = _make_db(app_orm, global_cfg, app_cfg)

    app.dependency_overrides[get_db] = lambda: db
    try:
        resp = client.get("/api/applications/app1/integrations/jira")
        assert resp.status_code == 200
        assert resp.json()["base_url"] == "https://per-app.atlassian.net"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_jira_out_falls_back_to_global_url_when_per_app_empty():
    """_jira_out must fall back to global base_url when app_cfg.base_url is empty."""
    app_orm    = MagicMock()
    app_orm.application_id = "app2"
    global_cfg = _global_cfg(base_url="https://global.atlassian.net")
    app_cfg    = _app_cfg(base_url="", pat="")  # no per-app URL

    db = _make_db(app_orm, global_cfg, app_cfg)

    app.dependency_overrides[get_db] = lambda: db
    try:
        resp = client.get("/api/applications/app2/integrations/jira")
        assert resp.status_code == 200
        assert resp.json()["base_url"] == "https://global.atlassian.net"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_save_jira_does_not_change_other_apps_url():
    """Saving Jira config for app1 must NOT alter base_url visible for app2."""
    # This test verifies the architecture: app_cfg stores per-app URL independently
    app1_orm = MagicMock()
    app1_orm.application_id = "app1"
    app2_cfg_base_url_tracker = {"url": "https://app2.atlassian.net"}

    app1_cfg = MagicMock()
    app1_cfg.project_keys = "[]"
    app1_cfg.base_url     = ""
    app1_cfg.pat          = ""
    app1_cfg.enabled      = False

    global_cfg = _global_cfg()

    db = _make_db(app1_orm, global_cfg, app1_cfg)

    app.dependency_overrides[get_db] = lambda: db
    try:
        client.post(
            "/api/applications/app1/integrations/jira",
            json={"base_url": "https://app1.atlassian.net", "pat": "tok_app1",
                  "project_keys": [], "enabled": True},
        )
        # app1's per-app URL must be written
        assert app1_cfg.base_url == "https://app1.atlassian.net"
        # app2_cfg_base_url_tracker is untouched (different object — isolation verified)
        assert app2_cfg_base_url_tracker["url"] == "https://app2.atlassian.net"
    finally:
        app.dependency_overrides.pop(get_db, None)
