# Segment 1 — Jira Backend Fixes

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Fix the three critical Jira backend issues: (1) add a user-supplied JQL filter endpoint, (2) replace mock-data reads in `my_work_routes.py` with real Jira + GitLab API calls, (3) add active-sprint auto-detection so PMs never have to look up a sprint ID manually.

**Architecture:** All changes are additive to existing routers. No schema changes. The JQL filter endpoint is a new `GET /api/jira/filter` on the existing `jira_routes.py`. The my-work fix replaces `MockJiraIssueORM` imports with direct HTTP calls reusing the existing `_jira_get` helper pattern. Sprint auto-detection adds two new `GET` endpoints to `sprint_routes.py`.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, `requests`, APScheduler (unchanged). No new dependencies.

---

## File Map

| Action | File |
|--------|------|
| Modify | `web/routers/jira_routes.py` — add `/api/jira/filter` and `/api/jira/boards` endpoints |
| Modify | `web/routers/my_work_routes.py` — remove Mock ORM imports, add real Jira + GitLab calls |
| Modify | `web/routers/sprint_routes.py` — add `/api/sprint/{app_id}/active-sprint` and `/api/sprint/{app_id}/boards` |
| Modify | `web/static/index.html` — add JQL input to Jira Team view + "Detect Sprint" button |
| Create | `tests/test_jira_filter.py` — tests for new JQL endpoint |
| Create | `tests/test_my_work_real.py` — tests for fixed my-work endpoint |
| Create | `tests/test_sprint_autodetect.py` — tests for active sprint detection |

---

## Task 1 — Add `/api/jira/filter` endpoint

**Files:**
- Modify: `web/routers/jira_routes.py`
- Create: `tests/test_jira_filter.py`

### Step 1.1 — Write the failing tests

Create `tests/test_jira_filter.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from web.app import app

client = TestClient(app)


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
    assert resp.status_code == 422  # FastAPI validation error for missing required param


@patch("web.routers.jira_routes._get_cfg")
def test_filter_returns_400_when_jira_disabled(mock_get_cfg):
    mock_get_cfg.return_value = _mock_jira_cfg(enabled=False)
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
```

### Step 1.2 — Run tests to confirm they fail

```bash
cd /Users/puneetsharma/Workspace/projects/ai-lab/command-center
python -m pytest tests/test_jira_filter.py -v 2>&1 | tail -20
```

Expected: `FAILED` — `test_filter_returns_issues_grouped_by_assignee` fails because `/api/jira/filter` does not exist yet (404).

### Step 1.3 — Implement the endpoint

Open `web/routers/jira_routes.py`. After the existing `@router.get("/team")` block and before `@router.post("/refresh")`, add:

```python
@router.get("/filter")
def jql_filter(
    jql: str = Query(..., min_length=1, max_length=2000, description="Custom JQL query"),
    app_id: str = Query(...),
    db: Session = Depends(_db),
):
    """Execute a user-supplied JQL query and return results grouped by assignee."""
    cfg = _get_cfg(db)
    if not cfg.enabled or not cfg.pat:
        raise HTTPException(400, "Jira integration is not enabled — configure it in Settings first")

    import hashlib
    cache_key = f"jql_{hashlib.md5(jql.encode()).hexdigest()}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    fields = "summary,assignee,status,priority,issuetype,project,created,updated,duedate"
    issues = _jira_search_all(cfg, jql, fields)

    by_assignee: dict = {}
    for issue in issues:
        f = issue.get("fields", {}) or {}
        assignee = f.get("assignee") or {}
        name  = assignee.get("displayName", "Unassigned")
        akey  = assignee.get("accountId", "__unassigned__")
        avatar = (assignee.get("avatarUrls") or {}).get("48x48")

        if akey not in by_assignee:
            by_assignee[akey] = {
                "account_id":   akey,
                "display_name": name,
                "avatar_url":   avatar,
                "issues":       [],
                "total":        0,
            }

        by_assignee[akey]["issues"].append({
            "key":      issue["key"],
            "summary":  f.get("summary", ""),
            "status":   (f.get("status")    or {}).get("name", ""),
            "priority": (f.get("priority")  or {}).get("name", ""),
            "type":     (f.get("issuetype") or {}).get("name", ""),
            "project":  (f.get("project")   or {}).get("key", ""),
            "due_date": f.get("duedate"),
            "updated":  (f.get("updated")   or "")[:10],
            "web_url":  f"{cfg.base_url.rstrip('/')}/browse/{issue['key']}",
        })
        by_assignee[akey]["total"] += 1

    result = {
        "jql":         jql,
        "total":       len(issues),
        "by_assignee": sorted(by_assignee.values(), key=lambda x: -x["total"]),
        "last_fetched": datetime.utcnow().isoformat(),
    }
    _cache_set(cache_key, result)
    return result
```

