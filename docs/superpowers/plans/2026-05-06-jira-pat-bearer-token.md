# Jira PAT + Bearer Token Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update Jira integration to use Personal Access Token (PAT) with bearer token authentication, and centralize header configuration.

**Architecture:** Replace basic auth (email + api_token) with bearer token in Authorization header. Centralize all Jira headers in one function for easy maintenance. Update database schema to remove email, rename api_token → pat. Implement token preservation logic so PAT isn't lost when editing other config fields.

**Tech Stack:** FastAPI (backend), SQLAlchemy ORM, Alpine.js (frontend), SQLite

---

## Task 1: Update AppJiraConfigORM Schema

**Files:**
- Modify: `db/models.py:130-141` (AppJiraConfigORM class)

Update the ORM model to remove `email` column and rename `api_token` to `pat`.

- [ ] **Step 1: Read the current AppJiraConfigORM definition**

File: `db/models.py`, lines 130-141

Current code:
```python
class AppJiraConfigORM(Base):
    __tablename__ = "jira_config"

    id           = Column(Integer, primary_key=True, default=1)
    base_url     = Column(String(500), default="")
    email        = Column(String(255), default="")
    api_token    = Column(Text,        default="")
    project_keys = Column(Text,        default="[]")
    enabled      = Column(Boolean,     default=False)
    last_synced  = Column(DateTime,    nullable=True)
    created_at   = Column(DateTime,    default=datetime.utcnow)
    updated_at   = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 2: Remove email column, rename api_token to pat**

Replace the class with:
```python
class AppJiraConfigORM(Base):
    __tablename__ = "jira_config"

    id           = Column(Integer, primary_key=True, default=1)
    base_url     = Column(String(500), default="")
    pat          = Column(Text,        default="")   # Personal Access Token (bearer auth)
    project_keys = Column(Text,        default="[]")
    enabled      = Column(Boolean,     default=False)
    last_synced  = Column(DateTime,    nullable=True)
    created_at   = Column(DateTime,    default=datetime.utcnow)
    updated_at   = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 3: Commit**

```bash
git add db/models.py
git commit -m "refactor: update AppJiraConfigORM to use PAT instead of email+api_token"
```

---

## Task 2: Create Database Migration

**Files:**
- Create: `db/migrations/jira_pat_migration.py` (or add to `db/init_db.py`)

Add migration to alter the jira_config table schema on existing deployments.

- [ ] **Step 1: Check if migration system exists**

Check if there's a migrations folder or if `init_db.py` has migration logic:

```bash
ls db/migrations/ 2>/dev/null || echo "No migrations folder"
grep -n "def.*migrat\|ALTER TABLE" db/init_db.py || echo "No migration logic found"
```

- [ ] **Step 2: Add migration to init_db.py**

Find `db/init_db.py` and add this migration function before `create_all()`:

```python
def _migrate_jira_config():
    """Migrate jira_config table: remove email, rename api_token to pat."""
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    if "jira_config" not in table_names:
        return  # Table doesn't exist yet, will be created fresh
    
    # Check if columns exist
    columns = {col['name'] for col in inspector.get_columns("jira_config")}
    
    with engine.connect() as conn:
        # Drop email column if it exists
        if "email" in columns:
            conn.execute(text("ALTER TABLE jira_config DROP COLUMN email"))
        
        # Rename api_token to pat if api_token exists
        if "api_token" in columns and "pat" not in columns:
            conn.execute(text("ALTER TABLE jira_config RENAME COLUMN api_token TO pat"))
        
        conn.commit()
```

Add this call in the init function (before `Base.metadata.create_all(engine)`):

```python
def init_db():
    _migrate_jira_config()  # Add this line
    Base.metadata.create_all(engine)
```

- [ ] **Step 3: Add imports if needed**

At the top of `db/init_db.py`, ensure you have:
```python
from sqlalchemy import inspect, text
```

- [ ] **Step 4: Test the migration**

Start the app to verify no errors:
```bash
python3 start.py
```

Expected: App starts, no migration errors in logs.

- [ ] **Step 5: Commit**

```bash
git add db/init_db.py
git commit -m "feat: add migration to update jira_config schema (email removal, api_token→pat)"
```

