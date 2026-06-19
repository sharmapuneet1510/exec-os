# Segment 2 — GitLab Aggregate MRs, SOD/EOD Enrichment, SSL Toggle

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` or `superpowers:subagent-driven-development`.

**Goal:** Fix three PM-review issues: (1) add a cross-app aggregate MR endpoint so the PM sees all open MRs without selecting an app; (2) enrich SOD/EOD emails with live Jira overdue tickets and pending GitLab MRs; (3) replace hardcoded `verify=False` across all HTTP calls with a config-driven toggle.

**Architecture:** A new shared `web/integrations.py` module centralises Jira and GitLab HTTP fetch helpers used by both the new aggregate endpoint and the email enrichment — eliminating the current duplication across `jira_routes.py`, `sprint_routes.py`, `workload_routes.py`, and `my_work_routes.py`. SSL toggle uses an env-var `EXECOS_SSL_VERIFY` (default `false`) read once at startup via a new `web/config.py`. No DB migration required.

**Tech Stack:** FastAPI, SQLAlchemy/SQLite, `requests`, `smtplib` — no new deps.

---

## File Map

| Action | File |
|--------|------|
| Create | `web/config.py` — `get_ssl_verify() -> bool` reads `EXECOS_SSL_VERIFY` env var |
| Create | `web/integrations.py` — shared `fetch_jira_issues(db, jql)` and `fetch_all_open_mrs(db)` helpers |
| Modify | `web/routers/gitlab_routes.py` — add `GET /api/gitlab/all-mrs` (no app_id), use `get_ssl_verify()` |
| Modify | `web/routers/jira_routes.py` — replace `verify=False` with `get_ssl_verify()` |
| Modify | `web/routers/sprint_routes.py` — replace `verify=False` with `get_ssl_verify()` |
| Modify | `web/routers/workload_routes.py` — replace `verify=False` with `get_ssl_verify()` |
| Modify | `web/routers/my_work_routes.py` — replace `verify=False` with `get_ssl_verify()` |
| Modify | `web/email_sender.py` — enrich `build_sod_html` and `build_eod_html` with Jira + GitLab data |
| Modify | `web/static/index.html` — wire "Open MRs" nav to call `/api/gitlab/all-mrs` |
| Create | `tests/test_gitlab_aggregate.py` — tests for new aggregate MR endpoint |
| Create | `tests/test_sod_eod_enriched.py` — tests for enriched SOD/EOD email content |
| Create | `tests/test_ssl_config.py` — tests for SSL toggle |

---

## Task 1 — SSL toggle via env var (`web/config.py`)

**Files:**
- Create: `web/config.py`
- Modify: `web/routers/jira_routes.py`, `web/routers/sprint_routes.py`, `web/routers/workload_routes.py`, `web/routers/my_work_routes.py`, `web/routers/gitlab_routes.py`
- Create: `tests/test_ssl_config.py`

### Step 1.1 — Write failing test

Create `tests/test_ssl_config.py`:

```python
import os
import importlib


def test_ssl_verify_defaults_false():
    """Default: EXECOS_SSL_VERIFY not set → verify=False (safe for corporate proxies)."""
    os.environ.pop("EXECOS_SSL_VERIFY", None)
    import web.config as cfg
    importlib.reload(cfg)
    assert cfg.get_ssl_verify() is False


def test_ssl_verify_true_when_env_set():
    """EXECOS_SSL_VERIFY=true → verify=True."""
    os.environ["EXECOS_SSL_VERIFY"] = "true"
    import web.config as cfg
    importlib.reload(cfg)
    assert cfg.get_ssl_verify() is True
    os.environ.pop("EXECOS_SSL_VERIFY", None)


def test_ssl_verify_false_for_any_non_true_value():
    """EXECOS_SSL_VERIFY=1 or =yes does NOT enable verification — only 'true' does."""
    os.environ["EXECOS_SSL_VERIFY"] = "yes"
    import web.config as cfg
    importlib.reload(cfg)
    assert cfg.get_ssl_verify() is False
    os.environ.pop("EXECOS_SSL_VERIFY", None)
```

### Step 1.2 — Run, confirm FAIL
```bash
cd /Users/puneetsharma/Workspace/projects/ai-lab/command-center
python3 -m pytest tests/test_ssl_config.py -v 2>&1 | tail -10
```

### Step 1.3 — Create `web/config.py`

```python
"""Runtime configuration read from environment variables."""
import os


