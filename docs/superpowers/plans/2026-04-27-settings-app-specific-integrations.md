# Settings — App-Specific Integrations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor Jira/GitLab/Sprint settings from global singletons to per-application configs, with an app-selector dropdown in the Settings page and in each live view.

**Architecture:** Remove global config singleton reads/writes in jira_routes, gitlab_routes, sprint_routes; all live-data endpoints accept `?app_id=` and read from `App*ConfigORM`. The Settings page (`admin` view) replaces three flat integration cards with one Integrations card containing an app dropdown and Jira/GitLab/Sprint sections. Sprint Board, Team Workload, and Open MRs each get their own compact app selector that persists in localStorage.

**Tech Stack:** FastAPI + SQLAlchemy (SQLite), Alpine.js SPA (single `web/static/index.html`)

---

## File Map

| File | Change |
|------|--------|
| `web/routers/app_integration_routes.py` | Remove 3 activate endpoints |
| `web/routers/jira_routes.py` | Remove `/config` routes; `_get_cfg` uses `AppJiraConfigORM`; add `app_id` query param to `/test`, `/team`, `/refresh`, `/projects` |
| `web/routers/gitlab_routes.py` | Same pattern as jira_routes |
| `web/routers/sprint_routes.py` | Remove `/config` routes; `_get_cfg/_get_jira_cfg/_get_gl_cfg` use App* ORM; add `app_id` to all live routes |
| `web/static/index.html` | Multiple targeted edits — see tasks 5-11 |

---

### Task 1: Remove activate endpoints from app_integration_routes.py

**Files:**
- Modify: `web/routers/app_integration_routes.py`

- [ ] **Step 1: Open the file and locate the three activate functions**

Run:
```bash
grep -n "activate" web/routers/app_integration_routes.py
```
Expected output: lines 77, 146, 216 showing the three `@router.post(".../activate")` functions.

- [ ] **Step 2: Remove the Jira activate endpoint**

In `web/routers/app_integration_routes.py`, remove these lines (the entire function):

```python
@router.post("/jira/activate")
def activate_jira(app_id: str, db: Session = Depends(get_db)):
    """Copy this app's Jira config to the global config used by Sprint Board / Team Workload."""
    _get_app(app_id, db)
    src = db.query(AppJiraConfigORM).filter(AppJiraConfigORM.application_id == app_id).first()
    if not src:
        raise HTTPException(404, "no Jira config for this app")
    g = db.query(JiraConfigORM).filter(JiraConfigORM.id == 1).first()
    if not g:
        g = JiraConfigORM(id=1)
        db.add(g)
    g.base_url = src.base_url
    g.email = src.email
    if src.api_token:
        g.api_token = src.api_token
    g.project_keys = src.project_keys
    g.enabled = src.enabled
    db.commit()
    return {"status": "activated"}
```

- [ ] **Step 3: Remove the GitLab activate endpoint**

Remove these lines:

```python
@router.post("/gitlab/activate")
def activate_gitlab(app_id: str, db: Session = Depends(get_db)):
    """Copy this app's GitLab config to the global config used by Open MRs / Sprint Board."""
    _get_app(app_id, db)
    src = db.query(AppGitLabConfigORM).filter(AppGitLabConfigORM.application_id == app_id).first()
    if not src:
        raise HTTPException(404, "no GitLab config for this app")
    g = db.query(GitLabConfigORM).filter(GitLabConfigORM.id == 1).first()
    if not g:
        g = GitLabConfigORM(id=1)
        db.add(g)
    g.base_url = src.base_url
    if src.access_token:
        g.access_token = src.access_token
    g.project_ids = src.project_ids
    g.enabled = src.enabled
    db.commit()
    return {"status": "activated"}
```

- [ ] **Step 4: Remove the Sprint activate endpoint**

Remove these lines:

```python
@router.post("/sprint/activate")
def activate_sprint(app_id: str, db: Session = Depends(get_db)):
    """Copy this app's Sprint config to the global config used by Sprint Board / My Hub."""
    _get_app(app_id, db)
    src = db.query(AppSprintConfigORM).filter(AppSprintConfigORM.application_id == app_id).first()
    if not src:
        raise HTTPException(404, "no Sprint config for this app")
    g = db.query(SprintConfigORM).filter(SprintConfigORM.id == 1).first()
    if not g:
        g = SprintConfigORM(id=1)
        db.add(g)
    g.board_id = src.board_id
    g.sprint_id = src.sprint_id
    g.sprint_name = src.sprint_name
    g.my_jira_email = src.my_jira_email
    g.my_gitlab_username = src.my_gitlab_username
    db.commit()
    return {"status": "activated"}
```

- [ ] **Step 5: Remove unused imports (JiraConfigORM, GitLabConfigORM, SprintConfigORM) from the import line**

Change:
```python
from db.models import (
    ApplicationORM,
    AppJiraConfigORM, AppGitLabConfigORM, AppSprintConfigORM,
    JiraConfigORM, GitLabConfigORM, SprintConfigORM,
)
```
To:
```python
from db.models import (
    ApplicationORM,
    AppJiraConfigORM, AppGitLabConfigORM, AppSprintConfigORM,
)
```

- [ ] **Step 6: Verify the file has no activate references**

Run:
```bash
grep -n "activate\|JiraConfigORM\|GitLabConfigORM\|SprintConfigORM" web/routers/app_integration_routes.py
```
Expected: no output.

- [ ] **Step 7: Commit**

```bash
git add web/routers/app_integration_routes.py
git commit -m "feat: remove per-app activate endpoints — global singleton pattern dropped"
```

---

### Task 2: Refactor jira_routes.py — per-app config + app_id query param

**Files:**
- Modify: `web/routers/jira_routes.py`

- [ ] **Step 1: Update imports — swap JiraConfigORM for AppJiraConfigORM**

Change:
```python
from db.models import JiraConfigORM
```
To:
```python
from db.models import AppJiraConfigORM
```

- [ ] **Step 2: Replace `_get_cfg` with per-app version**

Replace:
```python
def _get_cfg(db: Session) -> JiraConfigORM:
    cfg = db.query(JiraConfigORM).filter(JiraConfigORM.id == 1).first()
    if not cfg:
        cfg = JiraConfigORM(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg
```
With:
```python
def _get_cfg(app_id: str, db: Session) -> AppJiraConfigORM:
    cfg = db.query(AppJiraConfigORM).filter(AppJiraConfigORM.application_id == app_id).first()
    if not cfg:
        raise HTTPException(404, f"No Jira config found for application '{app_id}' — configure it in Settings first")
    return cfg
```

- [ ] **Step 3: Remove the GET /config and POST /config endpoints**

Remove these two functions entirely:
```python
@router.get("/config")
def get_config(db: Session = Depends(_db)):
    cfg = _get_cfg(db)
    return {
        "base_url":     cfg.base_url or "",
        "email":        cfg.email or "",
        "api_token":    "••••••••" if cfg.api_token else "",
        "project_keys": cfg.project_keys or "[]",
        "enabled":      cfg.enabled,
        "last_synced":  cfg.last_synced.isoformat() if cfg.last_synced else None,
    }


@router.post("/config")
def save_config(body: JiraConfigIn, db: Session = Depends(_db)):
    cfg = _get_cfg(db)
    if body.base_url is not None:
        cfg.base_url = body.base_url.rstrip("/")
    if body.email is not None:
        cfg.email = body.email
    if body.api_token and body.api_token != "••••••••":
        cfg.api_token = body.api_token
    if body.project_keys is not None:
        # Accept comma-separated string OR JSON array
        raw = body.project_keys.strip()
        if not raw.startswith("["):
            keys = [k.strip().upper() for k in raw.split(",") if k.strip()]
            cfg.project_keys = json.dumps(keys)
        else:
            cfg.project_keys = raw
    cfg.enabled = body.enabled
    db.commit()
    _cache_bust()
    return {"ok": True}
```

Also remove the now-unused `JiraConfigIn` schema:
```python
class JiraConfigIn(BaseModel):
    base_url:     Optional[str] = ""
    email:        Optional[str] = ""
    api_token:    Optional[str] = ""
    project_keys: Optional[str] = "[]"  # raw JSON string
    enabled:      Optional[bool] = False
```

- [ ] **Step 4: Update `/test` to accept app_id**

