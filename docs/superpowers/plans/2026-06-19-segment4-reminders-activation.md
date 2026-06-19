# Segment 4 — Activate the Reminders System

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development`.

**Goal:** Wire up the already-built reminder system (model + CRUD API + APScheduler) so it actually works, and give it a usable UI — recurring/fixed/relative reminders that fire into the Alerts bell and the SOD/EOD briefings.

**Architecture:** The backend is complete but dormant: `ReminderORM`, `web/routers/reminders.py` (full CRUD + snooze + trigger), and `services/reminder_scheduler.py` (`ReminderScheduler` with register/start/stop). Two wiring gaps: (1) the router is imported but never `include_router`-ed; (2) the scheduler is imported but never instantiated/started. The router already references `from web.app import _reminder_scheduler`, so the intended design is a module-level scheduler singleton in `web/app.py`. We add that, mount the router, start/stop in lifecycle, build a Reminders UI, and surface active reminders in SOD/EOD.

**Tech Stack:** FastAPI, SQLAlchemy/SQLite, APScheduler, Alpine.js — no new deps.

---

## File Map

| Action | File |
|--------|------|
| Modify | `web/app.py` — mount `reminders.router`, add `_reminder_scheduler` global, start/stop in lifecycle |
| Create | `tests/test_reminders_api.py` — CRUD, validation, snooze, trigger→alert (via TestClient) |
| Create | `tests/test_reminder_scheduler.py` — pure-logic units for trigger date + should-trigger |
| Modify | `web/static/index.html` — Reminders nav item + view + create modal + snooze/delete/toggle |
| Modify | `web/email_sender.py` — include active reminders in SOD/EOD (respect include_in_sod/eod) |
| Create | `tests/test_reminders_in_briefing.py` — SOD/EOD include reminder titles |

---

## Task 1 — Activate the backend (mount router + scheduler singleton)

**Files:**
- Modify: `web/app.py`
- Create: `tests/test_reminders_api.py`

### Step 1.1 — Write failing tests

Create `tests/test_reminders_api.py`:

```python
"""End-to-end tests for the reminders API (router must be mounted)."""
import pytest
from fastapi.testclient import TestClient
from web.app import app

client = TestClient(app)


@pytest.fixture
def cleanup_reminders():
    """Delete any reminders created during a test."""
    created = []
    yield created
    for rid in created:
        client.delete(f"/api/reminders/{rid}")