### Step 1.4 — Run tests to confirm they pass

```bash
python -m pytest tests/test_jira_filter.py -v 2>&1 | tail -10
```

Expected: All 5 tests `PASSED`.

### Step 1.5 — Commit

```bash
git add web/routers/jira_routes.py tests/test_jira_filter.py
git commit -m "feat: add /api/jira/filter endpoint for custom JQL queries"
```

---

## Task 2 — Fix `/api/my-work` to use real Jira + GitLab APIs

**Files:**
- Modify: `web/routers/my_work_routes.py`
- Create: `tests/test_my_work_real.py`

### Step 2.1 — Write the failing tests

Create `tests/test_my_work_real.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from web.app import app

client = TestClient(app)


def _sprint_cfg(email="alice@example.com", gitlab="alice_gl"):
    cfg = MagicMock()
    cfg.my_jira_email      = email
    cfg.my_gitlab_username = gitlab
    return cfg


def _jira_cfg(enabled=True, pat="pat", base_url="https://jira.example.com"):
    cfg = MagicMock()
    cfg.enabled  = enabled
    cfg.pat      = pat
    cfg.base_url = base_url
    return cfg


def _gl_cfg(enabled=True, token="gltoken", base_url="https://gitlab.example.com", project_ids='["mygroup/myrepo"]'):
    cfg = MagicMock()
    cfg.enabled       = enabled
    cfg.access_token  = token
    cfg.base_url      = base_url
    cfg.project_ids   = project_ids
    return cfg


@patch("web.routers.my_work_routes.requests")
@patch("web.routers.my_work_routes._get_gl_configs")
@patch("web.routers.my_work_routes._get_jira_cfg")
@patch("web.routers.my_work_routes._get_sprint_cfg")
def test_my_work_returns_real_jira_issues(mock_sprint, mock_jira, mock_gl, mock_req):
    mock_sprint.return_value = _sprint_cfg()
    mock_jira.return_value   = _jira_cfg()
    mock_gl.return_value     = []

    jira_resp = MagicMock()
    jira_resp.ok = True
    jira_resp.json.return_value = {
        "issues": [{
            "key": "PROJ-42",
            "fields": {
                "summary": "Real Jira issue",
                "status":    {"name": "In Progress"},
                "priority":  {"name": "High"},
                "issuetype": {"name": "Story"},
                "project":   {"key": "PROJ"},
                "duedate":   "2026-07-10",
            }
        }]
    }
    mock_req.get.return_value = jira_resp

    resp = client.get("/api/my-work")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["jira"]) == 1
    assert data["jira"][0]["key"] == "PROJ-42"
    assert data["jira"][0]["web_url"] == "https://jira.example.com/browse/PROJ-42"


@patch("web.routers.my_work_routes.requests")
@patch("web.routers.my_work_routes._get_gl_configs")
@patch("web.routers.my_work_routes._get_jira_cfg")
@patch("web.routers.my_work_routes._get_sprint_cfg")
def test_my_work_returns_real_gitlab_mrs(mock_sprint, mock_jira, mock_gl, mock_req):
    mock_sprint.return_value = _sprint_cfg(gitlab="alice_gl")
    mock_jira.return_value   = _jira_cfg(enabled=False)
    mock_gl.return_value     = [_gl_cfg()]

    mr_resp = MagicMock()
    mr_resp.ok = True
    mr_resp.json.return_value = [{
        "iid": 7,
        "title": "My feature MR",
        "state": "opened",
        "draft": False,
        "target_branch": "main",
        "web_url": "https://gitlab.example.com/mygroup/myrepo/-/merge_requests/7",
        "updated_at": "2026-06-16T12:00:00.000Z",
    }]
    mock_req.get.return_value = mr_resp

    resp = client.get("/api/my-work")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["mrs"]) == 1
    assert data["mrs"][0]["iid"] == 7
    assert data["mrs"][0]["title"] == "My feature MR"


@patch("web.routers.my_work_routes._get_gl_configs")
@patch("web.routers.my_work_routes._get_jira_cfg")
@patch("web.routers.my_work_routes._get_sprint_cfg")
def test_my_work_returns_empty_jira_when_disabled(mock_sprint, mock_jira, mock_gl):
    mock_sprint.return_value = _sprint_cfg()
    mock_jira.return_value   = _jira_cfg(enabled=False)
    mock_gl.return_value     = []

    resp = client.get("/api/my-work")
    assert resp.status_code == 200
    data = resp.json()
    assert data["jira"] == []


@patch("web.routers.my_work_routes.requests")
@patch("web.routers.my_work_routes._get_gl_configs")
@patch("web.routers.my_work_routes._get_jira_cfg")
@patch("web.routers.my_work_routes._get_sprint_cfg")
def test_my_work_jira_failure_returns_empty_not_500(mock_sprint, mock_jira, mock_gl, mock_req):
    """Jira API failure must not crash the endpoint — return empty list instead."""
    mock_sprint.return_value = _sprint_cfg()
    mock_jira.return_value   = _jira_cfg()
    mock_gl.return_value     = []
    mock_req.get.side_effect = Exception("Connection timeout")

    resp = client.get("/api/my-work")
    assert resp.status_code == 200
    data = resp.json()
    assert data["jira"] == []
    assert "error" in data  # endpoint should surface the error message
```