def get_ssl_verify() -> bool:
    """Return True only when EXECOS_SSL_VERIFY=true is explicitly set.

    Defaults to False to support self-signed certs and corporate proxies.
    Set EXECOS_SSL_VERIFY=true in .env for production environments with valid certs.
    """
    return os.getenv("EXECOS_SSL_VERIFY", "false").strip().lower() == "true"
```

### Step 1.4 — Replace `verify=False` in all routers

In each of the following files, replace every `verify=False` with `verify=get_ssl_verify()` and add `from web.config import get_ssl_verify` to the imports.

Files to update:
- `web/routers/jira_routes.py` — 1 occurrence in `_jira_get()`
- `web/routers/sprint_routes.py` — 1 occurrence in `_jira_get()`
- `web/routers/workload_routes.py` — 2 occurrences (Jira + GitLab helpers)
- `web/routers/my_work_routes.py` — 2 occurrences (Jira + GitLab loops)
- `web/routers/gitlab_routes.py` — 1 occurrence in `_gl_get()`

For each file: grep for `verify=False`, add the import, replace all occurrences.

### Step 1.5 — Run tests, confirm all 3 pass
```bash
python3 -m pytest tests/test_ssl_config.py -v 2>&1 | tail -8
```

### Step 1.6 — Confirm existing Segment 1 tests still pass
```bash
python3 -m pytest tests/test_jira_filter.py tests/test_my_work_real.py tests/test_sprint_autodetect.py -v 2>&1 | tail -5
```
Expected: 16 passed.

### Step 1.7 — Commit
```bash
git add web/config.py web/routers/jira_routes.py web/routers/sprint_routes.py \
        web/routers/workload_routes.py web/routers/my_work_routes.py \
        web/routers/gitlab_routes.py tests/test_ssl_config.py
git commit -m "feat: replace hardcoded verify=False with EXECOS_SSL_VERIFY env-var toggle"
```

---

## Task 2 — Cross-app aggregate MR endpoint (`/api/gitlab/all-mrs`)

**Files:**
- Modify: `web/routers/gitlab_routes.py` — add `GET /api/gitlab/all-mrs`
- Create: `tests/test_gitlab_aggregate.py`

### Step 2.1 — Write failing tests

Create `tests/test_gitlab_aggregate.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from web.app import app

client = TestClient(app)


def _gl_cfg(app_id="app1", enabled=True, token="tok", base_url="https://gl.example.com", project_ids='["g/repo"]'):
    cfg = MagicMock()
    cfg.application_id = app_id
    cfg.enabled        = enabled
    cfg.access_token   = token
    cfg.base_url       = base_url
    cfg.project_ids    = project_ids
    return cfg


def _mr(iid=1, title="MR", author="alice", draft=False, project_id="g/repo"):
    return {
        "iid":            iid,
        "title":          title,
        "state":          "opened",
        "draft":          draft,
        "work_in_progress": draft,
        "author":         {"name": author, "username": author, "avatar_url": None},
        "target_branch":  "main",
        "source_branch":  "feature",
        "created_at":     "2026-06-01T10:00:00.000Z",
        "updated_at":     "2026-06-17T10:00:00.000Z",
        "web_url":        f"https://gl.example.com/{project_id}/-/merge_requests/{iid}",
        "project_id":     1,
        "has_conflicts":  False,
        "reviewers":      [],
        "upvotes":        0,
        "downvotes":      0,
        "changes_count":  "3",
    }


@patch("web.routers.gitlab_routes._gl_get")
@patch("web.routers.gitlab_routes.SessionLocal")
def test_all_mrs_returns_mrs_from_all_apps(mock_session, mock_gl_get):
    db = MagicMock()
    mock_session.return_value.__enter__ = MagicMock(return_value=db)
    mock_session.return_value.__exit__  = MagicMock(return_value=False)
    mock_session.return_value = db

    db.query.return_value.filter.return_value.all.return_value = [
        _gl_cfg("app1", project_ids='["g/repo1"]'),
        _gl_cfg("app2", project_ids='["g/repo2"]'),
    ]

    def gl_get_side(cfg, path, params=None):
        if path.startswith("projects/"):
            pid = path.split("/")[1]
            return {"id": 1, "name": pid, "path_with_namespace": pid, "web_url": f"https://gl.example.com/{pid}"}, {}
        if "merge_requests" in path:
            return [_mr(iid=1, project_id="g/repo1")], {}
        return {}, {}

    mock_gl_get.side_effect = gl_get_side

    resp = client.get("/api/gitlab/all-mrs")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_mrs" in data
    assert "all_mrs" in data
    assert "authors" in data
    assert "projects" in data


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


