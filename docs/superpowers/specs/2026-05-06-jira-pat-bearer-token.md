# Jira Integration — Personal Access Token + Bearer Token Auth

**Date:** 2026-05-06  
**Feature:** Update Jira auth to use PAT with bearer token, centralize header config  
**Status:** Design approved

## Overview

Update Jira integration from basic auth (email + API token) to Personal Access Token (PAT) with bearer token authentication in HTTP headers. Centralize all header/auth configuration in one place for easy future changes.

## Current State → New State

| Aspect | Current | New |
|--------|---------|-----|
| Auth Method | Basic auth `(email, api_token)` | Bearer token in Authorization header |
| Token Type | Jira API token | Personal Access Token (PAT) |
| Database Fields | `email`, `api_token` | `pat` (email removed) |
| Headers | Inline in each call | Centralized `_jira_headers()` function |
| API Version | v3 | v3 (unchanged) |

## Architecture

### Database Schema Changes

**Update `AppJiraConfigORM` table:**
- Remove `email` column (no longer needed for PAT)
- Rename `api_token` → `pat`
- Keep: `base_url`, `project_keys`, `enabled`, timestamps

Migration: Existing configs with email+api_token will need to be reconfigured with PAT. Old data can be dropped.

### Centralized Header Configuration

Create new function in `jira_routes.py`:

```python
def _jira_headers(cfg: AppJiraConfigORM) -> dict:
    """Return centralized Jira API headers with bearer token auth.
    
    All requests to Jira API should use these headers.
    Centralized here for easy maintenance and future changes.
    """
    return {
        "Authorization": f"Bearer {cfg.pat}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
```

**Usage:**
- Replace all inline `headers={"Accept": "application/json"}` with `headers=_jira_headers(cfg)`
- Replace all `auth=(cfg.email, cfg.api_token)` with `headers=_jira_headers(cfg)` and remove auth parameter

### API Call Updates

**All Jira API calls:**
- Remove basic auth parameter: `auth=(cfg.email, cfg.api_token)`
- Use centralized headers: `headers=_jira_headers(cfg)`
- Example:
  ```python
  # Before
  requests.get(url, auth=(cfg.email, cfg.api_token), headers={"Accept": "application/json"})
  
  # After
  requests.get(url, headers=_jira_headers(cfg))
  ```

Affected functions in `jira_routes.py`:
- `_jira_get()`
- Any POST/PATCH calls to Jira API

### UI Changes

**Jira config form in web/static/index.html:**

Remove these fields:
- Email input field (no longer needed)

Update these fields:
- Rename label: "API Token" → "Personal Access Token"
- Update placeholder/help text: "Your Jira Personal Access Token (PAT)"
- Keep masking behavior: Display as `••••` when showing existing value

**Form layout:**
- Base URL
- Personal Access Token (masked)
- Project Keys
- Enabled checkbox

### Token Preservation (Fix)

When user submits the Jira config form:

**Backend logic in update endpoint (`web/routers/app_integration_routes.py`):**

```python
# Only update PAT if it's a new value (not masked "••••" and not empty)
if body.pat and body.pat not in ("••••", ""):
    cfg.pat = body.pat
elif body.pat == "" and not cfg.pat:
    # New record with empty PAT — that's ok, just leave it empty
    cfg.pat = ""
# If PAT is "••••", it means user didn't change it — keep existing
```

**Behavior:**
- User edits base_url or other fields without touching PAT field → existing PAT preserved
- User clears PAT field intentionally (empty string) → PAT is cleared
- User enters new PAT → PAT is updated
- User's form shows PAT as `••••` (masked) when editing → clicking save preserves it

This allows safe, repeated editing without requiring user to re-enter sensitive tokens.

## Testing

1. **Auth verification:**
   - Jira config with valid PAT → successful API calls (search, issues, etc.)
   - Jira config with invalid PAT → 401 error with clear message

2. **Token preservation:**
   - Edit config, don't touch PAT field → PAT remains unchanged
   - Edit config, clear PAT field → PAT cleared
   - Edit config, enter new PAT → PAT updated

3. **Header centralization:**
   - All Jira API responses successful with bearer token
   - No basic auth errors
   - Header format correct: `Authorization: Bearer <PAT>`

## Migration & Backward Compatibility

**Breaking change:** Existing Jira configs cannot be auto-migrated (PAT is different from API token).

**User action required:**
- Navigate to Jira config in Settings
- Replace email field removal (done automatically in UI)
- Enter new Personal Access Token (from Jira)
- Save

**Data cleanup:**
- Old `email` and `api_token` columns dropped from database
- If preserving data for audit: keep a migration log noting old configs were replaced

## Edge Cases

**What if PAT is not set?**
- Allow empty PAT (user might not have configured yet)
- API calls return 401 with message: "Jira PAT not configured — configure in Settings"

**What if base_url is incorrect?**
- Return clear error: "Cannot reach Jira — check base URL"

**What if user enters old API token instead of PAT?**
- API call fails with 401: "Invalid Jira credentials — ensure you're using a Personal Access Token"

## Implementation Sequence

1. Update `AppJiraConfigORM` model: remove `email`, rename `api_token` → `pat`
2. Update database migration to alter table
3. Create `_jira_headers()` function in `jira_routes.py`
4. Update all Jira API calls to use `_jira_headers()`
5. Update Jira config form UI: remove email, rename field, mask PAT
6. Update backend endpoint to preserve PAT (check for "••••")
7. Test: auth, token preservation, error messages
8. Update documentation/README about PAT setup

## Success Criteria

- [x] Jira auth uses bearer token in Authorization header (not basic auth)
- [x] All headers centralized in one function for easy changes
- [x] PAT properly masked in UI and preserved on save
- [x] Existing configs require reconfiguration (documented)
- [x] Clear error messages for auth failures
- [x] All Jira API calls working with PAT
- [x] Tests verify token preservation behavior