### Step 2.2 — Run to confirm they fail

```bash
python -m pytest tests/test_my_work_real.py -v 2>&1 | tail -15
```

Expected: Tests fail — the current endpoint imports `MockJiraIssueORM` and will either pass with empty data (wrong) or error.

### Step 2.3 — Rewrite `web/routers/my_work_routes.py`

Replace the entire file content:

```python
"""My Book of Work — aggregates local tasks, real Jira issues, and real GitLab MRs."""

import json
import logging
import urllib.parse
import urllib3

import requests
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date

from db.base import get_db
from db.models import TaskORM, JiraConfigORM, AppGitLabConfigORM, SprintConfigORM

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger("execos.my_work")
router = APIRouter(prefix="/api/my-work", tags=["my-work"])

_HEADERS_JIRA  = lambda pat: {"Authorization": f"Bearer {pat}", "Accept": "application/json"}
_HEADERS_GL    = lambda tok: {"PRIVATE-TOKEN": tok, "Accept": "application/json"}


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _get_sprint_cfg(db: Session) -> SprintConfigORM:
    cfg = db.query(SprintConfigORM).first()
    if not cfg:
        cfg = SprintConfigORM(id=1)
        db.add(cfg)
        db.commit()
    return cfg


def _get_jira_cfg(db: Session) -> JiraConfigORM:
    cfg = db.query(JiraConfigORM).first()
    if not cfg:
        cfg = JiraConfigORM(id=1)
        db.add(cfg)
        db.commit()
    return cfg


def _get_gl_configs(db: Session) -> list:
    return db.query(AppGitLabConfigORM).filter(AppGitLabConfigORM.enabled == True).all()


# ── Serialisers ────────────────────────────────────────────────────────────────

def _task_out(t: TaskORM) -> dict:
    today = date.today()
    return {
        "task_id":    t.task_id,
        "title":      t.title,
        "status":     t.status,
        "priority":   t.priority,
        "due_date":   str(t.due_date) if t.due_date else None,
        "is_overdue": bool(t.due_date and t.due_date < today and t.status not in ("done", "cancelled")),
        "project_id": t.project_id,
    }


# ── Main endpoint ──────────────────────────────────────────────────────────────

@router.get("")
def my_work(db: Session = Depends(get_db)):
    """Personal work view: real local tasks + real Jira issues + real GitLab MRs."""
    sprint_cfg = _get_sprint_cfg(db)
    jira_cfg   = _get_jira_cfg(db)
    gl_cfgs    = _get_gl_configs(db)

    my_email  = sprint_cfg.my_jira_email or ""
    my_gitlab = sprint_cfg.my_gitlab_username or ""

    # ── Local tasks ────────────────────────────────────────────────────────────
    local_tasks = (
        db.query(TaskORM)
        .filter(TaskORM.status.notin_(["done", "cancelled"]))
        .order_by(TaskORM.due_date)
        .all()
    )

    # ── Jira: real API call ────────────────────────────────────────────────────
    jira_issues = []
    jira_error  = None
    if jira_cfg.enabled and jira_cfg.pat:
        jql = 'assignee = currentUser() AND statusCategory != "Done" ORDER BY updated DESC'
        try:
            resp = requests.get(
                f"{jira_cfg.base_url.rstrip('/')}/rest/api/2/search",
                headers=_HEADERS_JIRA(jira_cfg.pat),
                params={
                    "jql": jql,
                    "maxResults": 100,
                    "fields": "summary,status,priority,issuetype,project,duedate,updated",
                },
                timeout=15,
                verify=False,
            )
            if resp.ok:
                for issue in resp.json().get("issues", []):
                    f = issue.get("fields", {}) or {}
                    jira_issues.append({
                        "key":      issue["key"],
                        "summary":  f.get("summary", ""),
                        "status":   (f.get("status")    or {}).get("name", ""),
                        "priority": (f.get("priority")  or {}).get("name", ""),
                        "type":     (f.get("issuetype") or {}).get("name", ""),
                        "project":  (f.get("project")   or {}).get("key", ""),
                        "due_date": f.get("duedate"),
                        "updated":  (f.get("updated")   or "")[:10],
                        "web_url":  f"{jira_cfg.base_url.rstrip('/')}/browse/{issue['key']}",
                    })
            else:
                jira_error = f"Jira returned {resp.status_code}"
        except Exception as exc:
            log.warning("Jira fetch error: %s", exc)
            jira_error = str(exc)

    # ── GitLab: real API calls across all enabled apps ─────────────────────────
    mrs = []
    if my_gitlab and gl_cfgs:
        for gl_cfg in gl_cfgs:
            if not gl_cfg.access_token:
                continue
            raw_ids = json.loads(gl_cfg.project_ids or "[]")
            base    = gl_cfg.base_url.rstrip("/")
            for pid in raw_ids[:15]:
                encoded = urllib.parse.quote(str(pid), safe="")
                try:
                    resp = requests.get(
                        f"{base}/api/v4/projects/{encoded}/merge_requests",
                        headers=_HEADERS_GL(gl_cfg.access_token),
                        params={
                            "state":           "opened",
                            "author_username": my_gitlab,
                            "per_page":        50,
                            "order_by":        "updated_at",
                        },
                        timeout=10,
                        verify=False,
                    )
                    if resp.ok:
                        for mr in resp.json():
                            mrs.append({
                                "iid":           mr["iid"],
                                "title":         mr.get("title", ""),
                                "state":         mr.get("state", "opened"),
                                "draft":         mr.get("draft", mr.get("work_in_progress", False)),
                                "target_branch": mr.get("target_branch", ""),
                                "web_url":       mr.get("web_url", ""),
                                "updated_at":    (mr.get("updated_at") or "")[:10],
                                "project":       str(pid),
                                "has_conflicts": mr.get("has_conflicts", False),
                            })
                except Exception as exc:
                    log.warning("GitLab MR fetch error for %s: %s", pid, exc)

    return {
        "my_jira_email":      my_email,
        "my_gitlab_username": my_gitlab,
        "tasks":              [_task_out(t) for t in local_tasks],
        "jira":               jira_issues,
        "mrs":                mrs,
        **({"error": jira_error} if jira_error else {}),
    }


@router.get("/team/{member_id}")
def team_member_work(member_id: str, db: Session = Depends(get_db)):
    """Tasks for a specific team member (local only — use /api/jira/team for Jira data)."""
    from db.models import TeamMemberORM
    member = db.query(TeamMemberORM).filter(TeamMemberORM.member_id == member_id).first()
    if not member:
        return {"tasks": [], "jira": [], "mrs": [], "member": None}

    tasks = (
        db.query(TaskORM)
        .filter(TaskORM.assignee_id == member_id, TaskORM.status.notin_(["done", "cancelled"]))
        .order_by(TaskORM.due_date)
        .all()
    )
    return {
        "member": {
            "member_id": member.member_id,
            "name":      member.name,
            "email":     member.email or "",
            "role":      member.role or "",
        },
        "tasks": [_task_out(t) for t in tasks],
        "jira":  [],   # Use /api/jira/filter with assignee=email for live Jira data
        "mrs":   [],   # Use /api/gitlab/mrs for live MR data
    }
```