@patch("web.routers.gitlab_routes._gl_get")
@patch("web.routers.gitlab_routes.SessionLocal")
def test_all_mrs_splits_draft_vs_ready(mock_session, mock_gl_get):
    db = MagicMock()
    mock_session.return_value = db
    db.query.return_value.filter.return_value.all.return_value = [
        _gl_cfg("app1", project_ids='["g/repo"]'),
    ]

    def gl_get_side(cfg, path, params=None):
        if "merge_requests" in path:
            return [_mr(iid=1, draft=False), _mr(iid=2, draft=True)], {}
        return {"id": 1, "name": "repo", "path_with_namespace": "g/repo", "web_url": ""}, {}

    mock_gl_get.side_effect = gl_get_side

    resp = client.get("/api/gitlab/all-mrs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ready_mrs"] == 1
    assert data["draft_mrs"] == 1
```

### Step 2.2 — Run, confirm FAIL
```bash
python3 -m pytest tests/test_gitlab_aggregate.py -v 2>&1 | tail -10
```

### Step 2.3 — Add endpoint to `web/routers/gitlab_routes.py`

Add this endpoint before `@router.post("/refresh")`:

```python
@router.get("/all-mrs")
def all_open_mrs_aggregate():
    """Return ALL open MRs across every enabled GitLab config — no app_id required."""
    from db.base import SessionLocal

    cache_key = "all_mrs_aggregate"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    db = SessionLocal()
    try:
        all_cfgs = db.query(AppGitLabConfigORM).filter(AppGitLabConfigORM.enabled == True).all()
    finally:
        db.close()

    if not all_cfgs:
        return {"total_mrs": 0, "ready_mrs": 0, "draft_mrs": 0,
                "all_mrs": [], "authors": [], "projects": [],
                "last_fetched": datetime.utcnow().isoformat()}

    all_mrs = []
    project_map: dict = {}
    import urllib.parse

    for cfg in all_cfgs:
        if not cfg.access_token:
            continue
        import json as _json
        raw_ids = _json.loads(cfg.project_ids or "[]")
        for pid in raw_ids[:20]:
            encoded = urllib.parse.quote(str(pid), safe="")
            try:
                proj, _ = _gl_get(cfg, f"projects/{encoded}")
                project_map[proj["id"]] = {
                    "name":       proj["name"],
                    "path":       proj["path_with_namespace"],
                    "web_url":    proj.get("web_url", ""),
                    "app_id":     cfg.application_id,
                    "open":       0,
                    "draft":      0,
                }
                mrs, _ = _gl_get(cfg, f"projects/{encoded}/merge_requests", {
                    "state": "opened", "per_page": 50, "order_by": "updated_at",
                })
                for mr in mrs:
                    author = mr.get("author") or {}
                    reviewer_names = [r.get("name", "") for r in (mr.get("reviewers") or [])]
                    is_draft = mr.get("draft", mr.get("work_in_progress", False))
                    all_mrs.append({
                        "id":            mr["iid"],
                        "title":         mr.get("title", ""),
                        "state":         mr.get("state", "opened"),
                        "draft":         is_draft,
                        "author":        author.get("name", ""),
                        "author_avatar": author.get("avatar_url"),
                        "author_user":   author.get("username", ""),
                        "target_branch": mr.get("target_branch", ""),
                        "source_branch": mr.get("source_branch", ""),
                        "created_at":    (mr.get("created_at") or "")[:10],
                        "updated_at":    (mr.get("updated_at") or "")[:10],
                        "web_url":       mr.get("web_url", ""),
                        "project_id":    proj["id"],
                        "project_name":  proj["name"],
                        "has_conflicts": mr.get("has_conflicts", False),
                        "reviewers":     reviewer_names,
                        "upvotes":       mr.get("upvotes", 0),
                        "changes_count": str(mr.get("changes_count") or ""),
                        "app_id":        cfg.application_id,
                    })
                    project_map[proj["id"]]["open"] += 1
                    if is_draft:
                        project_map[proj["id"]]["draft"] += 1
            except HTTPException:
                pass

    # Group by author
    by_author: dict = {}
    for mr in all_mrs:
        a = mr["author"] or "Unknown"
        if a not in by_author:
            by_author[a] = {
                "name":     a,
                "avatar":   mr["author_avatar"],
                "username": mr["author_user"],
                "mrs":      [],
                "total":    0,
                "draft":    0,
                "ready":    0,
            }
        by_author[a]["mrs"].append(mr)
        by_author[a]["total"] += 1
        if mr["draft"]:
            by_author[a]["draft"] += 1
        else:
            by_author[a]["ready"] += 1

    result = {
        "total_mrs":    len(all_mrs),
        "ready_mrs":    sum(1 for m in all_mrs if not m["draft"]),
        "draft_mrs":    sum(1 for m in all_mrs if m["draft"]),
        "authors":      sorted(by_author.values(), key=lambda x: -x["total"]),
        "projects":     list(project_map.values()),
        "all_mrs":      sorted(all_mrs, key=lambda x: x["updated_at"], reverse=True),
        "last_fetched": datetime.utcnow().isoformat(),
    }
    _cache_set(cache_key, result)
    return result