---

## Task 3: Create Centralized _jira_headers() Function

**Files:**
- Modify: `web/routers/jira_routes.py:53-75` (add new function)

Create a centralized function to build Jira API headers with bearer token auth.

- [ ] **Step 1: Add the function after imports**

In `jira_routes.py`, after the cache helpers (around line 35), add:

```python
# ── Jira Header Builder ───────────────────────────────────────────────────────
def _jira_headers(cfg: AppJiraConfigORM) -> dict:
    """Return centralized Jira API headers with bearer token authentication.
    
    All Jira API requests should use these headers for authentication.
    Centralized here for easy maintenance and future changes.
    
    Args:
        cfg: AppJiraConfigORM config with PAT
    
    Returns:
        dict: Headers including Authorization: Bearer <PAT>
    """
    return {
        "Authorization": f"Bearer {cfg.pat}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
```

- [ ] **Step 2: Verify function is in the right place**

It should be near the top of the file, before `_jira_get()` function.

- [ ] **Step 3: Commit**

```bash
git add web/routers/jira_routes.py
git commit -m "feat: add centralized _jira_headers() function for Jira API auth"
```

---

## Task 4: Update _jira_get() to Use Bearer Token

**Files:**
- Modify: `web/routers/jira_routes.py:54-74` (update _jira_get function)

Update the HTTP helper to use bearer token instead of basic auth.

- [ ] **Step 1: Read the current _jira_get() function**

Current code (lines 54-74):
```python
def _jira_get(cfg: AppJiraConfigORM, path: str, params: dict = None):
    """Make an authenticated GET to the Jira Cloud REST API."""
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    url = f"{cfg.base_url.rstrip('/')}/rest/api/3/{path.lstrip('/')}"
    resp = requests.get(
        url,
        params=params or {},
        auth=(cfg.email, cfg.api_token),
        headers={"Accept": "application/json"},
        timeout=15,
        verify=False,
    )
    if resp.status_code == 401:
        raise HTTPException(401, "Jira auth failed — check email and API token")
    if resp.status_code == 403:
        raise HTTPException(403, "Jira returned 403 — token may lack permissions")
    if not resp.ok:
        raise HTTPException(resp.status_code, f"Jira error: {resp.text[:200]}")
    return resp.json()
```

- [ ] **Step 2: Replace with bearer token version**

```python
def _jira_get(cfg: AppJiraConfigORM, path: str, params: dict = None):
    """Make an authenticated GET to the Jira Cloud REST API with bearer token."""
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    url = f"{cfg.base_url.rstrip('/')}/rest/api/3/{path.lstrip('/')}"
    resp = requests.get(
        url,
        params=params or {},
        headers=_jira_headers(cfg),
        timeout=15,
        verify=False,  # Disable SSL verification for corporate proxies/self-signed certs
    )
    if resp.status_code == 401:
        raise HTTPException(401, "Jira auth failed — check PAT and permissions")
    if resp.status_code == 403:
        raise HTTPException(403, "Jira returned 403 — PAT may lack permissions")
    if not resp.ok:
        raise HTTPException(resp.status_code, f"Jira error: {resp.text[:200]}")
    return resp.json()
```

Key changes:
- Removed `auth=(cfg.email, cfg.api_token)` parameter
- Changed `headers={"Accept": "application/json"}` to `headers=_jira_headers(cfg)`
- Updated error message from "API token" to "PAT"

- [ ] **Step 3: Check for other requests calls in the file**

Search for other POST/PATCH calls to Jira:
```bash
grep -n "requests\.\(post\|patch\|delete\)" web/routers/jira_routes.py
```

Update those too (usually in routes that save config). Apply same pattern: remove `auth=`, use `headers=_jira_headers(cfg)`.

- [ ] **Step 4: Commit**

```bash
git add web/routers/jira_routes.py
git commit -m "feat: update Jira API calls to use bearer token via _jira_headers()"
```

---

## Task 5: Update save_jira() Endpoint with PAT Preservation

**Files:**
- Modify: `web/routers/app_integration_routes.py:64-82` (save_jira function)

Implement token preservation logic so that submitting the form with masked `••••` doesn't overwrite the PAT.

