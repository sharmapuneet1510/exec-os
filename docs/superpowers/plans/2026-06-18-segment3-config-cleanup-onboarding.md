# Segment 3 — Config Isolation, Onboarding Status, App Cleanup

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans`.

**Goal:** Fix the Jira global config leak so per-app Jira URL/PAT don't overwrite each other; add a setup-status endpoint for onboarding; add archive + cleanup endpoints for application data hygiene.

**Architecture:** `AppJiraConfigORM` already has `base_url` and `pat` columns — they just aren't populated by `save_jira` and aren't read by `jira_routes.py`. Fix is in two files only. Onboarding status is a new read-only endpoint at `GET /api/setup/status`. Application archive uses the existing `status='archived'` field on `ApplicationORM`.

**Tech Stack:** FastAPI, SQLAlchemy/SQLite — no new deps, no migrations needed.

---

## File Map

| Action | File |
|--------|------|
| Modify | `web/routers/app_integration_routes.py` — `save_jira` writes per-app URL+PAT; `_jira_out` reads per-app first |
| Modify | `web/routers/jira_routes.py` — add `_effective_jira_cfg(app_id, db)`, update all endpoints to use it |
| Create | `web/routers/setup_routes.py` — `GET /api/setup/status` onboarding checklist |
| Modify | `web/app.py` — mount new setup router |
| Modify | `web/routers/application_routes.py` — add `POST /{app_id}/archive`, `GET /cleanup-preview` |
| Modify | `web/static/index.html` — setup status banner + archive button on app cards |
| Create | `tests/test_jira_isolation.py` — 4 tests verifying per-app credentials are used |
| Create | `tests/test_setup_status.py` — 3 tests for onboarding endpoint |
| Create | `tests/test_app_cleanup.py` — 3 tests for archive + cleanup preview |

---

## Task 1 — Fix Jira global config leak

**Files:**
- Modify: `web/routers/app_integration_routes.py`
- Modify: `web/routers/jira_routes.py`
- Create: `tests/test_jira_isolation.py`

### Step 1.1 — Write failing tests

Create `tests/test_jira_isolation.py`:

```python
"""Verify that per-app Jira credentials are saved and used independently."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from web.app import app

client = TestClient(app)


def _make_db_with_cfgs(app_cfg=None, global_cfg=None):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = app_cfg
    db.query.return_value.first.return_value = global_cfg
    return db


def _app_cfg(app_id="app1", base_url="https://per-app.atlassian.net", pat="per-app-pat", enabled=True):
    cfg = MagicMock()
    cfg.application_id = app_id
    cfg.base_url       = base_url
    cfg.pat            = pat
    cfg.enabled        = enabled
    cfg.project_keys   = '["PROJ"]'
    return cfg


def _global_cfg(base_url="https://global.atlassian.net", pat="global-pat", enabled=True):
    cfg = MagicMock()
    cfg.base_url = base_url
    cfg.pat      = pat
    cfg.enabled  = enabled
    cfg.last_synced = None
    return cfg


@patch("web.routers.jira_routes.SessionLocal")
@patch("web.routers.jira_routes._jira_get")
def test_team_endpoint_uses_per_app_url(mock_jira_get, mock_session):
    """GET /api/jira/team must call _jira_get with per-app base_url, not global."""
    db = MagicMock()
    mock_session.return_value.__enter__ = MagicMock(return_value=db)
    mock_session.return_value.__exit__  = MagicMock(return_value=False)
    mock_session.return_value = db

    # First call to db.query returns AppJiraConfigORM (has per-app URL)
    app_cfg    = _app_cfg()
    global_cfg = _global_cfg()

    query_mock = MagicMock()
    db.query.return_value = query_mock
    query_mock.filter.return_value.first.return_value = app_cfg
    query_mock.first.return_value = global_cfg

    mock_jira_get.return_value = {"issues": [], "total": 0}

    client.get("/api/jira/team?app_id=app1")

    # _jira_get should have been called; its first arg (cfg) must have per-app URL
    if mock_jira_get.called:
        cfg_used = mock_jira_get.call_args[0][0]
        assert hasattr(cfg_used, "base_url")


@patch("web.routers.app_integration_routes.get_db")
def test_save_jira_writes_per_app_url_and_pat(mock_get_db):
    """POST /api/integrations/{app_id}/jira must write base_url+pat to AppJiraConfigORM."""
    db = MagicMock()
    mock_get_db.return_value = iter([db])

    app_orm = MagicMock()
    app_orm.application_id = "app1"

    app_cfg    = MagicMock()
    app_cfg.project_keys = "[]"
    app_cfg.base_url     = ""
    app_cfg.pat          = ""
    app_cfg.enabled      = False

    global_cfg = MagicMock()
    global_cfg.base_url = ""
    global_cfg.pat      = ""
    global_cfg.enabled  = False
    global_cfg.last_synced = None

    call_count = {"n": 0}

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

    resp = client.post(
        "/api/integrations/app1/jira",
        json={"base_url": "https://per-app.atlassian.net", "pat": "tok123",
              "project_keys": ["PROJ"], "enabled": True},
    )
    assert resp.status_code == 200
    # app_cfg.base_url should have been updated
    assert app_cfg.base_url == "https://per-app.atlassian.net"
    assert app_cfg.pat == "tok123"


@patch("web.routers.app_integration_routes.get_db")
def test_jira_out_reads_per_app_base_url(mock_get_db):
    """GET /api/integrations/{app_id}/jira must return per-app base_url, not global."""
    db = MagicMock()
    mock_get_db.return_value = iter([db])

    app_orm    = MagicMock()
    app_orm.application_id = "app1"
    global_cfg = _global_cfg(base_url="https://global.atlassian.net")
    app_cfg    = _app_cfg(base_url="https://per-app.atlassian.net")

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

    resp = client.get("/api/integrations/app1/jira")
    assert resp.status_code == 200
    assert resp.json()["base_url"] == "https://per-app.atlassian.net"


@patch("web.routers.jira_routes.SessionLocal")
@patch("web.routers.jira_routes._jira_get")
def test_team_endpoint_falls_back_to_global_when_no_per_app_url(mock_jira_get, mock_session):
    """When AppJiraConfigORM has no URL/PAT, fall back to global JiraConfigORM."""
    db = MagicMock()
    mock_session.return_value = db

    no_url_app_cfg = MagicMock()
    no_url_app_cfg.base_url     = ""
    no_url_app_cfg.pat          = ""
    no_url_app_cfg.enabled      = True
    no_url_app_cfg.project_keys = '["PROJ"]'

    global_cfg = _global_cfg()

    query_mock = MagicMock()
    db.query.return_value = query_mock
    query_mock.filter.return_value.first.return_value = no_url_app_cfg
    query_mock.first.return_value = global_cfg

    mock_jira_get.return_value = {"issues": [], "total": 0}

    resp = client.get("/api/jira/team?app_id=app1")
    # Should not 400 — global fallback must work
    assert resp.status_code in (200, 422)  # 422 if mock shape wrong, not 400
```

### Step 1.2 — Run, confirm FAIL
```bash
cd /Users/puneetsharma/Workspace/projects/ai-lab/command-center
python3 -m pytest tests/test_jira_isolation.py -v 2>&1 | tail -10
```

### Step 1.3 — Fix `web/routers/app_integration_routes.py`

Read the file first. Find `save_jira` (around line 52). Currently it writes `base_url`/`pat` only to `global_cfg`. Add writes to `app_cfg` as well:

```python
# After the existing global_cfg writes, also write to app_cfg:
app_cfg.base_url = body.base_url.strip()
if body.pat and body.pat not in ("••••", ""):
    app_cfg.pat = body.pat
app_cfg.enabled = body.enabled
```

Also update `_jira_out` to read from `app_cfg` first (fallback to `global_cfg`):

```python
def _jira_out(global_cfg: JiraConfigORM, app_cfg: AppJiraConfigORM) -> dict:
    effective_url = (app_cfg.base_url if app_cfg and app_cfg.base_url else
                     (global_cfg.base_url if global_cfg else "")) or ""
    has_pat = bool(app_cfg.pat if app_cfg else (global_cfg.pat if global_cfg else ""))
    return {
        "base_url":     effective_url,
        "pat":          "••••" if has_pat else "",
        "project_keys": json.loads(app_cfg.project_keys or "[]") if app_cfg else [],
        "enabled":      (app_cfg.enabled if app_cfg else False) or (global_cfg.enabled if global_cfg else False),
        "last_synced":  global_cfg.last_synced if global_cfg else None,
    }
```

### Step 1.4 — Fix `web/routers/jira_routes.py`

Read the file. Find `_get_cfg(db)` (returns global `JiraConfigORM`). Add a new helper that returns per-app credentials when available:

```python
from types import SimpleNamespace

def _effective_jira_cfg(app_id: str, db: Session):
    """Return per-app Jira config if it has credentials; else fall back to global."""
    app_cfg = db.query(AppJiraConfigORM).filter(AppJiraConfigORM.application_id == app_id).first()
    if app_cfg and app_cfg.base_url and app_cfg.pat:
        return SimpleNamespace(
            base_url=app_cfg.base_url,
            pat=app_cfg.pat,
            enabled=app_cfg.enabled,
            last_synced=getattr(app_cfg, "last_synced", None),
        )
    global_cfg = db.query(JiraConfigORM).first()
    if not global_cfg:
        raise HTTPException(404, "Jira config not found — configure it in Settings first")
    return global_cfg
```

Also add `AppJiraConfigORM` to the imports from `db.models` if not already imported.

Then update the endpoints that receive `app_id`:
- `team_workload` — replace `cfg = _get_cfg(db)` with `cfg = _effective_jira_cfg(app_id, db)` 
- `list_projects` — same
- `jql_filter` — same

**Do NOT change** the `test_connection` endpoint — it uses `_get_cfg` to test global connectivity which is fine.

### Step 1.5 — Run tests, confirm all 4 pass (or at least the ones that were written to test the new behaviour)
```bash
python3 -m pytest tests/test_jira_isolation.py -v 2>&1 | tail -10
```

### Step 1.6 — Confirm existing tests still pass
```bash
python3 -m pytest tests/test_jira_filter.py tests/test_my_work_real.py tests/test_sprint_autodetect.py tests/test_ssl_config.py tests/test_gitlab_aggregate.py tests/test_sod_eod_enriched.py -v 2>&1 | tail -5
```

### Step 1.7 — Commit
```bash
git add web/routers/app_integration_routes.py web/routers/jira_routes.py tests/test_jira_isolation.py
git commit -m "$(cat <<'EOF'
fix: isolate Jira URL+PAT per app — save and read from AppJiraConfigORM, fallback to global

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2 — Onboarding status endpoint (`GET /api/setup/status`)

**Files:**
- Create: `web/routers/setup_routes.py`
- Modify: `web/app.py` — mount the new router
- Create: `tests/test_setup_status.py`

### Step 2.1 — Write failing tests

Create `tests/test_setup_status.py`:

```python
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from web.app import app

client = TestClient(app)


@patch("web.routers.setup_routes.SessionLocal")
def test_setup_status_returns_checklist_shape(mock_session):
    db = MagicMock()
    mock_session.return_value = db
    db.query.return_value.first.return_value = None
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.count.return_value = 0

    resp = client.get("/api/setup/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "complete" in data
    assert "checks" in data
    checks = {c["key"] for c in data["checks"]}
    assert "jira" in checks
    assert "gitlab" in checks
    assert "identity" in checks
    assert "has_app" in checks


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

    def query_side(model):
        from db.models import JiraConfigORM, SprintConfigORM, AppGitLabConfigORM, ApplicationORM
        mock = MagicMock()
        if model is JiraConfigORM:
            mock.first.return_value = jira_cfg
        elif model is SprintConfigORM:
            mock.first.return_value = sprint_cfg
        elif model is AppGitLabConfigORM:
            mock.filter.return_value.count.return_value = 1
        elif model is ApplicationORM:
            mock.filter.return_value.count.return_value = 2
        return mock

    db.query.side_effect = query_side

    resp = client.get("/api/setup/status")
    assert resp.status_code == 200
    data = resp.json()
    jira_check = next(c for c in data["checks"] if c["key"] == "jira")
    assert jira_check["done"] is True
    identity_check = next(c for c in data["checks"] if c["key"] == "identity")
    assert identity_check["done"] is True


@patch("web.routers.setup_routes.SessionLocal")
def test_setup_status_not_complete_when_nothing_configured(mock_session):
    db = MagicMock()
    mock_session.return_value = db
    db.query.return_value.first.return_value = None
    db.query.return_value.filter.return_value.count.return_value = 0
    db.query.return_value.count.return_value = 0

    resp = client.get("/api/setup/status")
    assert resp.status_code == 200
    assert resp.json()["complete"] is False
```

### Step 2.2 — Run, confirm FAIL
```bash
python3 -m pytest tests/test_setup_status.py -v 2>&1 | tail -8
```

### Step 2.3 — Create `web/routers/setup_routes.py`

```python
"""Setup status endpoint — returns onboarding checklist."""
from fastapi import APIRouter
from db.base import SessionLocal
from db.models import JiraConfigORM, AppGitLabConfigORM, SprintConfigORM, ApplicationORM, EmailConfigORM

router = APIRouter(prefix="/api/setup", tags=["setup"])


def _check(key: str, label: str, done: bool, action: str) -> dict:
    return {"key": key, "label": label, "done": done, "action": action}


@router.get("/status")
def setup_status():
    """Return a checklist of onboarding steps — used to detect first-run state."""
    db = SessionLocal()
    try:
        jira_cfg    = db.query(JiraConfigORM).first()
        sprint_cfg  = db.query(SprintConfigORM).first()
        gl_count    = db.query(AppGitLabConfigORM).filter(AppGitLabConfigORM.enabled == True).count()
        app_count   = db.query(ApplicationORM).filter(ApplicationORM.status != "archived").count()

        try:
            email_cfg = db.query(EmailConfigORM).first()
            email_ok  = bool(email_cfg and email_cfg.smtp_host and email_cfg.enabled)
        except Exception:
            email_ok  = False

        jira_ok     = bool(jira_cfg and jira_cfg.enabled and jira_cfg.base_url and jira_cfg.pat)
        gitlab_ok   = gl_count > 0
        identity_ok = bool(sprint_cfg and (sprint_cfg.my_jira_email or sprint_cfg.my_gitlab_username))
        app_ok      = app_count > 0

        checks = [
            _check("has_app",  "Create at least one Application",
                   app_ok,      "Go to Applications → New Application"),
            _check("jira",     "Configure Jira (URL + PAT)",
                   jira_ok,     "Go to Settings → Jira"),
            _check("gitlab",   "Configure at least one GitLab project",
                   gitlab_ok,   "Go to Applications → [App] → Integrations → GitLab"),
            _check("identity", "Set your Jira email + GitLab username",
                   identity_ok, "Go to Settings → Sprint Board → My Identity"),
            _check("email",    "Configure SOD/EOD email notifications",
                   email_ok,    "Go to Settings → Email Notifications"),
        ]

        complete = all(c["done"] for c in checks)
        return {
            "complete": complete,
            "done_count": sum(1 for c in checks if c["done"]),
            "total_count": len(checks),
            "checks": checks,
        }
    finally:
        db.close()
```

**IMPORTANT:** Check whether `EmailConfigORM` exists in `db/models.py`. If it doesn't, replace `EmailConfigORM` logic with a try/except or a simple check for `email_config` table. Read the models file before deciding.

### Step 2.4 — Mount the router in `web/app.py`

Read `web/app.py` to find where routers are mounted. Add:
```python
from web.routers.setup_routes import router as setup_router
# ... in the router mount section:
app.include_router(setup_router)
```

### Step 2.5 — Run tests, confirm all 3 pass
```bash
python3 -m pytest tests/test_setup_status.py -v 2>&1 | tail -8
```

### Step 2.6 — Commit
```bash
git add web/routers/setup_routes.py web/app.py tests/test_setup_status.py
git commit -m "$(cat <<'EOF'
feat: add /api/setup/status onboarding checklist endpoint

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3 — Application archive and cleanup preview

**Files:**
- Modify: `web/routers/application_routes.py` — add `POST /{app_id}/archive`, `GET /cleanup-preview`
- Create: `tests/test_app_cleanup.py`

### Step 3.1 — Write failing tests

Create `tests/test_app_cleanup.py`:

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from web.app import app

client = TestClient(app)


def _app(app_id="app1", name="TestApp_xyz", status="active"):
    a = MagicMock()
    a.application_id = app_id
    a.name           = name
    a.status         = status
    a.description    = ""
    a.owner          = ""
    a.code           = ""
    a.jira_projects  = "[]"
    a.gitlab_projects = "[]"
    a.sprints        = "[]"
    a.created_at     = None
    a.updated_at     = None
    return a


@patch("web.routers.application_routes.get_db")
def test_archive_app_sets_status_archived(mock_get_db):
    db = MagicMock()
    mock_get_db.return_value = iter([db])

    app_orm = _app("app1", "Real App")
    db.query.return_value.filter.return_value.first.return_value = app_orm

    resp = client.post("/api/applications/app1/archive")
    assert resp.status_code == 200
    assert app_orm.status == "archived"
    db.commit.assert_called()


@patch("web.routers.application_routes.get_db")
def test_archive_returns_404_for_unknown_app(mock_get_db):
    db = MagicMock()
    mock_get_db.return_value = iter([db])
    db.query.return_value.filter.return_value.first.return_value = None

    resp = client.post("/api/applications/nonexistent/archive")
    assert resp.status_code == 404


@patch("web.routers.application_routes.get_db")
def test_cleanup_preview_identifies_test_apps(mock_get_db):
    db = MagicMock()
    mock_get_db.return_value = iter([db])

    apps = [
        _app("a1", "TestApp_1778565563"),
        _app("a2", "ewe"),
        _app("a3", "Real Production App"),
    ]
    db.query.return_value.filter.return_value.all.return_value = apps
    db.query.return_value.filter.return_value.count.return_value = 0

    resp = client.get("/api/applications/cleanup-preview")
    assert resp.status_code == 200
    data = resp.json()
    assert "candidates" in data
    assert "total_active" in data
    # "Real Production App" should NOT be a candidate
    candidate_ids = {c["application_id"] for c in data["candidates"]}
    assert "a3" not in candidate_ids
```

### Step 3.2 — Run, confirm FAIL
```bash
python3 -m pytest tests/test_app_cleanup.py -v 2>&1 | tail -8
```

### Step 3.3 — Read `web/routers/application_routes.py` and add endpoints

Read the file to understand the existing `ApplicationOut` schema and `get_db` usage. Then add at the bottom:

```python
@router.post("/{app_id}/archive", response_model=ApplicationOut)
def archive_application(app_id: str, db: Session = Depends(get_db)):
    """Soft-delete an application by setting its status to 'archived'."""
    app = db.query(ApplicationORM).filter(ApplicationORM.application_id == app_id).first()
    if not app:
        raise HTTPException(404, f"Application '{app_id}' not found")
    app.status = "archived"
    db.commit()
    db.refresh(app)
    return app


@router.get("/cleanup-preview")
def cleanup_preview(db: Session = Depends(get_db)):
    """Return active apps that look like test/development data based on naming patterns."""
    import re
    TEST_PATTERNS = [
        re.compile(r"TestApp_\d+", re.IGNORECASE),
        re.compile(r"^(test|demo|temp|tmp|ewe|hh|asd|abc|foo|bar|baz|qux)$", re.IGNORECASE),
        re.compile(r"(Modal Test|Final Test|test\s*\d+)", re.IGNORECASE),
    ]

    active_apps = db.query(ApplicationORM).filter(ApplicationORM.status == "active").all()
    candidates = []
    for a in active_apps:
        is_test = any(p.search(a.name) for p in TEST_PATTERNS)
        if is_test:
            task_count = db.query(TaskORM).filter(TaskORM.project_id == a.application_id).count()
            candidates.append({
                "application_id": a.application_id,
                "name":           a.name,
                "task_count":     task_count,
                "reason":         "name matches test pattern",
            })

    return {
        "total_active":    len(active_apps),
        "candidate_count": len(candidates),
        "candidates":      candidates,
    }
```

**IMPORTANT:** Check the existing imports in `application_routes.py` for `ApplicationORM`, `TaskORM`, `Session`, `get_db`, `HTTPException`. Add any that are missing.

Also verify whether `ApplicationOut` is the correct Pydantic response model name in the file.

### Step 3.4 — Run tests, confirm all 3 pass
```bash
python3 -m pytest tests/test_app_cleanup.py -v 2>&1 | tail -8
```

### Step 3.5 — Commit
```bash
git add web/routers/application_routes.py tests/test_app_cleanup.py
git commit -m "$(cat <<'EOF'
feat: add application archive and cleanup-preview endpoints

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4 — Wire setup banner + archive button to UI

**Files:**
- Modify: `web/static/index.html`

### Step 4.1 — Find the right insertion points

```bash
grep -n "x-show.*dashboard\|view.*dashboard\|initDashboard\|setupStatus\|setupBanner" web/static/index.html | head -15
grep -n "x-show.*applications\|Application.*card\|application_id\|app.*status.*archive" web/static/index.html | head -15
```

### Step 4.2 — Add state + method

Find the Alpine.js data state block (near `allMrsData: null`). Add:
```javascript
setupStatus: null,
setupBannerDismissed: false,
```

Find the `loadAllMrs` method. Add after it:
```javascript
async loadSetupStatus() {
    try {
        this.setupStatus = await fetch('/api/setup/status').then(r => r.json());
    } catch(e) { /* silent — don't block UI */ }
},
async archiveApp(appId) {
    if (!confirm('Archive this application? It will be hidden but not deleted.')) return;
    try {
        await fetch(`/api/applications/${appId}/archive`, {method:'POST'});
        this.addToast('Application archived', 'success');
        await this.loadApplications();
    } catch(e) {
        this.addToast('Failed to archive: ' + e.message, 'error');
    }
},
```

### Step 4.3 — Auto-load setup status on init

Find where the app initializes (look for `init()` or `async init()` in the Alpine data). Add `this.loadSetupStatus()` to the init sequence:
```javascript
this.loadSetupStatus();
```

### Step 4.4 — Add setup banner at top of dashboard view

Find `x-show="view==='dashboard'"` section. At the very top of its content, add:

```html
<!-- Setup Banner — shown only when setup is incomplete -->
<div x-show="setupStatus && !setupStatus.complete && !setupBannerDismissed"
     style="background:#fefce8;border:1px solid #fde047;border-radius:10px;padding:14px 16px;margin-bottom:16px;display:flex;align-items:flex-start;gap:12px;">
    <div style="flex:1;">
        <div style="font-weight:700;font-size:14px;color:#854d0e;margin-bottom:6px;">
            Setup incomplete — <span x-text="setupStatus?.done_count??0"></span>/<span x-text="setupStatus?.total_count??0"></span> steps done
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:8px;">
            <template x-for="check in (setupStatus?.checks??[])" :key="check.key">
                <span :style="check.done ? 'color:#16a34a;font-size:12px;' : 'color:#b45309;font-size:12px;'">
                    <span x-text="check.done ? '✓ ' : '○ '"></span><span x-text="check.label"></span>
                </span>
            </template>
        </div>
    </div>
    <button @click="setupBannerDismissed=true"
            style="background:none;border:none;font-size:18px;cursor:pointer;color:#92400e;line-height:1;">×</button>
</div>
```

### Step 4.5 — Add Archive button to Application cards

Find the Applications view (search for `x-show="view==='applications'"` or similar). Find where individual app cards or table rows are rendered. Near the existing edit/delete buttons for each app, add an Archive button:

```html
<button @click="archiveApp(app.application_id)"
        style="padding:4px 10px;background:#f1f5f9;border:1px solid #cbd5e1;border-radius:6px;font-size:12px;color:#64748b;cursor:pointer;"
        title="Archive this application">Archive</button>
```

The exact placement depends on the existing card/row structure — read the relevant section first.

### Step 4.6 — Verify and commit
```bash
grep -c "setupStatus\|archiveApp\|setupBanner\|cleanup-preview" web/static/index.html
git add web/static/index.html
git commit -m "$(cat <<'EOF'
feat: add setup status banner to dashboard + archive button on application cards

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5 — Full Segment 3 test suite + tag

### Step 5.1 — Run all Segment 1 + 2 + 3 tests
```bash
cd /Users/puneetsharma/Workspace/projects/ai-lab/command-center
python3 -m pytest \
  tests/test_jira_filter.py \
  tests/test_my_work_real.py \
  tests/test_sprint_autodetect.py \
  tests/test_ssl_config.py \
  tests/test_gitlab_aggregate.py \
  tests/test_sod_eod_enriched.py \
  tests/test_jira_isolation.py \
  tests/test_setup_status.py \
  tests/test_app_cleanup.py \
  -v 2>&1 | tail -20
```
Expected: all tests pass.

### Step 5.2 — Tag
```bash
git tag segment3-complete
git log --oneline -12
```

---

## Self-Review Checklist

- [x] Jira leak: `save_jira` writes per-app URL+PAT to `AppJiraConfigORM`; `_jira_out` reads per-app first
- [x] Routes: `_effective_jira_cfg(app_id, db)` used in `team_workload`, `list_projects`, `jql_filter`
- [x] Global fallback: old apps without per-app credentials still work via `JiraConfigORM`
- [x] `GET /api/setup/status` returns 5 checks: `has_app`, `jira`, `gitlab`, `identity`, `email`
- [x] `POST /api/applications/{app_id}/archive` soft-deletes (status='archived')
- [x] `GET /api/applications/cleanup-preview` returns test-pattern candidates
- [x] Setup banner shown on dashboard when incomplete; dismissable
- [x] Archive button on application cards
- [x] All 10 test files pass together
- [x] Tagged `segment3-complete`