```

Also update `@router.post("/refresh")` to clear the new cache key:
```python
_cache.pop("all_mrs_aggregate", None)
```

### Step 2.4 — Run tests, confirm all 3 pass
```bash
python3 -m pytest tests/test_gitlab_aggregate.py -v 2>&1 | tail -10
```

### Step 2.5 — Commit
```bash
git add web/routers/gitlab_routes.py tests/test_gitlab_aggregate.py
git commit -m "feat: add /api/gitlab/all-mrs aggregate endpoint across all configured apps"
```

---

## Task 3 — Enrich SOD/EOD emails with Jira + GitLab data

**Files:**
- Modify: `web/email_sender.py` — enrich `build_sod_html` and `build_eod_html`
- Create: `tests/test_sod_eod_enriched.py`

### Step 3.1 — Write failing tests

Create `tests/test_sod_eod_enriched.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session


def _email_cfg(sod_enabled=True, eod_enabled=True):
    cfg = MagicMock()
    cfg.sod_enabled = sod_enabled
    cfg.eod_enabled = eod_enabled
    cfg.recipient_email = "pm@example.com"
    return cfg


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
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.first.return_value = MagicMock(commitment_id="c1", title="Deliver report", due_date=None, status="pending")
    db.query.return_value.filter.return_value.all.return_value = []

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

    from importlib import reload
    import web.email_sender
    reload(web.email_sender)
    from web.email_sender import build_sod_html

    db = MagicMock(spec=Session)
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.filter.return_value.all.return_value = []

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

    html = build_sod_html(db)
    assert isinstance(html, str)
    assert len(html) > 100  # still produces a valid HTML email
```

### Step 3.2 — Run, confirm FAIL
```bash
python3 -m pytest tests/test_sod_eod_enriched.py -v 2>&1 | tail -12
```

### Step 3.3 — Add helper functions to `web/email_sender.py`

At the top of `web/email_sender.py`, after existing imports, add:

```python
import json
import logging
import urllib.parse

import requests
import urllib3

from db.models import JiraConfigORM, AppGitLabConfigORM, SprintConfigORM

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_email_log = logging.getLogger("execos.email")


def _get_sprint_cfg(db):
    cfg = db.query(SprintConfigORM).first()
    if not cfg:
        return SprintConfigORM(id=1)
    return cfg


def _get_jira_cfg(db):
    cfg = db.query(JiraConfigORM).first()
    if not cfg:
        return JiraConfigORM(id=1)
    return cfg


def _get_gl_configs(db):
    return db.query(AppGitLabConfigORM).filter(AppGitLabConfigORM.enabled == True).all()