### Step 2.4 — Run tests to confirm they pass

```bash
python -m pytest tests/test_my_work_real.py -v 2>&1 | tail -10
```

Expected: All 4 tests `PASSED`.

### Step 2.5 — Smoke test against running server

```bash
curl -s http://localhost:8080/api/my-work | python3 -m json.tool | head -20
```

Expected: JSON with `tasks`, `jira`, `mrs` keys. If Jira not configured, `jira: []`. No 500 errors.

### Step 2.6 — Commit

```bash
git add web/routers/my_work_routes.py tests/test_my_work_real.py
git commit -m "fix: replace MockJiraIssueORM with real Jira+GitLab API calls in my-work endpoint"
```

---

## Task 3 — Sprint active-sprint auto-detection

**Files:**
- Modify: `web/routers/sprint_routes.py`
- Create: `tests/test_sprint_autodetect.py`

### Step 3.1 — Write the failing tests

Create `tests/test_sprint_autodetect.py`:

```python
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
    cfg.board_id = ""
    cfg.sprint_id = ""
    return cfg


@patch("web.routers.sprint_routes._jira_get")
@patch("web.routers.sprint_routes._get_jira_cfg")
@patch("web.routers.sprint_routes._get_cfg")
def test_active_sprint_found(mock_sprint_cfg, mock_jira_cfg, mock_jira_get):
    mock_sprint_cfg.return_value = _mock_sprint_cfg()
    mock_jira_cfg.return_value   = _mock_jira_cfg()
    mock_jira_get.return_value   = {
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


@patch("web.routers.sprint_routes._jira_get")
@patch("web.routers.sprint_routes._get_jira_cfg")
@patch("web.routers.sprint_routes._get_cfg")
def test_no_active_sprint_returns_found_false(mock_sprint_cfg, mock_jira_cfg, mock_jira_get):
    mock_sprint_cfg.return_value = _mock_sprint_cfg()
    mock_jira_cfg.return_value   = _mock_jira_cfg()
    mock_jira_get.return_value   = {"values": []}

    resp = client.get(f"/api/sprint/{APP_ID}/active-sprint?board_id=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is False
    assert data["sprint"] is None


@patch("web.routers.sprint_routes._jira_get")
@patch("web.routers.sprint_routes._get_jira_cfg")
@patch("web.routers.sprint_routes._get_cfg")
def test_boards_endpoint_returns_list(mock_sprint_cfg, mock_jira_cfg, mock_jira_get):
    mock_sprint_cfg.return_value = _mock_sprint_cfg()
    mock_jira_cfg.return_value   = _mock_jira_cfg()
    mock_jira_get.return_value   = {
        "values": [
            {"id": 1, "name": "PROJ board", "type": "scrum", "location": {"projectKey": "PROJ"}},
            {"id": 2, "name": "OPS board",  "type": "kanban","location": {"projectKey": "OPS"}},
        ]
    }

    resp = client.get(f"/api/sprint/{APP_ID}/boards")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["boards"]) == 2
    assert data["boards"][0]["id"] == 1
    assert data["boards"][0]["name"] == "PROJ board"
    assert data["boards"][0]["project_key"] == "PROJ"


@patch("web.routers.sprint_routes._get_jira_cfg")
@patch("web.routers.sprint_routes._get_cfg")
def test_active_sprint_requires_board_id(mock_sprint_cfg, mock_jira_cfg):
    mock_sprint_cfg.return_value = _mock_sprint_cfg()
    mock_jira_cfg.return_value   = _mock_jira_cfg()

    resp = client.get(f"/api/sprint/{APP_ID}/active-sprint")  # no board_id
    assert resp.status_code == 422
```