- [ ] **Step 1: Read the current save_jira() function**

File: `web/routers/app_integration_routes.py`, around line 64

Current code:
```python
@router.post("/applications/{app_id}/integrations/jira")
def save_jira(app_id: str, body: JiraIn, db: Session = Depends(get_db)):
    c = db.query(AppJiraConfigORM).filter(AppJiraConfigORM.application_id == app_id).first()
    if not c:
        c = AppJiraConfigORM(application_id=app_id)
        db.add(c)
    c.base_url = body.base_url.strip()
    c.email = body.email.strip()
    if body.api_token and body.api_token not in ("••••", ""):
        c.api_token = body.api_token
    # ... rest of function
```

- [ ] **Step 2: Update to use PAT with preservation logic**

Replace with:
```python
@router.post("/applications/{app_id}/integrations/jira")
def save_jira(app_id: str, body: JiraIn, db: Session = Depends(get_db)):
    c = db.query(AppJiraConfigORM).filter(AppJiraConfigORM.application_id == app_id).first()
    if not c:
        c = AppJiraConfigORM(application_id=app_id)
        db.add(c)
    c.base_url = body.base_url.strip()
    
    # PAT preservation: only update if it's a new value (not masked "••••" and not empty)
    if body.pat and body.pat not in ("••••", ""):
        c.pat = body.pat
    elif body.pat == "" and not c.pat:
        # New record with empty PAT — that's ok, just leave it empty
        c.pat = ""
    # If PAT is "••••", it means user didn't change it — keep existing
    
    c.project_keys = json.dumps(body.project_keys)
    c.enabled = body.enabled
    db.commit()
    db.refresh(c)
    return _out(c)
```

Key changes:
- Removed `c.email = body.email.strip()` (email field gone)
- Replaced `api_token` with `pat`
- Added preservation logic for PAT with "••••" check

- [ ] **Step 3: Update JiraIn Pydantic model**

Find the `JiraIn` class (around line 20-30) and update:

Old:
```python
class JiraIn(BaseModel):
    base_url: str
    email: str
    api_token: str
    project_keys: List[str] = []
    enabled: bool = False
```

New:
```python
class JiraIn(BaseModel):
    base_url: str
    pat: str  # Personal Access Token
    project_keys: List[str] = []
    enabled: bool = False
```

Remove `email` field.

- [ ] **Step 4: Update _out() helper if it references email**

Find `_out()` function for Jira config and remove `email` field if present:

```python
def _out(c: AppJiraConfigORM) -> dict:
    return {
        "base_url": c.base_url,
        "pat": "••••" if c.pat else "",  # Mask the PAT for security
        "project_keys": json.loads(c.project_keys or "[]"),
        "enabled": c.enabled,
        "last_synced": c.last_synced,
    }
```

- [ ] **Step 5: Commit**

```bash
git add web/routers/app_integration_routes.py
git commit -m "feat: update save_jira() to use PAT with preservation logic"
```

---

## Task 6: Update Jira Config UI Form

**Files:**
- Modify: `web/static/index.html` (Jira config form section, around line 4500+)

Remove email field, rename API Token to Personal Access Token, implement masking.

- [ ] **Step 1: Find the Jira config form**

Search for the Jira config modal/form in index.html:
```bash
grep -n "jira\|Jira" web/static/index.html | grep -i "modal\|form\|label" | head -20
```

Look for the form with email and api_token inputs.

- [ ] **Step 2: Remove email input field**

Find the email input section and delete it. It should look like:
```html
<div>
  <label>Email</label>
  <input x-model="jirac.email" placeholder="..." />
</div>
```

Delete this entire section.

- [ ] **Step 3: Rename API Token field to Personal Access Token**

Find the api_token input and update:

Old:
```html
<div>
  <label>API Token</label>
  <input x-model="jirac.api_token" type="password" placeholder="Jira API token" />
</div>
```

New:
```html
<div>
  <label>Personal Access Token (PAT)</label>
  <input x-model="jirac.pat" type="password" placeholder="Your Jira Personal Access Token" />
</div>
```

- [ ] **Step 4: Implement PAT masking in display**