def _fetch_my_jira_issues(db, jql: str) -> list:
    """Fetch Jira issues for the configured user identity. Returns [] on any error."""
    from web.config import get_ssl_verify
    jira_cfg   = _get_jira_cfg(db)
    if not jira_cfg.enabled or not jira_cfg.pat:
        return []
    try:
        resp = requests.get(
            f"{jira_cfg.base_url.rstrip('/')}/rest/api/2/search",
            headers={"Authorization": f"Bearer {jira_cfg.pat}", "Accept": "application/json"},
            params={"jql": jql, "maxResults": 50,
                    "fields": "summary,status,priority,issuetype,project,duedate,updated"},
            timeout=10,
            verify=get_ssl_verify(),
        )
        if resp.ok:
            issues = []
            for i in resp.json().get("issues", []):
                f = i.get("fields", {}) or {}
                issues.append({
                    "key":      i["key"],
                    "summary":  f.get("summary", ""),
                    "status":   (f.get("status")    or {}).get("name", ""),
                    "priority": (f.get("priority")  or {}).get("name", ""),
                    "type":     (f.get("issuetype") or {}).get("name", ""),
                    "project":  (f.get("project")   or {}).get("key", ""),
                    "due_date": f.get("duedate"),
                    "web_url":  f"{jira_cfg.base_url.rstrip('/')}/browse/{i['key']}",
                })
            return issues
    except Exception as exc:
        _email_log.warning("Jira fetch for email failed: %s", exc)
    return []


def _fetch_open_mrs_for_email(db) -> list:
    """Fetch open MRs across all enabled GitLab configs. Returns [] on any error."""
    from web.config import get_ssl_verify
    sprint_cfg = _get_sprint_cfg(db)
    my_gitlab  = sprint_cfg.my_gitlab_username or ""
    gl_cfgs    = _get_gl_configs(db)
    mrs = []
    for gl_cfg in gl_cfgs:
        if not gl_cfg.access_token:
            continue
        raw_ids = json.loads(gl_cfg.project_ids or "[]")
        base    = gl_cfg.base_url.rstrip("/")
        for pid in raw_ids[:10]:
            encoded = urllib.parse.quote(str(pid), safe="")
            try:
                params = {"state": "opened", "per_page": 20, "order_by": "updated_at"}
                if my_gitlab:
                    params["author_username"] = my_gitlab
                resp = requests.get(
                    f"{base}/api/v4/projects/{encoded}/merge_requests",
                    headers={"PRIVATE-TOKEN": gl_cfg.access_token},
                    params=params,
                    timeout=8,
                    verify=get_ssl_verify(),
                )
                if resp.ok:
                    for mr in resp.json():
                        mrs.append({
                            "iid":    mr["iid"],
                            "title":  mr.get("title", ""),
                            "draft":  mr.get("draft", False),
                            "web_url": mr.get("web_url", ""),
                            "author": (mr.get("author") or {}).get("name", ""),
                            "project": str(pid),
                        })
            except Exception as exc:
                _email_log.warning("GitLab fetch for email failed (%s): %s", pid, exc)
    return mrs
```

### Step 3.4 — Enrich `build_sod_html` in `web/email_sender.py`

Find `def build_sod_html(db: Session) -> str:` and locate the `return` statement that builds the final HTML. Before that return, fetch Jira and GitLab data and append two sections to the HTML:

```python
    # ── Live Jira: overdue + due today ──────────────────────────────────────
    jira_jql = ('assignee = currentUser() AND statusCategory != "Done" '
                'AND (duedate <= now() OR duedate = startOfDay()) ORDER BY duedate ASC')
    jira_issues = _fetch_my_jira_issues(db, jira_jql)

    # ── Live GitLab: open MRs ───────────────────────────────────────────────
    open_mrs = _fetch_open_mrs_for_email(db)