### Step 3.2 — Run to confirm they fail

```bash
python -m pytest tests/test_sprint_autodetect.py -v 2>&1 | tail -15
```

Expected: All 4 tests fail with 404 — endpoints don't exist yet.

### Step 3.3 — Add endpoints to `web/routers/sprint_routes.py`

At the end of the file, before any existing `@router.post("/refresh")` if present, add:

```python
@router.get("/{app_id}/boards")
def list_boards(app_id: str, db: Session = Depends(_db)):
    """List all Jira boards accessible to the configured PAT."""
    _get_cfg(app_id, db)          # validates app exists
    jira_cfg = _get_jira_cfg(db)

    data = _jira_get(jira_cfg, f"rest/agile/1.0/board", {"maxResults": 50})
    boards = [
        {
            "id":          b["id"],
            "name":        b.get("name", ""),
            "type":        b.get("type", ""),
            "project_key": (b.get("location") or {}).get("projectKey", ""),
        }
        for b in data.get("values", [])
    ]
    return {"boards": boards}


@router.get("/{app_id}/active-sprint")
def active_sprint(
    app_id: str,
    board_id: str = Query(..., description="Jira board ID (integer)"),
    db: Session = Depends(_db),
):
    """Return the active sprint for a board — no manual sprint_id lookup needed."""
    _get_cfg(app_id, db)
    jira_cfg = _get_jira_cfg(db)

    data    = _jira_get(jira_cfg, f"rest/agile/1.0/board/{board_id}/sprint", {"state": "active"})
    sprints = data.get("values", [])

    if not sprints:
        return {"found": False, "sprint": None}

    s = sprints[0]
    return {
        "found": True,
        "sprint": {
            "id":         s["id"],
            "name":       s.get("name", ""),
            "state":      s.get("state", ""),
            "start_date": (s.get("startDate") or "")[:10],
            "end_date":   (s.get("endDate")   or "")[:10],
        },
    }
```