Add `from fastapi import Query` to the import line (it's already there via `APIRouter, Depends, HTTPException`; add `Query`):

Change:
```python
from fastapi import APIRouter, Depends, HTTPException
```
To:
```python
from fastapi import APIRouter, Depends, HTTPException, Query
```

Replace the `/test` endpoint:
```python
@router.post("/test")
def test_connection(db: Session = Depends(_db)):
    cfg = _get_cfg(db)
    if not cfg.base_url or not cfg.email or not cfg.api_token:
        raise HTTPException(400, "Jira not configured — fill in URL, email, and API token first")
    data = _jira_get(cfg, "myself")
    return {
        "ok": True,
        "display_name": data.get("displayName", ""),
        "account_id":   data.get("accountId", ""),
        "message": f"Connected as {data.get('displayName', cfg.email)}",
    }
```
With:
```python
@router.post("/test")
def test_connection(app_id: str = Query(...), db: Session = Depends(_db)):
    cfg = _get_cfg(app_id, db)
    if not cfg.base_url or not cfg.email or not cfg.api_token:
        raise HTTPException(400, "Jira not configured — fill in URL, email, and API token first")
    data = _jira_get(cfg, "myself")
    return {
        "ok": True,
        "display_name": data.get("displayName", ""),
        "account_id":   data.get("accountId", ""),
        "message": f"Connected as {data.get('displayName', cfg.email)}",
    }
```

- [ ] **Step 5: Update `/projects` to accept app_id**

Replace:
```python
@router.get("/projects")
def list_projects(db: Session = Depends(_db)):
    cfg = _get_cfg(db)
    if not cfg.enabled or not cfg.api_token:
        raise HTTPException(400, "Jira integration is not enabled")
    cached = _cache_get("projects")
    if cached:
        return cached
    data = _jira_get(cfg, "project/search", {"maxResults": 50, "orderBy": "name"})
    projects = [
        {"key": p["key"], "name": p["name"], "type": p.get("projectTypeKey", "")}
        for p in data.get("values", [])
    ]
    _cache_set("projects", projects)
    return projects
```
With:
```python
@router.get("/projects")
def list_projects(app_id: str = Query(...), db: Session = Depends(_db)):
    cfg = _get_cfg(app_id, db)
    if not cfg.enabled or not cfg.api_token:
        raise HTTPException(400, "Jira integration is not enabled")
    cache_key = f"projects_{app_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
    data = _jira_get(cfg, "project/search", {"maxResults": 50, "orderBy": "name"})
    projects = [
        {"key": p["key"], "name": p["name"], "type": p.get("projectTypeKey", "")}
        for p in data.get("values", [])
    ]
    _cache_set(cache_key, projects)
    return projects
```

- [ ] **Step 6: Update `/team` to accept app_id**

Replace:
```python
@router.get("/team")
def team_workload(db: Session = Depends(_db)):
    """Return team workload: one entry per assignee with their open issues."""
    cfg = _get_cfg(db)
    if not cfg.enabled or not cfg.api_token:
        raise HTTPException(400, "Jira integration is not enabled")

    cached = _cache_get("team")
    if cached:
        return cached
```
With:
```python
@router.get("/team")
def team_workload(app_id: str = Query(...), db: Session = Depends(_db)):
    """Return team workload: one entry per assignee with their open issues."""
    cfg = _get_cfg(app_id, db)
    if not cfg.enabled or not cfg.api_token:
        raise HTTPException(400, "Jira integration is not enabled")

    cache_key = f"team_{app_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
```

And in the same function, replace:
```python
    _cache_set("team", result)

    # Update last_synced timestamp
    cfg.last_synced = datetime.utcnow()
    db.commit()

    return result
```
With:
```python
    _cache_set(cache_key, result)

    cfg.last_synced = datetime.utcnow()
    db.commit()

    return result
```

- [ ] **Step 7: Update `/refresh` to accept app_id**

Replace:
```python
@router.post("/refresh")
def refresh_cache(db: Session = Depends(_db)):
    _cache_bust()
    return {"ok": True, "message": "Cache cleared — next fetch will pull live data"}
```
With:
```python
@router.post("/refresh")
def refresh_cache(app_id: str = Query(...)):
    _cache.pop(f"team_{app_id}", None)
    _cache.pop(f"projects_{app_id}", None)
    return {"ok": True, "message": "Cache cleared — next fetch will pull live data"}
```

- [ ] **Step 8: Smoke-test the file parses cleanly**

Run:
```bash
python3 -c "import sys; sys.path.insert(0,'.');from web.routers.jira_routes import router; print('OK')"
```
Expected: `OK`

- [ ] **Step 9: Commit**

```bash
git add web/routers/jira_routes.py
git commit -m "feat: jira_routes — per-app config via app_id query param, drop global singleton"
```

---

### Task 3: Refactor gitlab_routes.py — per-app config + app_id query param

**Files:**
- Modify: `web/routers/gitlab_routes.py`

- [ ] **Step 1: Update import**

Change:
```python
from db.models import GitLabConfigORM
```
To:
```python
from db.models import AppGitLabConfigORM
```

- [ ] **Step 2: Add Query to FastAPI imports**

Change:
```python
from fastapi import APIRouter, Depends, HTTPException
```
To:
```python
from fastapi import APIRouter, Depends, HTTPException, Query
```

- [ ] **Step 3: Replace `_get_cfg`**

Replace:
```python
def _get_cfg(db: Session) -> GitLabConfigORM:
    cfg = db.query(GitLabConfigORM).filter(GitLabConfigORM.id == 1).first()
    if not cfg:
        cfg = GitLabConfigORM(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg
```
With:
```python
def _get_cfg(app_id: str, db: Session) -> AppGitLabConfigORM:
    cfg = db.query(AppGitLabConfigORM).filter(AppGitLabConfigORM.application_id == app_id).first()
    if not cfg:
        raise HTTPException(404, f"No GitLab config found for application '{app_id}' — configure it in Settings first")
    return cfg
```

- [ ] **Step 4: Remove GET /config and POST /config endpoints and GitLabConfigIn schema**

Remove:
```python
class GitLabConfigIn(BaseModel):
    base_url:     Optional[str] = "https://gitlab.com"
    access_token: Optional[str] = ""
    project_ids:  Optional[str] = "[]"   # JSON array of project IDs or "namespace/path"
    enabled:      Optional[bool] = False


@router.get("/config")
def get_config(db: Session = Depends(_db)):
    cfg = _get_cfg(db)
    return {
        "base_url":     cfg.base_url or "https://gitlab.com",
        "access_token": "••••••••" if cfg.access_token else "",
        "project_ids":  cfg.project_ids or "[]",
        "enabled":      cfg.enabled,
        "last_synced":  cfg.last_synced.isoformat() if cfg.last_synced else None,
    }


@router.post("/config")
def save_config(body: GitLabConfigIn, db: Session = Depends(_db)):
    cfg = _get_cfg(db)
    if body.base_url is not None:
        cfg.base_url = body.base_url.rstrip("/")
    if body.access_token and body.access_token != "••••••••":
        cfg.access_token = body.access_token
    if body.project_ids is not None:
        raw = body.project_ids.strip()
        if not raw.startswith("["):
            # Accept newline/comma-separated project paths
            items = [p.strip() for p in raw.replace("\n", ",").split(",") if p.strip()]
            cfg.project_ids = json.dumps(items)
        else:
            cfg.project_ids = raw
    cfg.enabled = body.enabled
    db.commit()
    _cache_bust()
    return {"ok": True}
```

- [ ] **Step 5: Update `/test` to accept app_id**

Replace:
```python
@router.post("/test")
def test_connection(db: Session = Depends(_db)):
    cfg = _get_cfg(db)
    if not cfg.access_token:
        raise HTTPException(400, "GitLab not configured — enter an access token first")
    data, _ = _gl_get(cfg, "user")
    return {
        "ok": True,
        "username":     data.get("username", ""),
        "display_name": data.get("name", ""),
        "message": f"Connected as {data.get('name', data.get('username', ''))}",
    }
```
With:
```python
@router.post("/test")
def test_connection(app_id: str = Query(...), db: Session = Depends(_db)):
    cfg = _get_cfg(app_id, db)
    if not cfg.access_token:
        raise HTTPException(400, "GitLab not configured — enter an access token first")
    data, _ = _gl_get(cfg, "user")
    return {
        "ok": True,
        "username":     data.get("username", ""),
        "display_name": data.get("name", ""),
        "message": f"Connected as {data.get('name', data.get('username', ''))}",
    }
```

- [ ] **Step 6: Update `/projects` to accept app_id**

Replace:
```python
@router.get("/projects")
def list_projects(db: Session = Depends(_db)):
    """Return projects from the configured list (resolves path-based IDs)."""
    cfg = _get_cfg(db)
    if not cfg.enabled or not cfg.access_token:
        raise HTTPException(400, "GitLab integration is not enabled")
    cached = _cache_get("gl_projects")
    if cached:
        return cached
```
With:
```python
@router.get("/projects")
def list_projects(app_id: str = Query(...), db: Session = Depends(_db)):
    """Return projects from the configured list (resolves path-based IDs)."""
    cfg = _get_cfg(app_id, db)
    if not cfg.enabled or not cfg.access_token:
        raise HTTPException(400, "GitLab integration is not enabled")
    cache_key = f"gl_projects_{app_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
```

And update the two `_cache_set` calls in this function: change `_cache_set("gl_projects", projects)` to `_cache_set(cache_key, projects)`.

- [ ] **Step 7: Update `/mrs` to accept app_id**

Replace:
```python
@router.get("/mrs")
def open_mrs(db: Session = Depends(_db)):
    """Return all open MRs across configured projects, grouped by author."""
    cfg = _get_cfg(db)
    if not cfg.enabled or not cfg.access_token:
        raise HTTPException(400, "GitLab integration is not enabled")

    cached = _cache_get("gl_mrs")
    if cached:
        return cached
```
With:
```python
@router.get("/mrs")
def open_mrs(app_id: str = Query(...), db: Session = Depends(_db)):
    """Return all open MRs across configured projects, grouped by author."""
    cfg = _get_cfg(app_id, db)
    if not cfg.enabled or not cfg.access_token:
        raise HTTPException(400, "GitLab integration is not enabled")

    cache_key = f"gl_mrs_{app_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
```

And update `_cache_set("gl_mrs", result)` to `_cache_set(cache_key, result)`.

- [ ] **Step 8: Update `/refresh` to accept app_id**

Replace:
```python
@router.post("/refresh")
def refresh_cache(db: Session = Depends(_db)):
    _cache_bust()
    return {"ok": True}
```
With:
```python
@router.post("/refresh")
def refresh_cache(app_id: str = Query(...)):
    _cache.pop(f"gl_mrs_{app_id}", None)
    _cache.pop(f"gl_projects_{app_id}", None)
    return {"ok": True}
```

- [ ] **Step 9: Smoke-test**

```bash
python3 -c "import sys; sys.path.insert(0,'.');from web.routers.gitlab_routes import router; print('OK')"
```
Expected: `OK`

- [ ] **Step 10: Commit**

```bash
git add web/routers/gitlab_routes.py
git commit -m "feat: gitlab_routes — per-app config via app_id query param, drop global singleton"
```

---

### Task 4: Refactor sprint_routes.py — per-app config + app_id query param

**Files:**
- Modify: `web/routers/sprint_routes.py`

- [ ] **Step 1: Update imports**

Change:
```python
from db.models import SprintConfigORM, JiraConfigORM, GitLabConfigORM
```
To:
```python
from db.models import AppSprintConfigORM, AppJiraConfigORM, AppGitLabConfigORM
```

- [ ] **Step 2: Replace the three `_get_*` helpers**

Replace:
```python
def _get_cfg(db: Session) -> SprintConfigORM:
    cfg = db.query(SprintConfigORM).filter(SprintConfigORM.id == 1).first()
    if not cfg:
        cfg = SprintConfigORM(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def _get_jira_cfg(db: Session) -> JiraConfigORM:
    cfg = db.query(JiraConfigORM).filter(JiraConfigORM.id == 1).first()
    if not cfg:
        cfg = JiraConfigORM(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def _get_gl_cfg(db: Session) -> GitLabConfigORM:
    cfg = db.query(GitLabConfigORM).filter(GitLabConfigORM.id == 1).first()
    if not cfg:
        cfg = GitLabConfigORM(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg
```
With:
```python
def _get_cfg(app_id: str, db: Session) -> AppSprintConfigORM:
    cfg = db.query(AppSprintConfigORM).filter(AppSprintConfigORM.application_id == app_id).first()
    if not cfg:
        raise HTTPException(404, f"No Sprint config for application '{app_id}'")
    return cfg


def _get_jira_cfg(app_id: str, db: Session) -> AppJiraConfigORM:
    cfg = db.query(AppJiraConfigORM).filter(AppJiraConfigORM.application_id == app_id).first()
    if not cfg:
        raise HTTPException(404, f"No Jira config for application '{app_id}' — configure it in Settings first")
    return cfg


def _get_gl_cfg(app_id: str, db: Session) -> AppGitLabConfigORM:
    cfg = db.query(AppGitLabConfigORM).filter(AppGitLabConfigORM.application_id == app_id).first()
    if not cfg:
        raise HTTPException(404, f"No GitLab config for application '{app_id}' — configure it in Settings first")
    return cfg
```

- [ ] **Step 3: Remove GET /config and POST /config endpoints and SprintConfigIn schema**

Remove:
```python
class SprintConfigIn(BaseModel):
    board_id:           Optional[str] = ""
    sprint_id:          Optional[str] = ""
    sprint_name:        Optional[str] = ""
    my_jira_email:      Optional[str] = ""
    my_gitlab_username: Optional[str] = ""


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("/config")
def get_config(db: Session = Depends(_db)):
    cfg = _get_cfg(db)
    return {
        "board_id":           cfg.board_id or "",
        "sprint_id":          cfg.sprint_id or "",
        "sprint_name":        cfg.sprint_name or "",
        "my_jira_email":      cfg.my_jira_email or "",
        "my_gitlab_username": cfg.my_gitlab_username or "",
    }


@router.post("/config")
def save_config(body: SprintConfigIn, db: Session = Depends(_db)):
    cfg = _get_cfg(db)
    if body.board_id is not None:
        cfg.board_id = body.board_id
    if body.sprint_id is not None:
        cfg.sprint_id = body.sprint_id
    if body.sprint_name is not None:
        cfg.sprint_name = body.sprint_name
    if body.my_jira_email is not None:
        cfg.my_jira_email = body.my_jira_email
    if body.my_gitlab_username is not None:
        cfg.my_gitlab_username = body.my_gitlab_username
    db.commit()
    _cache_bust()
    return {"ok": True}
```

Keep the `# ── Endpoints ──` comment line; just remove the schema and the two route functions.

- [ ] **Step 4: Update `/boards` to accept app_id**

Replace:
```python
@router.get("/boards")
def list_boards(db: Session = Depends(_db)):
    """List Jira boards (Software boards that have sprints)."""
    jira_cfg = _get_jira_cfg(db)
    if not jira_cfg.enabled or not jira_cfg.api_token:
        raise HTTPException(400, "Jira integration is not enabled")

    cached = _cache_get("boards")
    if cached:
        return cached

    data = _jira_get(jira_cfg, "rest/agile/1.0/board", {"type": "scrum", "maxResults": 50})
    boards = [
        {"id": str(b["id"]), "name": b.get("name", ""), "type": b.get("type", "")}
        for b in data.get("values", [])
    ]
    _cache_set("boards", boards)
    return boards
```
With:
```python
@router.get("/boards")
def list_boards(app_id: str = Query(...), db: Session = Depends(_db)):
    """List Jira boards (Software boards that have sprints)."""
    jira_cfg = _get_jira_cfg(app_id, db)
    if not jira_cfg.enabled or not jira_cfg.api_token:
        raise HTTPException(400, "Jira integration is not enabled")

    cache_key = f"boards_{app_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    data = _jira_get(jira_cfg, "rest/agile/1.0/board", {"type": "scrum", "maxResults": 50})
    boards = [
        {"id": str(b["id"]), "name": b.get("name", ""), "type": b.get("type", "")}
        for b in data.get("values", [])
    ]
    _cache_set(cache_key, boards)
    return boards
```

- [ ] **Step 5: Update `/sprints` to accept app_id**

The current signature is `def list_sprints(board_id: str = Query(...), db: Session = Depends(_db))`.

Replace:
```python
@router.get("/sprints")
def list_sprints(board_id: str = Query(...), db: Session = Depends(_db)):
    """List sprints for a Jira board."""
    jira_cfg = _get_jira_cfg(db)
    if not jira_cfg.enabled or not jira_cfg.api_token:
        raise HTTPException(400, "Jira integration is not enabled")

    cache_key = f"sprints_{board_id}"
```
With:
```python
@router.get("/sprints")
def list_sprints(app_id: str = Query(...), board_id: str = Query(...), db: Session = Depends(_db)):
    """List sprints for a Jira board."""
    jira_cfg = _get_jira_cfg(app_id, db)
    if not jira_cfg.enabled or not jira_cfg.api_token:
        raise HTTPException(400, "Jira integration is not enabled")

    cache_key = f"sprints_{app_id}_{board_id}"
```

- [ ] **Step 6: Update `/board` to accept app_id**

Replace the function signature and all three `_get_*` calls:
```python
@router.get("/board")
def sprint_board(db: Session = Depends(_db)):
    """Fetch sprint items with correlated GitLab MRs."""
    cached = _cache_get("board")
    if cached:
        return cached

    cfg      = _get_cfg(db)
    jira_cfg = _get_jira_cfg(db)
    gl_cfg   = _get_gl_cfg(db)
```
With:
```python
@router.get("/board")
def sprint_board(app_id: str = Query(...), db: Session = Depends(_db)):
    """Fetch sprint items with correlated GitLab MRs."""
    cache_key = f"board_{app_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    cfg      = _get_cfg(app_id, db)
    jira_cfg = _get_jira_cfg(app_id, db)
    gl_cfg   = _get_gl_cfg(app_id, db)
```

Near the bottom of `sprint_board`, find `_cache_set("board", result)` and replace with `_cache_set(cache_key, result)`.

- [ ] **Step 7: Update `/refresh` to accept app_id**

Find and replace the refresh endpoint:
```python
@router.post("/refresh")
def refresh_cache(db: Session = Depends(_db)):
    _cache_bust()
    return {"ok": True}
```
With:
```python
@router.post("/refresh")
def refresh_cache(app_id: str = Query(...)):
    for k in list(_cache.keys()):
        if k.endswith(f"_{app_id}"):
            del _cache[k]
    return {"ok": True}
```

- [ ] **Step 8: Smoke-test**

```bash
python3 -c "import sys; sys.path.insert(0,'.');from web.routers.sprint_routes import router; print('OK')"
```
Expected: `OK`

- [ ] **Step 9: Commit**

```bash
git add web/routers/sprint_routes.py
git commit -m "feat: sprint_routes — per-app config via app_id query param, drop global singleton"
```

---

### Task 5: Frontend — Remove global config load from startup init and fix nav badges

**Files:**
- Modify: `web/static/index.html`

- [ ] **Step 1: Remove loadJiraConfig and loadGitLabConfig from the startup loadAll chain**

In `index.html` around line 4355, find:
```javascript
        this.loadSummaries(), this.loadEstimations(), this.loadEmailConfig(), this.loadJiraConfig(), this.loadGitLabConfig(), this.loadOutlookConfig(),
```
Replace with:
```javascript
        this.loadSummaries(), this.loadEstimations(), this.loadEmailConfig(), this.loadOutlookConfig(),
```

- [ ] **Step 2: Update the nav() function — remove global-config-dependent auto-loads**

Find:
```javascript
      if(id==='jira-team' && this.jiraCfg.enabled && !this.jiraData.team.length) this.loadJiraTeam();
      if(id==='gitlab-mrs' && this.gitlabCfg.enabled && !this.glData.all_mrs.length) this.loadGitLabMRs();
      if(id==='my-hub' && !this.myHubData) this.loadMyHub();
      if(id==='sprint-board') { this.loadSprintConfig(); if(this.sprintCfg.sprint_id && !this.sprintData) this.loadSprintBoard(); }
      if(id==='admin') { this.loadEmailConfig(); this.loadJiraConfig(); this.loadGitLabConfig(); this.loadOutlookConfig(); this.loadSprintConfig(); }
```
Replace with:
```javascript
      if(id==='jira-team' && this.jiraAppId && !this.jiraData.team.length) this.onJiraAppChange();
      if(id==='gitlab-mrs' && this.gitlabAppId && !this.glData.all_mrs.length) this.onGitLabAppChange();
      if(id==='my-hub' && !this.myHubData) this.loadMyHub();
      if(id==='sprint-board' && this.sprintAppId && !this.sprintData) this.onSprintAppChange();
      if(id==='admin') {
        this.loadEmailConfig(); this.loadOutlookConfig();
        if (!this.settingsApp && this.applications.length) this.settingsApp = this.applications[0].application_id;
        this.loadSettingsAppConfig();
      }
```

- [ ] **Step 3: Remove the JIRA and GL nav badges; update the Sprint LIVE badge**

Find:
```html
      <div @click="nav('jira-team')"       :class="navCls('jira-team')">
        <div class="nav-icon">👥</div><span style="flex:1">Team Workload</span>
        <span x-show="jiraCfg.enabled" style="background:#0052cc;color:#fff;font-size:9px;font-weight:700;border-radius:4px;padding:1px 5px;letter-spacing:.04em;">JIRA</span>
      </div>
```
Replace with:
```html
      <div @click="nav('jira-team')"       :class="navCls('jira-team')">
        <div class="nav-icon">👥</div><span style="flex:1">Team Workload</span>
      </div>
```

Find:
```html
      <div @click="nav('sprint-board')" :class="navCls('sprint-board')">
        <div class="nav-icon">🏃</div><span style="flex:1">Sprint Board</span>
        <span x-show="sprintCfg.sprint_id" style="background:#7c3aed;color:#fff;font-size:9px;font-weight:700;border-radius:4px;padding:1px 5px;letter-spacing:.04em;">LIVE</span>
      </div>
      <div @click="nav('gitlab-mrs')" :class="navCls('gitlab-mrs')">
        <div class="nav-icon">🦊</div><span style="flex:1">Open MRs</span>
        <span x-show="gitlabCfg.enabled" style="background:#fc6d26;color:#fff;font-size:9px;font-weight:700;border-radius:4px;padding:1px 5px;letter-spacing:.04em;">GL</span>
      </div>
```
Replace with:
```html
      <div @click="nav('sprint-board')" :class="navCls('sprint-board')">
        <div class="nav-icon">🏃</div><span style="flex:1">Sprint Board</span>
        <span x-show="sprintAppId && sprintCfg.sprint_id" style="background:#7c3aed;color:#fff;font-size:9px;font-weight:700;border-radius:4px;padding:1px 5px;letter-spacing:.04em;">LIVE</span>
      </div>
      <div @click="nav('gitlab-mrs')" :class="navCls('gitlab-mrs')">
        <div class="nav-icon">🦊</div><span style="flex:1">Open MRs</span>
      </div>
```

- [ ] **Step 4: Add new state variables for settings page and live view app selectors**

Find the Alpine.js `data()` section. Locate:
```javascript
    jiraCfg: { base_url:'', email:'', api_token:'', project_keys:'[]', project_keys_raw:'', enabled:false, last_synced:null },
```
After this line, add:
```javascript
    // Settings page per-app integration state
    settingsApp: '',
    settingsAppCfg: {
      jira: { base_url:'', email:'', api_token:'', project_keys_raw:'', enabled:false },
      gitlab: { base_url:'https://gitlab.com', access_token:'', project_ids_raw:'', enabled:false },
      sprint: { board_id:'', sprint_id:'', sprint_name:'', my_jira_email:'', my_gitlab_username:'' },
    },
    settingsJiraTestLoading: false, settingsJiraMsg:'', settingsJiraOk:false,
    settingsGlTestLoading: false, settingsGlMsg:'', settingsGlOk:false,
    settingsSprintMsg:'', settingsSprintOk:false,
    // Live view per-view app selectors (persisted in localStorage)
    jiraAppId: localStorage.getItem('execos_jira_app')||'',
    gitlabAppId: localStorage.getItem('execos_gitlab_app')||'',
    sprintAppId: localStorage.getItem('execos_sprint_app')||'',
```

- [ ] **Step 5: Commit**

```bash
git add web/static/index.html
git commit -m "feat: remove global jira/gitlab config loads from startup; add per-view app selector state"
```

---

### Task 6: Frontend — Settings page HTML — replace global integration cards with app-selector UI

**Files:**
- Modify: `web/static/index.html`

- [ ] **Step 1: Remove the existing GitLab Integration card (lines ~3634-3683)**

Find and remove the entire GitLab card:
```html
          <!-- GitLab Integration -->
          <div class="card" style="margin-bottom:20px;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:18px;">
              <div style="width:36px;height:36px;border-radius:10px;background:#fff3ee;display:flex;align-items:center;justify-content:center;font-size:18px;">🦊</div>
              <div>
                <div style="font-size:15px;font-weight:800;color:var(--text-1);">GitLab — Open MRs</div>
                <div style="font-size:12px;color:var(--text-3);">Track open merge requests and team contributions across projects</div>
              </div>
              <div style="margin-left:auto;">
                <div :style="'padding:4px 12px;border-radius:12px;font-size:11px;font-weight:700;'+(gitlabCfg.enabled?'background:#fff3ee;color:#c2410c;border:1.5px solid #fed7aa;':'background:var(--bg);color:var(--text-3);border:1px solid var(--border);')"
                  x-text="gitlabCfg.enabled?'Connected':'Disabled'"></div>
              </div>
            </div>
```

Replace this entire block (everything from `<!-- GitLab Integration -->` through to the closing `</div>` of the card, which ends just before `<!-- Jira Integration -->`) with nothing — it will be replaced by the new Integrations card in the next step.

To avoid ambiguity, identify the full range: the GitLab card starts at `<!-- GitLab Integration -->` and ends with:
```html
            <div x-show="glTestMsg" style="margin-top:10px;padding:10px 14px;border-radius:9px;"
              :style="glTestOk?'background:#f0fdf4;border:1px solid #bbf7d0;color:#15803d;font-size:12.5px;font-weight:600;':'background:#fff1f2;border:1px solid #fecdd3;color:#be123c;font-size:12.5px;font-weight:600;'"
              x-text="glTestMsg"></div>
          </div>
```

Also remove the Jira Integration card that follows, which starts with `<!-- Jira Integration -->` and ends with:
```html
            <div x-show="jiraCfg.last_synced" style="margin-top:10px;font-size:11.5px;color:var(--text-3);">
              Last synced: <span x-text="jiraCfg.last_synced"></span>
            </div>
          </div>
```

Also remove the Sprint / My Hub Config card that follows, which starts with `<!-- Sprint / My Hub Config -->` and ends with:
```html
            <div x-show="sprintCfg.sprint_id" style="margin-top:10px;font-size:11.5px;color:var(--text-3);">
              Active sprint: <span style="color:var(--accent);font-weight:600;" x-text="sprintCfg.sprint_name||sprintCfg.sprint_id"></span>
            </div>
          </div>
```

The entire removal is from the `<!-- GitLab Integration -->` comment line through the closing `</div>` of the Sprint card.

- [ ] **Step 2: Insert the new Integrations card in place of the removed cards**

After the Email Briefings card closing `</div>` (which ends with `</div>` after the email settings section), add:

```html
          <!-- Integrations — per-application -->
          <div class="card" style="margin-bottom:20px;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:18px;">
              <div style="width:36px;height:36px;border-radius:10px;background:#f5f3ff;display:flex;align-items:center;justify-content:center;font-size:18px;">🔌</div>
              <div>
                <div style="font-size:15px;font-weight:800;color:var(--text-1);">Integrations</div>
                <div style="font-size:12px;color:var(--text-3);">Configure per-application Jira, GitLab, and Sprint settings</div>
              </div>
            </div>

            <!-- App selector -->
            <div style="margin-bottom:20px;">
              <label style="font-size:11.5px;font-weight:700;color:var(--text-2);display:block;margin-bottom:6px;">Application</label>
              <select x-model="settingsApp" @change="loadSettingsAppConfig()" style="width:100%;padding:8px 12px;border-radius:9px;border:1px solid var(--border);font-size:13px;color:var(--text-1);background:var(--bg);box-sizing:border-box;">
                <option value="">— select an application —</option>
                <template x-for="app in applications" :key="app.application_id">
                  <option :value="app.application_id" x-text="app.name"></option>
                </template>
              </select>
              <div x-show="!applications.length" style="font-size:12px;color:var(--text-3);margin-top:6px;">No applications yet — create one in the Applications view first.</div>
            </div>

            <div x-show="settingsApp">

              <!-- Jira section -->
              <div style="border-top:1px solid var(--border);padding-top:18px;margin-bottom:18px;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">
                  <div style="width:28px;height:28px;border-radius:8px;background:#e8f0ff;display:flex;align-items:center;justify-content:center;font-size:14px;">🔗</div>
                  <div style="font-size:14px;font-weight:700;color:var(--text-1);">Jira</div>
                  <div style="margin-left:auto;padding:3px 10px;border-radius:10px;font-size:11px;font-weight:700;"
                    :style="settingsAppCfg.jira.enabled?'background:#eff6ff;color:#2563eb;border:1.5px solid #bfdbfe;':'background:var(--bg);color:var(--text-3);border:1px solid var(--border);'"
                    x-text="settingsAppCfg.jira.enabled?'Connected':'Disabled'"></div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                  <div style="grid-column:1/-1;">
                    <label style="font-size:11.5px;font-weight:700;color:var(--text-2);display:block;margin-bottom:5px;">Jira Base URL</label>
                    <input x-model="settingsAppCfg.jira.base_url" placeholder="https://yourcompany.atlassian.net"
                      style="width:100%;padding:8px 12px;border-radius:9px;border:1px solid var(--border);font-size:13px;color:var(--text-1);box-sizing:border-box;">
                  </div>
                  <div>
                    <label style="font-size:11.5px;font-weight:700;color:var(--text-2);display:block;margin-bottom:5px;">Email</label>
                    <input x-model="settingsAppCfg.jira.email" type="email" placeholder="you@company.com"
                      style="width:100%;padding:8px 12px;border-radius:9px;border:1px solid var(--border);font-size:13px;color:var(--text-1);box-sizing:border-box;">
                  </div>
                  <div>
                    <label style="font-size:11.5px;font-weight:700;color:var(--text-2);display:block;margin-bottom:5px;">API Token
                      <a href="https://id.atlassian.com/manage-profile/security/api-tokens" target="_blank" style="color:#6366f1;font-weight:400;margin-left:4px;">Get token ↗</a>
                    </label>
                    <input x-model="settingsAppCfg.jira.api_token" type="password" placeholder="Leave blank to keep existing"
                      style="width:100%;padding:8px 12px;border-radius:9px;border:1px solid var(--border);font-size:13px;color:var(--text-1);box-sizing:border-box;">
                  </div>
                  <div style="grid-column:1/-1;">
                    <label style="font-size:11.5px;font-weight:700;color:var(--text-2);display:block;margin-bottom:5px;">Project Keys <span style="font-weight:400;color:var(--text-3);">— one per line (leave blank for all)</span></label>
                    <textarea x-model="settingsAppCfg.jira.project_keys_raw" rows="3" placeholder="ENG&#10;OPS&#10;MOBILE"
                      style="width:100%;padding:8px 12px;border-radius:9px;border:1px solid var(--border);font-size:13px;color:var(--text-1);box-sizing:border-box;resize:vertical;font-family:monospace;"></textarea>
                  </div>
                </div>
                <div style="display:flex;align-items:center;gap:10px;margin-top:12px;flex-wrap:wrap;">
                  <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                    <input type="checkbox" x-model="settingsAppCfg.jira.enabled" style="width:16px;height:16px;accent-color:#0052cc;">
                    <span style="font-size:13px;font-weight:600;color:var(--text-1);">Enable Jira integration</span>
                  </label>
                  <div style="flex:1;"></div>
                  <button @click="testSettingsJira()" :disabled="settingsJiraTestLoading"
                    style="padding:8px 16px;border-radius:9px;background:#eff6ff;border:1.5px solid #bfdbfe;color:#2563eb;font-size:12.5px;font-weight:700;cursor:pointer;">
                    <span x-show="!settingsJiraTestLoading">⚡ Test</span>
                    <span x-show="settingsJiraTestLoading">Testing…</span>
                  </button>
                  <button @click="saveSettingsJira()" class="btn-primary" style="font-size:13px;">Save Jira</button>
                </div>
                <div x-show="settingsJiraMsg" style="margin-top:8px;padding:8px 12px;border-radius:9px;font-size:12.5px;font-weight:600;"
                  :style="settingsJiraOk?'background:#f0fdf4;border:1px solid #bbf7d0;color:#15803d;':'background:#fff1f2;border:1px solid #fecdd3;color:#be123c;'"
                  x-text="settingsJiraMsg"></div>
              </div>

              <!-- GitLab section -->
              <div style="border-top:1px solid var(--border);padding-top:18px;margin-bottom:18px;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">
                  <div style="width:28px;height:28px;border-radius:8px;background:#fff3ee;display:flex;align-items:center;justify-content:center;font-size:14px;">🦊</div>
                  <div style="font-size:14px;font-weight:700;color:var(--text-1);">GitLab</div>
                  <div style="margin-left:auto;padding:3px 10px;border-radius:10px;font-size:11px;font-weight:700;"
                    :style="settingsAppCfg.gitlab.enabled?'background:#fff3ee;color:#c2410c;border:1.5px solid #fed7aa;':'background:var(--bg);color:var(--text-3);border:1px solid var(--border);'"
                    x-text="settingsAppCfg.gitlab.enabled?'Connected':'Disabled'"></div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                  <div style="grid-column:1/-1;">
                    <label style="font-size:11.5px;font-weight:700;color:var(--text-2);display:block;margin-bottom:5px;">GitLab Base URL <span style="font-weight:400;color:var(--text-3);">(self-hosted or gitlab.com)</span></label>
                    <input x-model="settingsAppCfg.gitlab.base_url" placeholder="https://gitlab.com"
                      style="width:100%;padding:8px 12px;border-radius:9px;border:1px solid var(--border);font-size:13px;color:var(--text-1);box-sizing:border-box;">
                  </div>
                  <div style="grid-column:1/-1;">
                    <label style="font-size:11.5px;font-weight:700;color:var(--text-2);display:block;margin-bottom:5px;">Personal Access Token
                      <a href="https://gitlab.com/-/user_settings/personal_access_tokens" target="_blank" style="color:#fc6d26;font-weight:400;margin-left:4px;">Get token ↗</a>
                      <span style="font-weight:400;color:var(--text-3);margin-left:4px;">— requires <code>api</code> scope</span>
                    </label>
                    <input x-model="settingsAppCfg.gitlab.access_token" type="password" placeholder="Leave blank to keep existing"
                      style="width:100%;padding:8px 12px;border-radius:9px;border:1px solid var(--border);font-size:13px;color:var(--text-1);box-sizing:border-box;">
                  </div>
                  <div style="grid-column:1/-1;">
                    <label style="font-size:11.5px;font-weight:700;color:var(--text-2);display:block;margin-bottom:5px;">Project paths <span style="font-weight:400;color:var(--text-3);">— one per line (leave blank for all accessible)</span></label>
                    <textarea x-model="settingsAppCfg.gitlab.project_ids_raw" rows="3" placeholder="group/project&#10;group/another"
                      style="width:100%;padding:8px 12px;border-radius:9px;border:1px solid var(--border);font-size:13px;color:var(--text-1);box-sizing:border-box;resize:vertical;font-family:monospace;"></textarea>
                  </div>
                </div>
                <div style="display:flex;align-items:center;gap:10px;margin-top:12px;flex-wrap:wrap;">
                  <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                    <input type="checkbox" x-model="settingsAppCfg.gitlab.enabled" style="width:16px;height:16px;accent-color:#fc6d26;">
                    <span style="font-size:13px;font-weight:600;color:var(--text-1);">Enable GitLab integration</span>
                  </label>
                  <div style="flex:1;"></div>
                  <button @click="testSettingsGitLab()" :disabled="settingsGlTestLoading"
                    style="padding:8px 16px;border-radius:9px;background:#fff3ee;border:1.5px solid #fed7aa;color:#c2410c;font-size:12.5px;font-weight:700;cursor:pointer;">
                    <span x-show="!settingsGlTestLoading">⚡ Test</span>
                    <span x-show="settingsGlTestLoading">Testing…</span>
                  </button>
                  <button @click="saveSettingsGitLab()" class="btn-primary" style="font-size:13px;">Save GitLab</button>
                </div>
                <div x-show="settingsGlMsg" style="margin-top:8px;padding:8px 12px;border-radius:9px;font-size:12.5px;font-weight:600;"
                  :style="settingsGlOk?'background:#f0fdf4;border:1px solid #bbf7d0;color:#15803d;':'background:#fff1f2;border:1px solid #fecdd3;color:#be123c;'"
                  x-text="settingsGlMsg"></div>
              </div>

              <!-- Sprint section -->
              <div style="border-top:1px solid var(--border);padding-top:18px;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">
                  <div style="width:28px;height:28px;border-radius:8px;background:#f5f3ff;display:flex;align-items:center;justify-content:center;font-size:14px;">🏃</div>
                  <div style="font-size:14px;font-weight:700;color:var(--text-1);">Sprint</div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                  <div>
                    <label style="font-size:11.5px;font-weight:700;color:var(--text-2);display:block;margin-bottom:5px;">My Jira Email</label>
                    <input x-model="settingsAppCfg.sprint.my_jira_email" type="email" placeholder="you@company.com"
                      style="width:100%;padding:8px 12px;border-radius:9px;border:1px solid var(--border);font-size:13px;color:var(--text-1);box-sizing:border-box;">
                  </div>
                  <div>
                    <label style="font-size:11.5px;font-weight:700;color:var(--text-2);display:block;margin-bottom:5px;">My GitLab Username</label>
                    <input x-model="settingsAppCfg.sprint.my_gitlab_username" type="text" placeholder="gitlab-username"
                      style="width:100%;padding:8px 12px;border-radius:9px;border:1px solid var(--border);font-size:13px;color:var(--text-1);box-sizing:border-box;">
                  </div>
                  <div>
                    <label style="font-size:11.5px;font-weight:700;color:var(--text-2);display:block;margin-bottom:5px;">Jira Board ID</label>
                    <input x-model="settingsAppCfg.sprint.board_id" type="text" placeholder="e.g. 42"
                      style="width:100%;padding:8px 12px;border-radius:9px;border:1px solid var(--border);font-size:13px;color:var(--text-1);box-sizing:border-box;">
                  </div>
                  <div>
                    <label style="font-size:11.5px;font-weight:700;color:var(--text-2);display:block;margin-bottom:5px;">Jira Sprint ID</label>
                    <input x-model="settingsAppCfg.sprint.sprint_id" type="text" placeholder="e.g. 123"
                      style="width:100%;padding:8px 12px;border-radius:9px;border:1px solid var(--border);font-size:13px;color:var(--text-1);box-sizing:border-box;">
                  </div>
                </div>
                <div style="margin-top:12px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                  <button @click="saveSettingsSprint()" class="btn-primary" style="font-size:13px;">Save Sprint</button>
                  <span x-show="settingsSprintMsg" style="font-size:12px;font-weight:600;" :style="settingsSprintOk?'color:#16a34a':'color:#ef4444'" x-text="settingsSprintMsg"></span>
                </div>
                <div x-show="settingsAppCfg.sprint.sprint_id" style="margin-top:8px;font-size:11.5px;color:var(--text-3);">
                  Active sprint: <span style="color:var(--accent);font-weight:600;" x-text="settingsAppCfg.sprint.sprint_name||settingsAppCfg.sprint.sprint_id"></span>
                </div>
              </div>

            </div><!-- /x-show settingsApp -->
          </div><!-- /Integrations card -->
```

- [ ] **Step 3: Commit**

```bash
git add web/static/index.html
git commit -m "feat: Settings page — replace global integration cards with per-app Integrations card"
```

---

### Task 7: Frontend — Settings page JS functions (loadSettingsAppConfig, save/test functions)

**Files:**
- Modify: `web/static/index.html`

- [ ] **Step 1: Replace loadJiraConfig with loadSettingsAppConfig**

Find `async loadJiraConfig()` function and replace it plus `saveJiraConfig()`, `testJira()` with the new settings functions. Locate:
```javascript
    async loadJiraConfig() {
      try {
        const cfg = await fetch('/api/jira/config').then(r=>r.json());
        this.jiraCfg = {
          ...this.jiraCfg, ...cfg,
```
(This block runs through `async saveJiraConfig()` and `async testJira()` — replace everything from `async loadJiraConfig()` through to just before `async loadGitLabConfig()`)

Replace `async loadJiraConfig()` through the end of `async testJira()` with:

```javascript
    async loadSettingsAppConfig() {
      if (!this.settingsApp) return;
      const aid = this.settingsApp;
      try {
        const [j, g, s] = await Promise.all([
          fetch(`/api/applications/${aid}/integrations/jira`).then(r=>r.json()).catch(()=>({})),
          fetch(`/api/applications/${aid}/integrations/gitlab`).then(r=>r.json()).catch(()=>({})),
          fetch(`/api/applications/${aid}/integrations/sprint`).then(r=>r.json()).catch(()=>({})),
        ]);
        this.settingsAppCfg = {
          jira: {
            base_url: j.base_url||'', email: j.email||'', api_token: '',
            project_keys_raw: (j.project_keys||[]).join('\n'), enabled: j.enabled||false,
          },
          gitlab: {
            base_url: g.base_url||'https://gitlab.com', access_token: '',
            project_ids_raw: (g.project_ids||[]).join('\n'), enabled: g.enabled||false,
          },
          sprint: {
            board_id: s.board_id||'', sprint_id: s.sprint_id||'', sprint_name: s.sprint_name||'',
            my_jira_email: s.my_jira_email||'', my_gitlab_username: s.my_gitlab_username||'',
          },
        };
        this.settingsJiraMsg=''; this.settingsGlMsg=''; this.settingsSprintMsg='';
      } catch(e) {}
    },
    async saveSettingsJira() {
      if (!this.settingsApp) return;
      const c = this.settingsAppCfg.jira;
      await fetch(`/api/applications/${this.settingsApp}/integrations/jira`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({
          base_url: c.base_url, email: c.email, api_token: c.api_token,
          project_keys: c.project_keys_raw.split('\n').map(s=>s.trim()).filter(Boolean),
          enabled: c.enabled,
        }),
      });
      this.settingsJiraMsg='Jira config saved ✓'; this.settingsJiraOk=true;
      await this.loadSettingsAppConfig();
    },
    async testSettingsJira() {
      if (!this.settingsApp) return;
      this.settingsJiraTestLoading=true; this.settingsJiraMsg='';
      try {
        const r = await fetch(`/api/jira/test?app_id=${this.settingsApp}`, {method:'POST'});
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail||'Connection failed');
        this.settingsJiraMsg=d.message||'Connected ✓'; this.settingsJiraOk=true;
      } catch(e) { this.settingsJiraMsg=e.message||'Connection failed'; this.settingsJiraOk=false; }
      finally { this.settingsJiraTestLoading=false; }
    },
    async saveSettingsGitLab() {
      if (!this.settingsApp) return;
      const c = this.settingsAppCfg.gitlab;
      await fetch(`/api/applications/${this.settingsApp}/integrations/gitlab`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({
          base_url: c.base_url, access_token: c.access_token,
          project_ids: c.project_ids_raw.split('\n').map(s=>s.trim()).filter(Boolean),
          enabled: c.enabled,
        }),
      });
      this.settingsGlMsg='GitLab config saved ✓'; this.settingsGlOk=true;
      await this.loadSettingsAppConfig();
    },
    async testSettingsGitLab() {
      if (!this.settingsApp) return;
      this.settingsGlTestLoading=true; this.settingsGlMsg='';
      try {
        const r = await fetch(`/api/gitlab/test?app_id=${this.settingsApp}`, {method:'POST'});
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail||'Connection failed');
        this.settingsGlMsg=d.message||'Connected ✓'; this.settingsGlOk=true;
      } catch(e) { this.settingsGlMsg=e.message||'Connection failed'; this.settingsGlOk=false; }
      finally { this.settingsGlTestLoading=false; }
    },
    async saveSettingsSprint() {
      if (!this.settingsApp) return;
      const c = this.settingsAppCfg.sprint;
      await fetch(`/api/applications/${this.settingsApp}/integrations/sprint`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(c),
      });
      this.settingsSprintMsg='Sprint config saved ✓'; this.settingsSprintOk=true;
      await this.loadSettingsAppConfig();
    },
```

- [ ] **Step 2: Replace loadGitLabConfig / saveGitLabConfig / testGitLab**

Find `async loadGitLabConfig()` through the end of `async testGitLab()` and delete the entire block (these are now handled by `loadSettingsAppConfig`, `saveSettingsGitLab`, `testSettingsGitLab` above).

The block to delete spans from:
```javascript
    async loadGitLabConfig() {
      try {
        const cfg = await fetch('/api/gitlab/config').then(r=>r.json());
```
through to just before `async loadJiraTeam()`.

- [ ] **Step 3: Replace loadSprintConfig / saveSprintConfig**

Find `async loadSprintConfig()` and `async saveSprintConfig(fromAdmin=false)` and replace both with:

```javascript
    async loadSprintAppConfig(appId) {
      if (!appId) return;
      try {
        const s = await fetch(`/api/applications/${appId}/integrations/sprint`).then(r=>r.json());
        this.sprintCfg = {
          board_id: s.board_id||'', sprint_id: s.sprint_id||'', sprint_name: s.sprint_name||'',
          my_jira_email: s.my_jira_email||'', my_gitlab_username: s.my_gitlab_username||'',
        };
        const j = await fetch(`/api/applications/${appId}/integrations/jira`).then(r=>r.json());
        this.jiraCfg = { ...this.jiraCfg, base_url: j.base_url||'', email: j.email||'', enabled: j.enabled||false };
      } catch(e) {}
    },
    async saveSprintAppConfig() {
      if (!this.sprintAppId) return;
      await fetch(`/api/applications/${this.sprintAppId}/integrations/sprint`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(this.sprintCfg),
      });
      if (this.sprintCfg.sprint_id) this.loadSprintBoard();
    },
```

- [ ] **Step 4: Update loadJiraTeam to use jiraAppId**

Find `async loadJiraTeam(bust=false)` function. Inside it, replace:
```javascript
        if (bust) await fetch('/api/jira/refresh', {method:'POST'});
        const data = await fetch('/api/jira/team').then(r=>{ if(!r.ok) return r.json().then(d=>{throw new Error(d.detail||'Error');}); return r.json(); });
```
With:
```javascript
        if (bust) await fetch(`/api/jira/refresh?app_id=${this.jiraAppId}`, {method:'POST'});
        const data = await fetch(`/api/jira/team?app_id=${this.jiraAppId}`).then(r=>{ if(!r.ok) return r.json().then(d=>{throw new Error(d.detail||'Error');}); return r.json(); });
```

- [ ] **Step 5: Update loadGitLabMRs to use gitlabAppId**

Find `async loadGitLabMRs(bust=false)`. Inside it, replace:
```javascript
        if (bust) await fetch('/api/gitlab/refresh', {method:'POST'});
        const data = await fetch('/api/gitlab/mrs').then(r=>{ if(!r.ok) return r.json().then(d=>{throw new Error(d.detail||'Error');}); return r.json(); });
```
With:
```javascript
        if (bust) await fetch(`/api/gitlab/refresh?app_id=${this.gitlabAppId}`, {method:'POST'});
        const data = await fetch(`/api/gitlab/mrs?app_id=${this.gitlabAppId}`).then(r=>{ if(!r.ok) return r.json().then(d=>{throw new Error(d.detail||'Error');}); return r.json(); });
```

- [ ] **Step 6: Update loadSprintBoard, loadSprintBoards, loadSprintList to use sprintAppId**

Find `async loadSprintBoard(bust=false)`. Replace the fetch calls to add `?app_id=`:

- `'/api/sprint/refresh'` → `` `/api/sprint/refresh?app_id=${this.sprintAppId}` ``
- `'/api/sprint/board'` → `` `/api/sprint/board?app_id=${this.sprintAppId}` ``

Find `async loadSprintBoards()`. Replace:
- `'/api/sprint/boards'` → `` `/api/sprint/boards?app_id=${this.sprintAppId}` ``

Find `async loadSprintList()`. Replace:
- `` `/api/sprint/sprints?board_id=${this.sprintCfg.board_id}` `` → `` `/api/sprint/sprints?app_id=${this.sprintAppId}&board_id=${this.sprintCfg.board_id}` ``

- [ ] **Step 7: Commit**

```bash
git add web/static/index.html
git commit -m "feat: Settings page JS — per-app loadSettingsAppConfig, save/test functions"
```

---

### Task 8: Frontend — Sprint Board view: add app selector dropdown

**Files:**
- Modify: `web/static/index.html`

- [ ] **Step 1: Add app selector and wire saveSprintAppConfig into Sprint Board**

Find the Sprint Board view opening:
```html
      <div x-show="view==='sprint-board'" x-cloak>
```

Just after this opening div (before the config panel), insert:
```html
        <!-- App selector -->
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
          <label style="font-size:12px;font-weight:700;color:var(--text-2);white-space:nowrap;">Application</label>
          <select x-model="sprintAppId" @change="onSprintAppChange()" style="padding:7px 10px;border-radius:8px;border:1px solid var(--border);font-size:13px;color:var(--text-1);background:var(--bg);">
            <option value="">— select —</option>
            <template x-for="app in applications" :key="app.application_id">
              <option :value="app.application_id" x-text="app.name"></option>
            </template>
          </select>
        </div>
```

- [ ] **Step 2: Update the Sprint Board inline config save button**

Find:
```html
            <button @click="saveSprintConfig()" class="btn-primary" style="width:100%;font-size:13px;padding:9px;">
```
Replace with:
```html
            <button @click="saveSprintAppConfig()" class="btn-primary" style="width:100%;font-size:13px;padding:9px;">
```

- [ ] **Step 3: Add onSprintAppChange helper after saveSprintAppConfig in the JS section**

After the `saveSprintAppConfig` function added in Task 7, add:

```javascript
    async onSprintAppChange() {
      localStorage.setItem('execos_sprint_app', this.sprintAppId);
      this.sprintData = null;
      await this.loadSprintAppConfig(this.sprintAppId);
      if (this.sprintCfg.sprint_id) this.loadSprintBoard();
    },
```

- [ ] **Step 4: Commit**

```bash
git add web/static/index.html
git commit -m "feat: Sprint Board — app selector dropdown with localStorage persistence"
```

---

### Task 9: Frontend — Team Workload view: add app selector dropdown

**Files:**
- Modify: `web/static/index.html`

- [ ] **Step 1: Add app selector at top of jira-team view**

Find the Team Workload view opening:
```html
      <div x-show="view==='jira-team'" x-cloak>
```

Just inside (before the `x-show="!jiraCfg.enabled"` not-connected placeholder), insert:
```html
        <!-- App selector -->
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
          <label style="font-size:12px;font-weight:700;color:var(--text-2);white-space:nowrap;">Application</label>
          <select x-model="jiraAppId" @change="onJiraAppChange()" style="padding:7px 10px;border-radius:8px;border:1px solid var(--border);font-size:13px;color:var(--text-1);background:var(--bg);">
            <option value="">— select —</option>
            <template x-for="app in applications" :key="app.application_id">
              <option :value="app.application_id" x-text="app.name"></option>
            </template>
          </select>
        </div>
```

- [ ] **Step 2: Add onJiraAppChange helper in the JS section**

After `onSprintAppChange`, add:

```javascript
    async onJiraAppChange() {
      localStorage.setItem('execos_jira_app', this.jiraAppId);
      this.jiraData = { team:[], last_fetched:null };
      if (!this.jiraAppId) return;
      const j = await fetch(`/api/applications/${this.jiraAppId}/integrations/jira`).then(r=>r.json()).catch(()=>({}));
      this.jiraCfg = { ...this.jiraCfg, base_url: j.base_url||'', email: j.email||'', enabled: j.enabled||false };
      if (this.jiraCfg.enabled) this.loadJiraTeam();
    },
```

- [ ] **Step 3: Commit**

```bash
git add web/static/index.html
git commit -m "feat: Team Workload — app selector dropdown with localStorage persistence"
```

---

### Task 10: Frontend — Open MRs view: add app selector dropdown

**Files:**
- Modify: `web/static/index.html`

- [ ] **Step 1: Add app selector at top of gitlab-mrs view**

Find the Open MRs view opening:
```html
      <div x-show="view==='gitlab-mrs'" x-cloak>
```

Just inside (before the `x-show="!gitlabCfg.enabled"` placeholder), insert:
```html
        <!-- App selector -->
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
          <label style="font-size:12px;font-weight:700;color:var(--text-2);white-space:nowrap;">Application</label>
          <select x-model="gitlabAppId" @change="onGitLabAppChange()" style="padding:7px 10px;border-radius:8px;border:1px solid var(--border);font-size:13px;color:var(--text-1);background:var(--bg);">
            <option value="">— select —</option>
            <template x-for="app in applications" :key="app.application_id">
              <option :value="app.application_id" x-text="app.name"></option>
            </template>
          </select>
        </div>
```

- [ ] **Step 2: Add onGitLabAppChange helper in the JS section**

After `onJiraAppChange`, add:

```javascript
    async onGitLabAppChange() {
      localStorage.setItem('execos_gitlab_app', this.gitlabAppId);
      this.glData = { all_mrs:[], authors:[], projects:[], total_mrs:0, ready_mrs:0, draft_mrs:0, last_fetched:null };
      if (!this.gitlabAppId) return;
      const g = await fetch(`/api/applications/${this.gitlabAppId}/integrations/gitlab`).then(r=>r.json()).catch(()=>({}));
      this.gitlabCfg = { ...this.gitlabCfg, base_url: g.base_url||'https://gitlab.com', enabled: g.enabled||false };
      if (this.gitlabCfg.enabled) this.loadGitLabMRs();
    },
```

- [ ] **Step 3: Commit**

```bash
git add web/static/index.html
git commit -m "feat: Open MRs — app selector dropdown with localStorage persistence"
```

---

### Task 11: Frontend — Applications view: remove Activate buttons

**Files:**
- Modify: `web/static/index.html`

- [ ] **Step 1: Remove the Jira Activate button and activateJira function call**

Find in the Applications view Jira tab:
```html
                    <button @click="activateJira()"
```
and the full button block through its closing `</button>`. Remove the entire button.

Also remove the subtitle text that references Activate:
```html
                    <div style="font-size:12px;color:var(--text-3);">Per-app Jira credentials. Click Activate to push to global config.</div>
```
Replace with:
```html
                    <div style="font-size:12px;color:var(--text-3);">Per-app Jira credentials for this application.</div>
```

- [ ] **Step 2: Remove the GitLab Activate button**

Find in the Applications view GitLab tab:
```html
                    <button @click="activateGitLab()"
```
and remove the full button. Also update the subtitle:
```html
                    <div style="font-size:12px;color:var(--text-3);">Per-app GitLab credentials. Click Activate to push to global config.</div>
```
To:
```html
                    <div style="font-size:12px;color:var(--text-3);">Per-app GitLab credentials for this application.</div>
```

- [ ] **Step 3: Remove the Sprint Activate button**

Find in the Applications view Sprint tab:
```html
                    <button @click="activateSprint()"
```
(or similar) and remove the full button. Update the subtitle:
```html
                    <div style="font-size:12px;color:var(--text-3);">Board, sprint and identity for this app. Click Activate to push to global config.</div>
```
To:
```html
                    <div style="font-size:12px;color:var(--text-3);">Board, sprint and identity for this application.</div>
```

- [ ] **Step 4: Remove the activateJira, activateGitLab, activateSprint JS functions**

Find and delete these three functions from the JS section:
```javascript
          async activateJira() {
            await fetch('/api/applications/'+this.selApp.application_id+'/integrations/jira/activate',{method:'POST'});
            this.cfgMsg='Jira config activated as global — Sprint Board & Team Workload will use this now ✓';
```
And:
```javascript
          async activateGitLab() {
            await fetch('/api/applications/'+this.selApp.application_id+'/integrations/gitlab/activate',{method:'POST'});
            this.cfgMsg='GitLab config activated as global — Open MRs & Sprint Board will use this now ✓';
```
And the Sprint activate function.

- [ ] **Step 5: Final smoke test — start the server and verify Settings page loads**

```bash
python3 start.py &
sleep 3
curl -s http://localhost:8080/health | python3 -m json.tool
```
Expected: `{"status": "ok", ...}`

Then visit `http://localhost:8080` and:
1. Navigate to Settings — verify the Integrations card appears with app dropdown
2. Navigate to Team Workload — verify app selector appears
3. Navigate to Open MRs — verify app selector appears
4. Navigate to Sprint Board — verify app selector appears
5. Navigate to Applications → any app → Jira tab — verify no Activate button

Kill the server: `pkill -f "python3 start.py"`

- [ ] **Step 6: Commit**

```bash
git add web/static/index.html
git commit -m "feat: Applications view — remove Activate buttons; settings refactor complete"
```