def test_list_reminders_endpoint_is_mounted():
    """GET /api/reminders must return 200 (router mounted), not 404."""
    resp = client.get("/api/reminders")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_fixed_time_reminder(cleanup_reminders):
    resp = client.post("/api/reminders", json={
        "title": "Standup",
        "trigger_type": "fixed_time",
        "trigger_value": "09:30",
        "priority": "medium",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Standup"
    assert data["trigger_value"] == "09:30"
    assert data["is_active"] is True
    cleanup_reminders.append(data["reminder_id"])


def test_create_relative_interval_reminder(cleanup_reminders):
    resp = client.post("/api/reminders", json={
        "title": "Day before deadline",
        "trigger_type": "relative_interval",
        "trigger_value": "-1d",
        "due_date": "2026-07-01",
        "priority": "high",
    })
    assert resp.status_code == 201
    cleanup_reminders.append(resp.json()["reminder_id"])


def test_create_rejects_bad_fixed_time():
    resp = client.post("/api/reminders", json={
        "title": "Bad", "trigger_type": "fixed_time", "trigger_value": "99:99",
    })
    assert resp.status_code == 400


def test_create_rejects_bad_interval():
    resp = client.post("/api/reminders", json={
        "title": "Bad", "trigger_type": "relative_interval", "trigger_value": "soon",
    })
    assert resp.status_code == 400


def test_get_patch_delete_lifecycle(cleanup_reminders):
    # create
    rid = client.post("/api/reminders", json={
        "title": "Temp", "trigger_type": "fixed_time", "trigger_value": "10:00",
    }).json()["reminder_id"]

    # get
    assert client.get(f"/api/reminders/{rid}").status_code == 200

    # patch
    patched = client.patch(f"/api/reminders/{rid}", json={"title": "Renamed"})
    assert patched.status_code == 200
    assert patched.json()["title"] == "Renamed"

    # delete
    assert client.delete(f"/api/reminders/{rid}").status_code == 204
    assert client.get(f"/api/reminders/{rid}").status_code == 404


def test_snooze_sets_snooze_until(cleanup_reminders):
    rid = client.post("/api/reminders", json={
        "title": "Snoozable", "trigger_type": "fixed_time", "trigger_value": "11:00",
    }).json()["reminder_id"]
    cleanup_reminders.append(rid)

    resp = client.post(f"/api/reminders/{rid}/snooze?minutes=30")
    assert resp.status_code == 200
    assert resp.json()["snooze_until"] is not None


def test_manual_trigger_creates_alert(cleanup_reminders):
    rid = client.post("/api/reminders", json={
        "title": "Fire me", "trigger_type": "fixed_time", "trigger_value": "12:00",
        "priority": "high",
    }).json()["reminder_id"]
    cleanup_reminders.append(rid)

    before = len(client.get("/api/alerts").json())
    resp = client.post(f"/api/reminders/{rid}/trigger")
    assert resp.status_code == 200
    after = len(client.get("/api/alerts").json())
    assert after == before + 1
```

### Step 1.2 — Run, confirm FAIL
```bash
cd /Users/puneetsharma/Workspace/projects/ai-lab/command-center
python3 -m pytest tests/test_reminders_api.py -v 2>&1 | tail -15
```
Expected: `test_list_reminders_endpoint_is_mounted` fails with 404 (router not mounted).

### Step 1.3 — Mount the router in `web/app.py`

After the line `app.include_router(setup_router)` (around line 113), add:
```python
app.include_router(reminders.router)
```

### Step 1.4 — Add the scheduler singleton + lifecycle in `web/app.py`

The router does `from web.app import _reminder_scheduler`, so define it at module level. After the `app = FastAPI(...)` line (around line 44), add:
```python
_reminder_scheduler = None
```

In `on_startup()` (around line 119), after `start_backup_scheduler()`, add:
```python
    _start_reminder_scheduler()
```

Add this new function near `_start_scheduler()`:
```python
def _start_reminder_scheduler():
    global _reminder_scheduler
    try:
        _reminder_scheduler = create_scheduler_job()
        _reminder_scheduler.start()
    except Exception as exc:
        import logging
        logging.getLogger("execos").warning("Reminder scheduler failed to start: %s", exc)
        _reminder_scheduler = None
```

In `on_shutdown()` (around line 143), add:
```python
    global _reminder_scheduler
    if _reminder_scheduler:
        try:
            _reminder_scheduler.stop()
        except Exception:
            pass
```

### Step 1.5 — Run tests, confirm all pass
```bash
python3 -m pytest tests/test_reminders_api.py -v 2>&1 | tail -15
```
Expected: all pass. (The scheduler singleton is created on FastAPI startup; TestClient triggers startup. CRUD calls to `_register_reminder_with_scheduler` are wrapped in try/except so they never break the request.)

### Step 1.6 — Confirm no regressions
```bash
python3 -m pytest tests/ -v 2>&1 | tail -8
```

### Step 1.7 — Commit
```bash
git add web/app.py tests/test_reminders_api.py
git commit -m "$(cat <<'EOF'
feat: activate reminders — mount router and start background scheduler singleton

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2 — Lock in the scheduler trigger logic with unit tests

**Files:**
- Create: `tests/test_reminder_scheduler.py`

> No production changes — this pins the existing pure logic so future edits can't silently break relative-interval math or snooze/dedup guards.

### Step 2.1 — Write the tests

Create `tests/test_reminder_scheduler.py`:

```python
"""Pure-logic unit tests for ReminderScheduler (no APScheduler start)."""
from datetime import date, datetime, timedelta
from types import SimpleNamespace

from services.reminder_scheduler import ReminderScheduler


def _sched():
    return ReminderScheduler()


def test_calculate_trigger_date_minus_one_day():
    s = _sched()
    r = SimpleNamespace(due_date=date(2026, 7, 1), trigger_value="-1d")
    assert s._calculate_trigger_date(r) == date(2026, 6, 30)


def test_calculate_trigger_date_plus_one_week():
    s = _sched()
    r = SimpleNamespace(due_date=date(2026, 7, 1), trigger_value="+1w")
    assert s._calculate_trigger_date(r) == date(2026, 7, 8)


def test_calculate_trigger_date_one_month():
    s = _sched()
    r = SimpleNamespace(due_date=date(2026, 7, 1), trigger_value="1m")
    assert s._calculate_trigger_date(r) == date(2026, 8, 1)


def test_calculate_trigger_date_missing_due_date_returns_today():
    s = _sched()
    r = SimpleNamespace(due_date=None, trigger_value="-1d")
    assert s._calculate_trigger_date(r) == date.today()


def test_priority_to_severity_mapping():
    s = _sched()
    assert s._priority_to_severity("low") == "info"
    assert s._priority_to_severity("high") == "warning"
    assert s._priority_to_severity("critical") == "critical"
    assert s._priority_to_severity("unknown") == "info"


def test_should_trigger_blocked_by_snooze():
    s = _sched()
    r = SimpleNamespace(
        snooze_until=datetime.utcnow() + timedelta(minutes=30),
        last_triggered=None, trigger_type="fixed_time",
    )
    assert s._should_trigger(r) is False


def test_should_trigger_blocked_by_recent_fire():
    s = _sched()
    r = SimpleNamespace(
        snooze_until=None,
        last_triggered=datetime.utcnow() - timedelta(seconds=60),  # < 5 min
        trigger_type="fixed_time",
    )
    assert s._should_trigger(r) is False


def test_should_trigger_fixed_time_passes_when_clear():
    s = _sched()
    r = SimpleNamespace(snooze_until=None, last_triggered=None, trigger_type="fixed_time")
    assert s._should_trigger(r) is True


def test_should_trigger_relative_true_when_target_reached():
    s = _sched()
    r = SimpleNamespace(
        snooze_until=None, last_triggered=None, trigger_type="relative_interval",
        due_date=date.today(), trigger_value="-1d",  # target = yesterday → now >= target
    )
    assert s._should_trigger(r) is True
```

### Step 2.2 — Run, confirm all pass
```bash
python3 -m pytest tests/test_reminder_scheduler.py -v 2>&1 | tail -15
```

### Step 2.3 — Commit
```bash
git add tests/test_reminder_scheduler.py
git commit -m "$(cat <<'EOF'
test: lock in reminder scheduler trigger-date and should-trigger logic

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3 — Reminders UI view

**Files:**
- Modify: `web/static/index.html`

### Step 3.1 — Find insertion points

```bash
grep -n "nav('alerts')\|nav('planner')\|view==='alerts'\|sidebarOpen.dash" web/static/index.html | head
grep -n "allMrsData: null\|loadSetupStatus()\|async loadAllMrs" web/static/index.html | head
grep -n "navCls\|pageTitle\|pageSubtitle\|x-show=\"view==='dashboard'\"" web/static/index.html | head
```

Read the relevant ~40-line sections to learn: the nav-item markup, where Alpine state lives, the `nav()`/`navCls()` helpers, how `pageTitle`/`pageSubtitle` are set, and the modal pattern (reuse `.modal-backdrop`/`.modal-box` and `addToast`).

### Step 3.2 — Add nav item

In the DASHBOARD nav group (the `x-show="sidebarOpen.dash"` block), after the Alerts nav item, add:
```html
    <div @click="nav('reminders')" :class="navCls('reminders')"><span class="nav-icon">⏰</span><span>Reminders</span></div>
```

### Step 3.3 — Register the view as routable

Find the big `x-show="[...].includes(view)"` array on the main content wrapper (around line 2658) and add `'reminders'` to that list so the content container renders for the new view.

Also find where `pageTitle`/`pageSubtitle` are computed (a map or switch keyed by `view`). Add a `reminders` entry: title `Reminders`, subtitle `Scheduled nudges into your alerts and briefings`.

### Step 3.4 — Add Alpine state + methods

Near `allMrsData: null,` add:
```javascript
reminders: [],
remindersLoading: false,
reminderModal: { open: false, data: {} },
```

Near `async loadAllMrs(...)` add:
```javascript
async loadReminders() {
  this.remindersLoading = true;
  try { this.reminders = await fetch('/api/reminders').then(r => r.json()); }
  catch(e) { this.addToast('Failed to load reminders: ' + e.message, 'error'); }
  this.remindersLoading = false;
},
openReminderModal() {
  this.reminderModal = { open: true, data: {
    title: '', description: '', trigger_type: 'fixed_time',
    trigger_value: '09:00', due_date: '', priority: 'medium',
    include_in_sod: true, include_in_eod: true,
  }};
},
async saveReminder() {
  const d = this.reminderModal.data;
  if (!d.title || !d.title.trim()) { this.addToast('Title is required', 'warning'); return; }
  const body = {
    title: d.title.trim(), description: d.description || '',
    reminder_type: 'independent', trigger_type: d.trigger_type,
    trigger_value: d.trigger_value, priority: d.priority,
    include_in_sod: !!d.include_in_sod, include_in_eod: !!d.include_in_eod,
  };
  if (d.trigger_type === 'relative_interval') body.due_date = d.due_date || null;
  try {
    const r = await fetch('/api/reminders', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Error'); }
    this.reminderModal.open = false;
    this.addToast('Reminder created', 'success');
    await this.loadReminders();
  } catch(e) { this.addToast('Failed: ' + e.message, 'error'); }
},
async toggleReminder(rid, active) {
  try { await fetch(`/api/reminders/${rid}`, {method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify({is_active: active})}); await this.loadReminders(); }
  catch(e) { this.addToast('Failed: ' + e.message, 'error'); }
},
async snoozeReminder(rid) {
  try { await fetch(`/api/reminders/${rid}/snooze?minutes=60`, {method:'POST'}); this.addToast('Snoozed 1 hour', 'info'); await this.loadReminders(); }
  catch(e) { this.addToast('Failed: ' + e.message, 'error'); }
},
async deleteReminder(rid) {
  if (!confirm('Delete this reminder?')) return;
  try { await fetch(`/api/reminders/${rid}`, {method:'DELETE'}); this.addToast('Reminder deleted', 'success'); await this.loadReminders(); }
  catch(e) { this.addToast('Failed: ' + e.message, 'error'); }
},
async testFireReminder(rid) {
  try { await fetch(`/api/reminders/${rid}/trigger`, {method:'POST'}); this.addToast('Reminder fired — check Alerts', 'reminder'); await this.loadAlerts?.(); }
  catch(e) { this.addToast('Failed: ' + e.message, 'error'); }
},
```

### Step 3.5 — Auto-load on nav

In `nav()`, add alongside the other view-load guards:
```javascript
if (id === 'reminders') this.loadReminders();
```

### Step 3.6 — Add the view HTML

Inside the main content wrapper (sibling of the other `x-show="view==='...'"` blocks), add a `reminders` view. Use existing tokens/classes (`.card`, `.btn-primary`, `.btn-secondary`, `.chip-*`, `.toggle-btn`). It must:
- A header row with a `+ New Reminder` `.btn-primary` calling `openReminderModal()`
- An empty state when `reminders.length === 0`
- A list (`<template x-for="r in reminders" :key="r.reminder_id">`) showing: title, description, a chip for `trigger_type` + `trigger_value`, a priority chip, an Active toggle, and buttons: Snooze, Test, Delete
- The create modal (reuse `.modal-backdrop`/`.modal-box`/`.modal-header`/`.modal-body`/`.modal-footer`) with: title input, description textarea, a trigger_type `<select>` (`fixed_time` / `relative_interval`), a trigger_value input (label/placeholder switches: `HH:MM` vs `-1d` / `2h` / `+1w` / `1m`), a due_date date input shown only when `trigger_type === 'relative_interval'`, a priority select, and two checkboxes for include in SOD / EOD. Footer: Cancel (`.btn-secondary`, sets `reminderModal.open=false`) + Create (`.btn-primary`, calls `saveReminder()`).

Keep markup style consistent with the existing views (inline styles using `var(--...)` tokens are fine — match neighbours).

### Step 3.7 — Verify and commit
```bash
grep -c "loadReminders\|reminderModal\|saveReminder\|nav('reminders')" web/static/index.html
git add web/static/index.html
git commit -m "$(cat <<'EOF'
feat: add Reminders UI — list, create (fixed/relative), snooze, test-fire, delete

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4 — Surface active reminders in SOD/EOD briefings

**Files:**
- Modify: `web/email_sender.py`
- Create: `tests/test_reminders_in_briefing.py`

> Ties the existing `include_in_sod` / `include_in_eod` flags to real behaviour.

### Step 4.1 — Write failing tests

Create `tests/test_reminders_in_briefing.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session


def _reminder(title="Submit timesheet", sod=True, eod=False):
    r = MagicMock()
    r.title = title
    r.description = ""
    r.priority = "medium"
    r.trigger_type = "fixed_time"
    r.trigger_value = "09:00"
    r.include_in_sod = sod
    r.include_in_eod = eod
    r.is_active = True
    return r


@patch("web.email_sender._get_active_reminders")
@patch("web.email_sender._fetch_open_mrs_for_email")
@patch("web.email_sender._fetch_my_jira_issues")
def test_sod_includes_reminders_flagged_for_sod(mock_jira, mock_mrs, mock_rem):
    mock_jira.return_value = []
    mock_mrs.return_value = []
    mock_rem.return_value = [_reminder("Submit timesheet", sod=True)]

    from web.email_sender import build_sod_html
    db = MagicMock(spec=Session)
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.filter.return_value.all.return_value = []
    db.query.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.all.return_value = []

    html = build_sod_html(db)
    assert "Submit timesheet" in html


@patch("web.email_sender._get_active_reminders")
@patch("web.email_sender._fetch_my_jira_issues")
def test_eod_excludes_sod_only_reminders(mock_jira, mock_rem):
    mock_jira.return_value = []
    mock_rem.return_value = [_reminder("Morning only", sod=True, eod=False)]

    from web.email_sender import build_eod_html
    db = MagicMock(spec=Session)
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.filter.return_value.all.return_value = []
    db.query.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.all.return_value = []

    html = build_eod_html(db)
    assert "Morning only" not in html
```

### Step 4.2 — Run, confirm FAIL
```bash
python3 -m pytest tests/test_reminders_in_briefing.py -v 2>&1 | tail -10
```

### Step 4.3 — Add helper + sections in `web/email_sender.py`

Add `ReminderORM` to the `db.models` import. Add a helper near the other `_fetch_*` helpers:
```python
def _get_active_reminders(db) -> list:
    try:
        return db.query(ReminderORM).filter(ReminderORM.is_active == True).all()
    except Exception as exc:
        _email_log.warning("Reminder fetch for email failed: %s", exc)
        return []
```

In `build_sod_html`, after the existing fetches, add:
```python
    sod_reminders = [r for r in _get_active_reminders(db) if r.include_in_sod]
```
Build a section (reuse the same table style used for the Jira/MR sections) titled `Reminders ({len})` listing each reminder's title (HTML-escaped with `_he`) + its `trigger_value`. Inject it into the SOD body before `</body>` / before the `_wrap` call (match how the Jira/MR sections are injected). Only render when the list is non-empty.

In `build_eod_html`, do the same with `include_in_eod`:
```python
    eod_reminders = [r for r in _get_active_reminders(db) if r.include_in_eod]
```

### Step 4.4 — Run tests, confirm pass
```bash
python3 -m pytest tests/test_reminders_in_briefing.py tests/test_sod_eod_enriched.py -v 2>&1 | tail -12
```

### Step 4.5 — Commit
```bash
git add web/email_sender.py tests/test_reminders_in_briefing.py
git commit -m "$(cat <<'EOF'
feat: include active reminders in SOD/EOD briefings per include_in_sod/eod flags

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5 — Full suite, live run, tag

### Step 5.1 — Run the whole test suite
```bash
cd /Users/puneetsharma/Workspace/projects/ai-lab/command-center
python3 -m pytest tests/ -v 2>&1 | tail -25
```
Expected: all pass.

### Step 5.2 — Live smoke test
```bash
lsof -ti:8080 | xargs kill -9 2>/dev/null; sleep 1
python3 start.py &>/tmp/execos.log &
sleep 4
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/reminders ; echo " <- GET /api/reminders (expect 200)"
# create + trigger
RID=$(curl -s -X POST http://localhost:8080/api/reminders -H 'Content-Type: application/json' \
  -d '{"title":"Smoke test","trigger_type":"fixed_time","trigger_value":"09:00"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['reminder_id'])")
curl -s -X POST http://localhost:8080/api/reminders/$RID/trigger >/dev/null && echo "triggered $RID"
grep -i "reminder scheduler started" /tmp/execos.log && echo "scheduler started ✓"
curl -s -X DELETE http://localhost:8080/api/reminders/$RID >/dev/null && echo "cleaned up"
```

### Step 5.3 — Tag
```bash
git tag segment4-complete
git log --oneline -8
```

---

## Self-Review Checklist

- [x] `reminders.router` mounted in `web/app.py`
- [x] `_reminder_scheduler` module global created, started on startup, stopped on shutdown
- [x] CRUD/snooze/trigger reachable; trigger creates an Alert
- [x] Scheduler trigger-date + should-trigger logic covered by unit tests
- [x] Reminders UI: nav + view + create modal (fixed & relative) + snooze/test/delete/toggle
- [x] Active reminders appear in SOD/EOD per include flags (HTML-escaped)
- [x] Full suite green; live run confirms scheduler starts and endpoint responds
- [x] Tagged `segment4-complete`