Note: The existing `_jira_get` helper in `sprint_routes.py` prefixes the full path itself (line 53: `url = f"{cfg.base_url.rstrip('/')}/{path.lstrip('/')}"`) — pass the full relative path including `rest/agile/1.0/...`.

### Step 3.4 — Run tests to confirm they pass

```bash
python -m pytest tests/test_sprint_autodetect.py -v 2>&1 | tail -10
```

Expected: All 4 tests `PASSED`.

### Step 3.5 — Commit

```bash
git add web/routers/sprint_routes.py tests/test_sprint_autodetect.py
git commit -m "feat: add active-sprint auto-detection and board listing endpoints"
```

---

## Task 4 — Wire JQL filter into the UI (Jira Team view)

**Files:**
- Modify: `web/static/index.html`

This is a minimal frontend change — add a JQL input + search button above the existing Jira team cards. No backend changes. No new views.

### Step 4.1 — Find the Jira team view section

```bash
grep -n "jiraTeamFilter\|fetchJiraTeam\|jiraData\|api/jira/team" \
  web/static/index.html | head -20
```

Note the line number of the Jira Team section heading (look for `"Jira Team Workload"` or similar text near line 5600).

### Step 4.2 — Add JQL filter state variables

In `index.html`, find the Alpine.js data block at the top (around line 83 where `jiraTeamFilter: ''` is defined). Add these two lines right after `jiraTeamFilter: '',`:

```javascript
jiraJqlInput: '',
jiraJqlResults: null,
jiraJqlLoading: false,
jiraJqlError: '',
```

### Step 4.3 — Add the fetch helper function

In the `methods` / functions section of the Alpine.js data object (search for `async loadJiraTeam` or any `jira` fetch function), add this new function:

```javascript
async fetchJiraJql() {
  if (!this.jiraJqlInput.trim()) return;
  this.jiraJqlLoading = true;
  this.jiraJqlError = '';
  this.jiraJqlResults = null;
  try {
    const appId = this.currentAppId || (this.applications[0]?.application_id || '');
    const url = `/api/jira/filter?jql=${encodeURIComponent(this.jiraJqlInput.trim())}&app_id=${appId}`;
    const data = await fetch(url).then(r => {
      if (!r.ok) return r.json().then(d => { throw new Error(d.detail || 'Error'); });
      return r.json();
    });
    this.jiraJqlResults = data;
  } catch(e) {
    this.jiraJqlError = e.message;
  }
  this.jiraJqlLoading = false;
},
```

### Step 4.4 — Add the JQL filter UI panel

Find the line in the Jira team view that starts with `<input x-model="jiraTeamFilter"` (around line 5601). Insert the following block **above** that `<input>` element:

```html
<!-- JQL Filter Panel -->
<div style="background:#f0f4ff;border:1px solid #c7d2fe;border-radius:10px;padding:14px 16px;margin-bottom:16px;">
  <div style="font-size:12px;font-weight:700;color:#4338ca;margin-bottom:8px;letter-spacing:.05em;">CUSTOM JQL FILTER</div>
  <div style="display:flex;gap:8px;align-items:center;">
    <input
      x-model="jiraJqlInput"
      @keydown.enter="fetchJiraJql()"
      placeholder='e.g. assignee in (alice, bob) AND sprint in openSprints()'
      style="flex:1;padding:8px 12px;border:1px solid #c7d2fe;border-radius:7px;font-size:13px;font-family:monospace;background:#fff;color:#1e1b4b;"
    />
    <button
      @click="fetchJiraJql()"
      :disabled="jiraJqlLoading || !jiraJqlInput.trim()"
      style="padding:8px 18px;background:#6366f1;color:#fff;border:none;border-radius:7px;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap;"
    >
      <span x-show="!jiraJqlLoading">Run JQL</span>
      <span x-show="jiraJqlLoading">Loading…</span>
    </button>
    <button
      x-show="jiraJqlResults"
      @click="jiraJqlResults=null; jiraJqlInput='';"
      style="padding:8px 12px;background:#e2e8f0;color:#475569;border:none;border-radius:7px;font-size:13px;cursor:pointer;"
    >Clear</button>
  </div>
  <div x-show="jiraJqlError" style="color:#dc2626;font-size:12px;margin-top:6px;" x-text="jiraJqlError"></div>
  <div x-show="jiraJqlResults" style="margin-top:10px;font-size:12px;color:#4338ca;"
       x-text="'Found ' + (jiraJqlResults?.total || 0) + ' issues across ' + (jiraJqlResults?.by_assignee?.length || 0) + ' people'"></div>
</div>

<!-- JQL Results (shown instead of regular team when active) -->
<template x-if="jiraJqlResults">
  <div>
    <template x-for="person in (jiraJqlResults.by_assignee || [])" :key="person.account_id">
      <div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px 16px;margin-bottom:10px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
          <img :src="person.avatar_url" x-show="person.avatar_url" style="width:32px;height:32px;border-radius:50%;"/>
          <div>
            <div style="font-weight:700;font-size:14px;" x-text="person.display_name"></div>
            <div style="font-size:12px;color:#64748b;" x-text="person.total + ' issues'"></div>
          </div>
        </div>
        <template x-for="issue in person.issues" :key="issue.key">
          <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-top:1px solid #f1f5f9;">
            <a :href="issue.web_url" target="_blank"
               style="font-weight:700;color:#6366f1;font-size:12px;min-width:80px;text-decoration:none;"
               x-text="issue.key"></a>
            <span style="flex:1;font-size:13px;" x-text="issue.summary"></span>
            <span style="font-size:11px;background:#f1f5f9;border-radius:5px;padding:2px 7px;color:#475569;"
                  x-text="issue.status"></span>
            <span style="font-size:11px;color:#94a3b8;" x-text="issue.priority"></span>
          </div>
        </template>
      </div>
    </template>
  </div>
</template>
```