When showing existing config (not editing), display PAT as masked `••••`. Find where Jira config is displayed (read-only view) and update:

Old:
```html
<div x-show="jiraConfig.api_token">API Token: <span x-text="jiraConfig.api_token ? '••••' : ''"></span></div>
```

New (if not already masked):
```html
<div x-show="jiraConfig.pat">PAT: <span x-text="jiraConfig.pat ? '••••' : ''"></span></div>
```

- [ ] **Step 5: Update any references in JavaScript**

Search for references to `jirac.email` or `jirac.api_token` in the form handling code and update to use `jirac.pat`:

```bash
grep -n "jirac\.\(email\|api_token\)" web/static/index.html
```

Replace all `jirac.email` references with nothing (remove them), and `jirac.api_token` with `jirac.pat`.

- [ ] **Step 6: Test the form**

Start the app and:
1. Navigate to Jira config section
2. Verify email field is gone
3. Verify "Personal Access Token" label exists
4. Enter a test PAT, save
5. Verify PAT is masked as `••••` on reload
6. Edit again without changing PAT, save
7. Verify PAT is still there (not deleted)

- [ ] **Step 7: Commit**

```bash
git add web/static/index.html
git commit -m "feat: update Jira config form to use PAT, remove email field"
```

---

## Task 7: Test End-to-End

**Files:**
- Test: Manual testing + optional automated tests

Verify the entire Jira integration works with PAT and bearer token.

- [ ] **Step 1: Start the dev server**

```bash
python3 start.py
```

- [ ] **Step 2: Create/Update Jira Config**

1. Navigate to Settings → Jira
2. Enter:
   - Base URL: `https://your-instance.atlassian.net`
   - Personal Access Token: (your valid PAT from Jira)
   - Project Keys: `TEST,ENG` (or your actual keys)
   - Enable: ✓
3. Click Save
4. Verify success (no auth error)

- [ ] **Step 3: Test Jira API Call**

Trigger a Jira API call (e.g., fetch issues, search):
```bash
curl -X GET http://localhost:8080/api/jira/issues \
  -H "Content-Type: application/json"
```

Expected: Returns issues from Jira with 200 status.

- [ ] **Step 4: Test PAT Preservation**

1. Go back to Jira config form
2. Change only Base URL (leave PAT field as-is)
3. Click Save
4. Verify:
   - Base URL was updated
   - PAT still works (no auth error)
   - PAT shown as `••••` (masked)

- [ ] **Step 5: Test Invalid PAT**

1. Clear PAT field or enter invalid value
2. Click Save
3. Trigger Jira API call
4. Verify: Returns 401 error with message "Jira auth failed — check PAT and permissions"

- [ ] **Step 6: Verify Header Centralization**

Check that all Jira API calls use `_jira_headers()`:
```bash
grep -n "_jira_headers\|auth=" web/routers/jira_routes.py
```

Expected: All requests use `_jira_headers()`, no `auth=` parameter found.

- [ ] **Step 7: Run existing tests**

```bash
python3 -m pytest tests/test_jira* -v 2>&1 | head -50
```

Expected: Any existing Jira tests should pass (may need updates if they test auth method).

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "test: verify Jira PAT + bearer token auth end-to-end"
```

---

## Summary

**What was implemented:**
- Database schema updated: removed `email`, renamed `api_token` → `pat`
- Centralized `_jira_headers()` function for bearer token auth
- All Jira API calls use bearer token via Authorization header
- UI form updated: removed email, renamed to Personal Access Token
- PAT preservation logic prevents accidental loss when editing other fields
- Token masking for security (`••••` in UI)

**Files modified:**
- `db/models.py` — AppJiraConfigORM schema
- `db/init_db.py` — Migration to update existing tables
- `web/routers/jira_routes.py` — Bearer token auth, centralized headers
- `web/routers/app_integration_routes.py` — PAT preservation logic
- `web/static/index.html` — UI form updates

**Testing checklist:**
- [ ] Create new Jira config with valid PAT
- [ ] Jira API calls succeed with bearer token
- [ ] PAT preserved when editing other fields
- [ ] Invalid PAT returns clear error message
- [ ] Existing tests pass