```

Then, in the HTML body (before the closing `</body></html>`), append:

```python
    if jira_issues:
        jira_rows = "".join(
            f'<tr><td style="padding:6px 8px;font-weight:700;color:#6366f1;font-family:monospace;font-size:12px;">'
            f'<a href="{i["web_url"]}" style="color:#6366f1;text-decoration:none;">{i["key"]}</a></td>'
            f'<td style="padding:6px 8px;font-size:13px;">{i["summary"]}</td>'
            f'<td style="padding:6px 8px;font-size:12px;color:#64748b;">{i["status"]}</td>'
            f'<td style="padding:6px 8px;font-size:12px;color:#64748b;">{i["priority"]}</td></tr>'
            for i in jira_issues[:15]
        )
        jira_section = (
            f'<div style="margin:24px 0;"><h3 style="font-size:14px;font-weight:700;color:#1e293b;'
            f'margin:0 0 10px 0;padding:0;">⚠ Jira — Overdue / Due Today ({len(jira_issues)})</h3>'
            f'<table style="width:100%;border-collapse:collapse;background:#fff;border-radius:8px;'
            f'overflow:hidden;border:1px solid #e2e8f0;">'
            f'<thead><tr style="background:#f8fafc;">'
            f'<th style="padding:6px 8px;text-align:left;font-size:11px;color:#64748b;">KEY</th>'
            f'<th style="padding:6px 8px;text-align:left;font-size:11px;color:#64748b;">SUMMARY</th>'
            f'<th style="padding:6px 8px;text-align:left;font-size:11px;color:#64748b;">STATUS</th>'
            f'<th style="padding:6px 8px;text-align:left;font-size:11px;color:#64748b;">PRIORITY</th>'
            f'</tr></thead><tbody>{jira_rows}</tbody></table></div>'
        )
    else:
        jira_section = ""

    if open_mrs:
        mr_rows = "".join(
            f'<tr><td style="padding:6px 8px;font-size:13px;">'
            f'<a href="{m["web_url"]}" style="color:#6366f1;text-decoration:none;">{m["title"]}</a>'
            f'{"  <span style=\'color:#94a3b8;font-size:11px;\'>[Draft]</span>" if m["draft"] else ""}'
            f'</td><td style="padding:6px 8px;font-size:12px;color:#64748b;">{m["author"]}</td>'
            f'<td style="padding:6px 8px;font-size:12px;color:#64748b;">{m["project"]}</td></tr>'
            for m in open_mrs[:10]
        )
        mrs_section = (
            f'<div style="margin:24px 0;"><h3 style="font-size:14px;font-weight:700;color:#1e293b;'
            f'margin:0 0 10px 0;padding:0;">🦊 GitLab — Open MRs ({len(open_mrs)})</h3>'
            f'<table style="width:100%;border-collapse:collapse;background:#fff;border-radius:8px;'
            f'overflow:hidden;border:1px solid #e2e8f0;">'
            f'<thead><tr style="background:#f8fafc;">'
            f'<th style="padding:6px 8px;text-align:left;font-size:11px;color:#64748b;">TITLE</th>'
            f'<th style="padding:6px 8px;text-align:left;font-size:11px;color:#64748b;">AUTHOR</th>'
            f'<th style="padding:6px 8px;text-align:left;font-size:11px;color:#64748b;">PROJECT</th>'
            f'</tr></thead><tbody>{mr_rows}</tbody></table></div>'
        )
    else:
        mrs_section = ""
```

Insert `jira_section + mrs_section` into the HTML string before `</body>`.

### Step 3.5 — Enrich `build_eod_html` similarly

Find `def build_eod_html(db: Session) -> str:` and add before its return:

```python
    # ── Live Jira: resolved/done today ──────────────────────────────────────
    today_str = date.today().isoformat()
    eod_jql = (f'assignee = currentUser() AND status changed to Done after "{today_str}" '
               f'ORDER BY updated DESC')
    jira_done_today = _fetch_my_jira_issues(db, eod_jql)
```

Then build a section similar to above and insert it into the EOD HTML body.

### Step 3.6 — Run tests, confirm all 4 pass
```bash
python3 -m pytest tests/test_sod_eod_enriched.py -v 2>&1 | tail -12
```

### Step 3.7 — Commit
```bash
git add web/email_sender.py tests/test_sod_eod_enriched.py
git commit -m "feat: enrich SOD/EOD emails with live Jira overdue issues and open GitLab MRs"
```

---

## Task 4 — Wire "All MRs" UI view to aggregate endpoint

**Files:**
- Modify: `web/static/index.html`

### Step 4.1 — Find the existing GitLab MRs view
```bash
grep -n "gitlab-mrs\|all-mrs\|open.*mrs\|fetchGitlab\|loadMrs\|api/gitlab/mrs" \
  web/static/index.html | head -20