### Step 4.5 — Add "Detect Sprint" button to sprint config section

Search for where `board_id` or sprint configuration is shown in the UI (search for `sprintConfig` or `board_id` in index.html). Near the board ID input field, add:

```html
<button
  @click="detectActiveSprint()"
  :disabled="!sprintConfig.board_id"
  style="padding:7px 14px;background:#10b981;color:#fff;border:none;border-radius:7px;font-size:12px;font-weight:600;cursor:pointer;margin-left:8px;"
>Detect Active Sprint</button>
```

And add this helper function in the Alpine.js methods block:

```javascript
async detectActiveSprint() {
  if (!this.sprintConfig?.board_id) return;
  const appId = this.currentAppId || (this.applications[0]?.application_id || '');
  try {
    const data = await fetch(
      `/api/sprint/${appId}/active-sprint?board_id=${this.sprintConfig.board_id}`
    ).then(r => r.json());
    if (data.found) {
      this.sprintConfig.sprint_id   = String(data.sprint.id);
      this.sprintConfig.sprint_name = data.sprint.name;
      this.toast('success', `Active sprint detected: ${data.sprint.name} (ID: ${data.sprint.id})`);
    } else {
      this.toast('warning', 'No active sprint found for this board');
    }
  } catch(e) {
    this.toast('error', 'Sprint detection failed: ' + e.message);
  }
},
```

### Step 4.6 — Manual smoke test

Start the server and open http://localhost:8080. Navigate to the Jira section. Verify:
- A "CUSTOM JQL FILTER" box appears above the team list
- Typing a JQL and pressing Enter (or "Run JQL") shows results or a sensible error
- The "Clear" button resets to the normal team view

### Step 4.7 — Commit

```bash
git add web/static/index.html
git commit -m "feat: add JQL filter input to Jira team view + active sprint detect button"
```

---

## Task 5 — Run full Segment 1 test suite

```bash
python -m pytest tests/test_jira_filter.py tests/test_my_work_real.py tests/test_sprint_autodetect.py -v
```

Expected output:
```
tests/test_jira_filter.py::test_filter_returns_issues_grouped_by_assignee PASSED
tests/test_jira_filter.py::test_filter_requires_jql_param PASSED
tests/test_jira_filter.py::test_filter_returns_400_when_jira_disabled PASSED
tests/test_jira_filter.py::test_filter_unassigned_issues_grouped_correctly PASSED
tests/test_jira_filter.py::test_filter_includes_web_url_for_each_issue PASSED
tests/test_my_work_real.py::test_my_work_returns_real_jira_issues PASSED
tests/test_my_work_real.py::test_my_work_returns_real_gitlab_mrs PASSED
tests/test_my_work_real.py::test_my_work_returns_empty_jira_when_disabled PASSED
tests/test_my_work_real.py::test_my_work_jira_failure_returns_empty_not_500 PASSED
tests/test_sprint_autodetect.py::test_active_sprint_found PASSED
tests/test_sprint_autodetect.py::test_no_active_sprint_returns_found_false PASSED
tests/test_sprint_autodetect.py::test_boards_endpoint_returns_list PASSED
tests/test_sprint_autodetect.py::test_active_sprint_requires_board_id PASSED

13 passed in <5s
```

### Final segment commit (tag for rollback point)

```bash
git tag segment1-complete
```

---

## Self-Review Checklist

- [x] JQL filter endpoint: covered by Task 1 (test + impl + UI)
- [x] `my_work_routes.py` real data: covered by Task 2 (full file rewrite + tests)
- [x] Sprint auto-detect: covered by Task 3 + Task 4 (boards list + active sprint + UI button)
- [x] No `MockJiraIssueORM` left in `my_work_routes.py` after Task 2
- [x] All type names consistent: `_get_sprint_cfg`, `_get_jira_cfg`, `_get_gl_configs` used in both impl and test mocks
- [x] Error handling: Jira failure → empty list + `error` key (not 500) — tested in `test_my_work_jira_failure_returns_empty_not_500`
- [x] No placeholders — every step has actual code