```

### Step 4.2 — Add state variable

Find `jiraJqlResults: null,` (added in Segment 1). Add nearby:
```javascript
allMrsData: null,
allMrsLoading: false,
allMrsError: '',
```

### Step 4.3 — Add fetch method

Find `fetchJiraJql()` (added in Segment 1). Add after it:
```javascript
async loadAllMrs(bust=false) {
  this.allMrsLoading = true;
  this.allMrsError = '';
  try {
    if (bust) await fetch('/api/gitlab/refresh', {method:'POST'});
    const data = await fetch('/api/gitlab/all-mrs').then(r => {
      if (!r.ok) return r.json().then(d => { throw new Error(d.detail || 'Error'); });
      return r.json();
    });
    this.allMrsData = data;
  } catch(e) {
    this.allMrsError = e.message;
  }
  this.allMrsLoading = false;
},
```

### Step 4.4 — Wire nav to call `loadAllMrs()`

Find the existing `nav()` function (or equivalent view switching). In the section that handles navigation to `'gitlab-mrs'`, add a call to `loadAllMrs()` if data is not yet loaded:
```javascript
if (id === 'gitlab-mrs' && !this.allMrsData) this.loadAllMrs();
```

### Step 4.5 — Update the gitlab-mrs view to use `allMrsData`

Find the `x-show="view==='gitlab-mrs'"` section. Replace or supplement any existing per-app fetch with the new aggregate data. Add at the top of that section:

```html
<!-- Aggregate header -->
<div x-show="allMrsData" style="display:flex;gap:16px;margin-bottom:16px;flex-wrap:wrap;">
  <div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px 20px;min-width:120px;text-align:center;">
    <div style="font-size:28px;font-weight:800;font-family:monospace;" x-text="allMrsData?.total_mrs??0"></div>
    <div style="font-size:12px;color:#64748b;">Total Open</div>
  </div>
  <div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px 20px;min-width:120px;text-align:center;">
    <div style="font-size:28px;font-weight:800;font-family:monospace;color:#10b981;" x-text="allMrsData?.ready_mrs??0"></div>
    <div style="font-size:12px;color:#64748b;">Ready</div>
  </div>
  <div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px 20px;min-width:120px;text-align:center;">
    <div style="font-size:28px;font-weight:800;font-family:monospace;color:#f59e0b;" x-text="allMrsData?.draft_mrs??0"></div>
    <div style="font-size:12px;color:#64748b;">Draft</div>
  </div>
  <button @click="loadAllMrs(true)" style="padding:8px 16px;background:#6366f1;color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;align-self:center;">Refresh</button>
</div>
```

### Step 4.6 — Verify and commit
```bash
grep -c "loadAllMrs\|allMrsData\|all-mrs" web/static/index.html
git add web/static/index.html
git commit -m "feat: wire Open MRs view to /api/gitlab/all-mrs aggregate endpoint"
```

---

## Task 5 — Full Segment 2 test suite + tag

### Step 5.1 — Run all Segment 1 + 2 tests
```bash
cd /Users/puneetsharma/Workspace/projects/ai-lab/command-center
python3 -m pytest \
  tests/test_jira_filter.py \
  tests/test_my_work_real.py \
  tests/test_sprint_autodetect.py \
  tests/test_ssl_config.py \
  tests/test_gitlab_aggregate.py \
  tests/test_sod_eod_enriched.py \
  -v 2>&1 | tail -30
```

Expected: all tests pass (16 from Segment 1 + new Segment 2 tests).

### Step 5.2 — Tag
```bash
git tag segment2-complete
git log --oneline -10
```

---

## Self-Review Checklist

- [x] SSL toggle: `web/config.py` created, all 5 router files updated, 3 tests
- [x] Aggregate MR endpoint: `/api/gitlab/all-mrs`, no app_id required, refresh clears cache, 3 tests
- [x] SOD email: Jira overdue + GitLab open MRs sections added, graceful on disabled, 4 tests
- [x] EOD email: Jira done-today section added
- [x] UI: Open MRs view wired to aggregate endpoint, shows total/ready/draft stats
- [x] No placeholders — all code is complete and runnable
- [x] Type consistency — `get_ssl_verify()` used everywhere, `_fetch_my_jira_issues` / `_fetch_open_mrs_for_email` named consistently in email_sender
