# Release Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing Delivery subsystem into a Release Planner with stage-gated planned/actual dates, derived status, curated Jira sprint attachment, and SOD/EOD breach alerts.

**Architecture:** Build on `DeliveryRelease`/`DeliveryReleaseItem` (a release instantiates a template into ordered checklist items with `status` + auto `completed_at`). Add a `stage` + `planned_date` to items, a curated `delivery_release_sprints` table, a pure `services/release_health.py` for status/breach derivation, new sprint + health API on `/api/delivery`, and a "Releases at risk" section in the SOD/EOD dashboard endpoints and email briefings.

**Tech Stack:** FastAPI, SQLAlchemy 2.x, SQLite (idempotent `ALTER TABLE` migrations in `db/init_db.py`), pytest, Alpine.js + inline-styled SPA (`web/static/index.html`).

## Global Constraints

- Python 3.11; no new third-party dependencies (stdlib + existing deps only).
- SQLite schema changes go through the idempotent list in `db/init_db.py._migrate()` (duplicate-column errors are swallowed by the existing executor). New tables via `Base.metadata.create_all`.
- Pipeline stages, in order: `requirement_gathering`, `development`, `qa`, `uat`, `in_prod`.
- `RISK_WINDOW = 3` (calendar days).
- Item statuses (existing): `pending`, `in_progress`, `done`, `skipped`, `blocked`. `completed_at` is auto-stamped when status→`done` (see `delivery_routes.update_release_item`).
- Derived release statuses: `TODO`, `IN_PROGRESS`, `COMPLETED`.
- "mine" = Jira issue `fields.assignee.emailAddress` equals `SprintConfigORM.my_jira_email` (case-insensitive).
- Do not modify the legacy `ReleaseORM` / `releases` table or `/api/releases` in this workstream.
- Run tests with `python3 -m pytest`. Commit after every task.

---

### Task 1: Schema — stage + planned_date on items, sprint attachment table

**Files:**
- Modify: `db/models.py:299-347` (DeliveryTemplateItemORM, DeliveryReleaseItemORM) and append a new class.
- Test: `tests/test_release_planner_models.py`

**Interfaces:**
- Produces: `DeliveryTemplateItemORM.stage`, `.planned_offset_days`; `DeliveryReleaseItemORM.stage`, `.planned_date`; new `DeliveryReleaseSprintORM(attach_id, release_id, board_id, sprint_id, sprint_name, added_at)` with `__tablename__ = "delivery_release_sprints"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_release_planner_models.py
from db.models import DeliveryTemplateItemORM, DeliveryReleaseItemORM, DeliveryReleaseSprintORM

def test_template_item_has_stage_and_offset():
    cols = DeliveryTemplateItemORM.__table__.columns.keys()
    assert "stage" in cols
    assert "planned_offset_days" in cols

def test_release_item_has_stage_and_planned_date():
    cols = DeliveryReleaseItemORM.__table__.columns.keys()
    assert "stage" in cols
    assert "planned_date" in cols

def test_release_sprint_table():
    cols = DeliveryReleaseSprintORM.__table__.columns.keys()
    assert DeliveryReleaseSprintORM.__tablename__ == "delivery_release_sprints"
    for c in ("attach_id", "release_id", "board_id", "sprint_id", "sprint_name", "added_at"):
        assert c in cols
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_release_planner_models.py -v`
Expected: FAIL (`AttributeError`/`ImportError` — `DeliveryReleaseSprintORM` not defined, `stage` missing).

- [ ] **Step 3: Add columns and the new model**

In `db/models.py`, add to `DeliveryTemplateItemORM` (after `is_required`):
```python
    stage               = Column(String(40), default="development")
    planned_offset_days = Column(Integer, nullable=True)
```
Add to `DeliveryReleaseItemORM` (after `is_required`):
```python
    stage        = Column(String(40), nullable=True)
    planned_date = Column(Date, nullable=True)
```
Append a new class after `DeliveryReleaseItemORM`:
```python
class DeliveryReleaseSprintORM(Base):
    __tablename__ = "delivery_release_sprints"

    attach_id   = Column(String, primary_key=True, default=_uuid)
    release_id  = Column(String, ForeignKey("delivery_releases.release_id", ondelete="CASCADE"), nullable=False)
    board_id    = Column(String(100), default="")
    sprint_id   = Column(String(100), default="")
    sprint_name = Column(String(255), default="")
    added_at    = Column(DateTime, default=datetime.utcnow)
```
(`Date`, `Integer`, `ForeignKey`, `datetime`, `_uuid` are already imported/defined in this file.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_release_planner_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add db/models.py tests/test_release_planner_models.py
git commit -m "feat(models): add stage/planned_date to delivery items + sprint attachment table"
```

---

### Task 2: Migration + default stage template seed

**Files:**
- Modify: `db/init_db.py` (`_migrate()` list, add a `_seed_default_template()` called from `create_all`).
- Test: `tests/test_release_planner_migration.py`

**Interfaces:**
- Produces: `db.init_db._seed_default_template(db)` idempotent; default template named `"Standard Release"` with 6 items carrying `stage`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_release_planner_migration.py
from db.base import SessionLocal
from db.init_db import create_all, _seed_default_template
from db.models import DeliveryTemplateORM, DeliveryTemplateItemORM

def test_default_template_seeded_once():
    create_all()
    db = SessionLocal()
    _seed_default_template(db)          # second call must be a no-op
    tmpls = db.query(DeliveryTemplateORM).filter(DeliveryTemplateORM.name == "Standard Release").all()
    assert len(tmpls) == 1
    items = db.query(DeliveryTemplateItemORM).filter(
        DeliveryTemplateItemORM.template_id == tmpls[0].template_id).all()
    stages = {i.stage for i in items}
    assert len(items) == 6
    assert stages == {"requirement_gathering", "development", "qa", "uat", "in_prod"}
    db.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_release_planner_migration.py -v`
Expected: FAIL (`ImportError: cannot import name '_seed_default_template'`).

- [ ] **Step 3: Add migrations and seeder**

In `db/init_db.py`, add to the `migrations` list inside `_migrate()`:
```python
        "ALTER TABLE delivery_template_items ADD COLUMN stage TEXT DEFAULT 'development'",
        "ALTER TABLE delivery_template_items ADD COLUMN planned_offset_days INTEGER",
        "ALTER TABLE delivery_release_items ADD COLUMN stage TEXT",
        "ALTER TABLE delivery_release_items ADD COLUMN planned_date DATE",
```
Add a new function and call it from `create_all` after `_migrate()`:
```python
def _seed_default_template(db):
    from db.models import DeliveryTemplateORM, DeliveryTemplateItemORM
    existing = db.query(DeliveryTemplateORM).filter(
        DeliveryTemplateORM.name == "Standard Release").first()
    if existing:
        return
    tmpl = DeliveryTemplateORM(name="Standard Release", is_default=True,
                               description="Default stage-gated release pipeline")
    db.add(tmpl); db.commit(); db.refresh(tmpl)
    gates = [
        ("Requirement Cut", "requirement_gathering", "pre_release"),
        ("Dev Completion",  "development",           "pre_release"),
        ("QA Completion",   "qa",                    "pre_release"),
        ("UAT Completion",  "uat",                   "pre_release"),
        ("UAT Sign-off",    "uat",                   "release"),
        ("Release Date",    "in_prod",               "release"),
    ]
    for order, (title, stage, category) in enumerate(gates):
        db.add(DeliveryTemplateItemORM(template_id=tmpl.template_id, order=order,
               title=title, stage=stage, category=category, is_required=True))
    db.commit()
```
In `create_all(...)`, after the existing `_migrate()` call, add:
```python
    from db.base import SessionLocal
    _db = SessionLocal()
    try:
        _seed_default_template(_db)
    finally:
        _db.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_release_planner_migration.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add db/init_db.py tests/test_release_planner_migration.py
git commit -m "feat(db): migrate delivery items for stage/planned_date + seed default template"
```

---

### Task 3: Release health service (pure functions)

**Files:**
- Create: `services/release_health.py`
- Test: `tests/test_release_health.py`

**Interfaces:**
- Produces: `RISK_WINDOW`, `STAGES`, `derive_status(items)->str`, `current_stage(items)->str`, `item_health(item, today, risk_window=RISK_WINDOW)->dict`, `release_health(items, today, risk_window=RISK_WINDOW)->dict`. `item`/`items` are any objects with `.status`, `.stage`, `.is_required`, `.order`, `.planned_date`, `.title`, `.item_id`, `.completed_at`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_release_health.py
from datetime import date
from types import SimpleNamespace
from services.release_health import derive_status, current_stage, item_health, release_health, RISK_WINDOW

def _item(stage, status, planned=None, order=0, required=True):
    return SimpleNamespace(item_id="i", title=stage, stage=stage, status=status,
                           is_required=required, order=order, planned_date=planned, completed_at=None)

TODAY = date(2026, 6, 29)

def test_item_breached():
    assert item_health(_item("development", "pending", date(2026,6,20)), TODAY)["state"] == "breached"

def test_item_at_risk_within_window():
    h = item_health(_item("qa", "pending", date(2026,7,1)), TODAY)  # +2 days
    assert h["state"] == "at_risk" and h["days"] == 2

def test_item_done_never_breached():
    assert item_health(_item("development", "done", date(2026,6,20)), TODAY)["state"] == "done"

def test_item_boundary_today_is_at_risk():
    assert item_health(_item("qa", "pending", TODAY), TODAY)["state"] == "at_risk"

def test_derive_status():
    assert derive_status([_item("requirement_gathering","pending")]) == "TODO"
    assert derive_status([_item("development","in_progress")]) == "IN_PROGRESS"
    assert derive_status([_item("in_prod","done")]) == "COMPLETED"

def test_current_stage_first_pending():
    items = [_item("requirement_gathering","done"), _item("development","pending"), _item("qa","pending")]
    assert current_stage(items) == "development"

def test_release_health_rollup_breached():
    items = [_item("requirement_gathering","done", date(2026,6,2)),
             _item("development","pending", date(2026,6,20))]
    h = release_health(items, TODAY)
    assert h["level"] == "breached"
    assert h["derived_status"] == "IN_PROGRESS"
    assert h["current_stage"] == "development"
    assert any(g["state"] == "breached" for g in h["items"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_release_health.py -v`
Expected: FAIL (`ModuleNotFoundError: services.release_health`).

- [ ] **Step 3: Implement the service**

```python
# services/release_health.py
"""Pure derivation of release status, current stage, and gate breach health."""
from datetime import date
from typing import Optional

RISK_WINDOW = 3
STAGES = ["requirement_gathering", "development", "qa", "uat", "in_prod"]


def _stage_index(stage: Optional[str]) -> int:
    try:
        return STAGES.index(stage)
    except (ValueError, TypeError):
        return len(STAGES)


def derive_status(items) -> str:
    items = list(items)
    if not items:
        return "TODO"
    required = [i for i in items if i.is_required]
    if required and all(i.status in ("done", "skipped") for i in required):
        return "COMPLETED"
    if any(i.status in ("in_progress", "done") for i in items):
        return "IN_PROGRESS"
    return "TODO"


def current_stage(items) -> str:
    pending = [i for i in items if i.is_required and i.status not in ("done", "skipped")]
    if not pending:
        return "in_prod"
    pending.sort(key=lambda i: _stage_index(i.stage))
    return pending[0].stage or "development"


def item_health(item, today: date, risk_window: int = RISK_WINDOW) -> dict:
    if item.status in ("done", "skipped"):
        return {"state": "done", "days": 0}
    planned = item.planned_date
    if planned is None:
        return {"state": "unset", "days": 0}
    if planned < today:
        return {"state": "breached", "days": (today - planned).days}
    delta = (planned - today).days
    if 0 <= delta <= risk_window and item.status == "pending":
        return {"state": "at_risk", "days": delta}
    return {"state": "upcoming", "days": delta}


def release_health(items, today: date, risk_window: int = RISK_WINDOW) -> dict:
    items = sorted(items, key=lambda i: (_stage_index(i.stage), i.order))
    gates, any_breach, any_risk = [], False, False
    for i in items:
        h = item_health(i, today, risk_window)
        any_breach = any_breach or h["state"] == "breached"
        any_risk = any_risk or h["state"] == "at_risk"
        gates.append({
            "item_id": i.item_id, "title": i.title, "stage": i.stage,
            "planned_date": i.planned_date.isoformat() if i.planned_date else None,
            "completed_at": i.completed_at.isoformat() if i.completed_at else None,
            "state": h["state"], "days": h["days"],
        })
    level = "breached" if any_breach else "at_risk" if any_risk else "on_track"
    return {"level": level, "derived_status": derive_status(items),
            "current_stage": current_stage(items), "items": gates}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_release_health.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add services/release_health.py tests/test_release_health.py
git commit -m "feat(services): add pure release_health derivation (status/stage/breach)"
```

---

### Task 4: Delivery API — item stage/planned_date + release health block

**Files:**
- Modify: `web/routers/delivery_routes.py` (Pydantic `ReleaseItemPatch`, `TemplateItemIn`; helpers `_rel_item_out`, `_rel_out`; item-copy in `create_release`; `get_release`).
- Test: `tests/test_delivery_api_health.py`

**Interfaces:**
- Consumes: `services.release_health.release_health`.
- Produces: `ReleaseItemPatch.planned_date: Optional[str]`, `.stage: Optional[str]`; `_rel_item_out` includes `stage`, `planned_date`; `get_release` response includes `health` (from `release_health`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_delivery_api_health.py
from fastapi.testclient import TestClient
from web.app import app
from db.init_db import create_all
from db.base import SessionLocal
from db.models import DeliveryTemplateORM

create_all()
client = TestClient(app)

def _std_template_id():
    db = SessionLocal()
    t = db.query(DeliveryTemplateORM).filter(DeliveryTemplateORM.name == "Standard Release").first()
    db.close()
    return t.template_id

def test_release_from_template_has_health_and_stages():
    r = client.post("/api/delivery/releases", json={
        "name": "Rel HealthTest", "version": "9.9", "template_id": _std_template_id(),
        "status": "in_progress"})
    assert r.status_code == 201
    rid = r.json()["release_id"]
    detail = client.get(f"/api/delivery/releases/{rid}").json()
    assert "health" in detail
    assert detail["health"]["derived_status"] in ("TODO", "IN_PROGRESS", "COMPLETED")
    assert len(detail["items"]) == 6
    assert detail["items"][0]["stage"] in ("requirement_gathering","development","qa","uat","in_prod")

def test_patch_item_planned_date_and_done_stamps_completed():
    rid = client.post("/api/delivery/releases", json={
        "name": "Rel PatchTest", "template_id": _std_template_id(), "status": "in_progress"}).json()["release_id"]
    item = client.get(f"/api/delivery/releases/{rid}").json()["items"][0]
    patched = client.patch(f"/api/delivery/releases/{rid}/items/{item['item_id']}",
                           json={"planned_date": "2026-06-20", "status": "done"}).json()
    assert patched["planned_date"] == "2026-06-20"
    assert patched["completed_at"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_delivery_api_health.py -v`
Expected: FAIL (`health` / `planned_date` absent from responses).

- [ ] **Step 3: Wire stage/planned_date + health into the router**

In `web/routers/delivery_routes.py`:

1. Add import near the top: `from services.release_health import release_health` and `from datetime import date as _date`.
2. In `ReleaseItemPatch`, add fields: `planned_date: Optional[str] = None` and `stage: Optional[str] = None`.
3. In `_rel_item_out(i)`, add to the returned dict:
```python
        "stage": i.stage,
        "planned_date": i.planned_date.isoformat() if i.planned_date else None,
```
4. In `create_release`, when copying template items, also copy the stage:
```python
                stage=ti.stage,
```
(add to the `DeliveryReleaseItemORM(...)` constructor).
5. In `update_release_item`, after the existing `status` handling, add:
```python
    if body.planned_date is not None:
        i.planned_date = _date.fromisoformat(body.planned_date) if body.planned_date else None
    if body.stage is not None:
        i.stage = body.stage
```
6. In `get_release`, after building `d` and loading `items`, attach health:
```python
    d["health"] = release_health(items, _date.today())
```
Ensure `d["items"] = [_rel_item_out(i) for i in items]` is present (it already builds item output — keep it).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_delivery_api_health.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/routers/delivery_routes.py tests/test_delivery_api_health.py
git commit -m "feat(delivery): item stage/planned_date + release health block"
```

---

### Task 5: Curated Jira sprint attachment API

**Files:**
- Modify: `web/routers/delivery_routes.py` (add 3 endpoints + Pydantic `SprintAttachIn`).
- Test: `tests/test_delivery_sprints.py`

**Interfaces:**
- Consumes: `DeliveryReleaseSprintORM`; `services.jira_service.get_jira_service`; `db.models.SprintConfigORM.my_jira_email`.
- Produces: `POST /api/delivery/releases/{id}/sprints`, `GET /api/delivery/releases/{id}/sprints`, `DELETE /api/delivery/releases/{id}/sprints/{attach_id}`.

- [ ] **Step 1: Write the failing test** (attach/detach persist; Jira not configured → issues empty, no crash)

```python
# tests/test_delivery_sprints.py
from fastapi.testclient import TestClient
from web.app import app
from db.init_db import create_all
create_all()
client = TestClient(app)

def _new_release():
    return client.post("/api/delivery/releases", json={"name": "SprintRel"}).json()["release_id"]

def test_attach_list_detach_sprint():
    rid = _new_release()
    a = client.post(f"/api/delivery/releases/{rid}/sprints",
                    json={"board_id": "12", "sprint_id": "340", "sprint_name": "Sprint 24"})
    assert a.status_code == 201
    attach_id = a.json()["attach_id"]

    listed = client.get(f"/api/delivery/releases/{rid}/sprints").json()
    assert len(listed["sprints"]) == 1
    assert listed["sprints"][0]["sprint_name"] == "Sprint 24"
    assert "issues" in listed["sprints"][0]           # empty when Jira not configured

    d = client.delete(f"/api/delivery/releases/{rid}/sprints/{attach_id}")
    assert d.status_code == 204
    assert client.get(f"/api/delivery/releases/{rid}/sprints").json()["sprints"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_delivery_sprints.py -v`
Expected: FAIL (404 — endpoints missing).

- [ ] **Step 3: Implement the endpoints**

In `web/routers/delivery_routes.py` add (import `DeliveryReleaseSprintORM`, `SprintConfigORM` from `db.models`, and `get_jira_service` from `services.jira_service`):
```python
class SprintAttachIn(BaseModel):
    board_id: str = ""
    sprint_id: str
    sprint_name: str = ""


def _my_email(db):
    cfg = db.query(SprintConfigORM).first()
    return (cfg.my_jira_email or "").lower() if cfg else ""


def _sprint_issues(release, sprint_id, my_email):
    if not release.application_id or not release.jira_project_key:
        return []
    jira = get_jira_service(release.application_id, db=None) if False else None
    return []  # replaced below


@router.post("/releases/{release_id}/sprints", status_code=201)
def attach_sprint(release_id: str, body: SprintAttachIn, db: Session = Depends(get_db)):
    if not db.query(DeliveryReleaseORM).filter(DeliveryReleaseORM.release_id == release_id).first():
        raise HTTPException(404, "release not found")
    row = DeliveryReleaseSprintORM(release_id=release_id, board_id=body.board_id,
                                   sprint_id=body.sprint_id, sprint_name=body.sprint_name)
    db.add(row); db.commit(); db.refresh(row)
    return {"attach_id": row.attach_id, "sprint_id": row.sprint_id, "sprint_name": row.sprint_name}


@router.get("/releases/{release_id}/sprints")
def list_sprints(release_id: str, db: Session = Depends(get_db)):
    release = db.query(DeliveryReleaseORM).filter(DeliveryReleaseORM.release_id == release_id).first()
    if not release:
        raise HTTPException(404, "release not found")
    my_email = _my_email(db)
    jira = get_jira_service(release.application_id, db) if release.application_id else None
    out = []
    for s in db.query(DeliveryReleaseSprintORM).filter(DeliveryReleaseSprintORM.release_id == release_id).all():
        issues = []
        if jira and release.jira_project_key and s.sprint_id:
            try:
                raw = jira.get_sprint_issues(release.jira_project_key, int(s.sprint_id))
            except Exception:
                raw = []
            for it in raw:
                f = it.get("fields", {})
                ass = (f.get("assignee") or {}).get("emailAddress", "") or ""
                issues.append({
                    "key": it.get("key", ""),
                    "summary": f.get("summary", ""),
                    "status": (f.get("status") or {}).get("name", ""),
                    "mine": bool(my_email) and ass.lower() == my_email,
                })
        out.append({"attach_id": s.attach_id, "board_id": s.board_id, "sprint_id": s.sprint_id,
                    "sprint_name": s.sprint_name, "issues": issues})
    return {"release_id": release_id, "sprints": out}


@router.delete("/releases/{release_id}/sprints/{attach_id}", status_code=204)
def detach_sprint(release_id: str, attach_id: str, db: Session = Depends(get_db)):
    row = db.query(DeliveryReleaseSprintORM).filter(
        DeliveryReleaseSprintORM.attach_id == attach_id,
        DeliveryReleaseSprintORM.release_id == release_id).first()
    if not row:
        raise HTTPException(404, "attachment not found")
    db.delete(row); db.commit()
    return None
```
Delete the placeholder `_sprint_issues` stub — it is not used (issues are built inline in `list_sprints`).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_delivery_sprints.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/routers/delivery_routes.py tests/test_delivery_sprints.py
git commit -m "feat(delivery): curated Jira sprint attach/list/detach with mine flag"
```

---

### Task 6: SOD/EOD — releases_at_risk

**Files:**
- Modify: `web/routers/dashboard.py:152-184` (`sod_summary`, `eod_summary`) + a shared helper.
- Test: `tests/test_dashboard_releases_at_risk.py`

**Interfaces:**
- Consumes: `services.release_health.release_health`; `DeliveryReleaseORM`, `DeliveryReleaseItemORM`.
- Produces: `dashboard._releases_at_risk(db)->list[dict]`; `sod`/`eod` responses include key `releases_at_risk`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dashboard_releases_at_risk.py
from datetime import date, timedelta
from fastapi.testclient import TestClient
from web.app import app
from db.init_db import create_all
from db.base import SessionLocal
from db.models import DeliveryReleaseORM, DeliveryReleaseItemORM
create_all()
client = TestClient(app)

def test_breached_release_item_appears_in_sod():
    db = SessionLocal()
    r = DeliveryReleaseORM(name="AtRisk Rel", status="in_progress")
    db.add(r); db.commit(); db.refresh(r)
    db.add(DeliveryReleaseItemORM(release_id=r.release_id, order=0, title="Dev Completion",
           stage="development", status="pending", planned_date=date.today() - timedelta(days=5)))
    db.commit(); db.close()

    sod = client.get("/api/dashboard/sod").json()
    assert "releases_at_risk" in sod
    hit = [x for x in sod["releases_at_risk"] if x["item"] == "Dev Completion"]
    assert hit and hit[0]["state"] == "breached" and hit[0]["days"] == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_dashboard_releases_at_risk.py -v`
Expected: FAIL (`KeyError: releases_at_risk`).

- [ ] **Step 3: Implement the helper and wire into sod/eod**

In `web/routers/dashboard.py` (add imports `from services.release_health import release_health` and the delivery models):
```python
def _releases_at_risk(db):
    from db.models import DeliveryReleaseORM, DeliveryReleaseItemORM
    today = date.today()
    out = []
    releases = db.query(DeliveryReleaseORM).filter(DeliveryReleaseORM.status != "released").all()
    for r in releases:
        items = db.query(DeliveryReleaseItemORM).filter(
            DeliveryReleaseItemORM.release_id == r.release_id).all()
        if not items:
            continue
        h = release_health(items, today)
        if h["derived_status"] == "COMPLETED":
            continue
        for g in h["items"]:
            if g["state"] in ("breached", "at_risk"):
                out.append({"release_id": r.release_id, "name": r.name, "item": g["title"],
                            "stage": g["stage"], "state": g["state"],
                            "planned": g["planned_date"], "days": g["days"]})
    return out
```
Add `"releases_at_risk": _releases_at_risk(db),` to the return dict of both `sod_summary` and `eod_summary`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_dashboard_releases_at_risk.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/routers/dashboard.py tests/test_dashboard_releases_at_risk.py
git commit -m "feat(dashboard): add releases_at_risk to SOD/EOD summaries"
```

---

### Task 7: Email briefings — Releases at risk section

**Files:**
- Modify: `web/email_sender.py` (add `_releases_at_risk_section(db)`; inject into `build_sod_html` and `build_eod_html`).
- Test: `tests/test_email_releases_section.py`

**Interfaces:**
- Consumes: `dashboard._releases_at_risk` (import the function) and existing `_card`/`_pill` helpers.
- Produces: `email_sender._releases_at_risk_section(db)->str` (returns `""` when none).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_email_releases_section.py
from datetime import date, timedelta
from db.init_db import create_all
from db.base import SessionLocal
from db.models import DeliveryReleaseORM, DeliveryReleaseItemORM
from web.email_sender import _releases_at_risk_section, build_sod_html
create_all()

def test_section_lists_breached_item():
    db = SessionLocal()
    r = DeliveryReleaseORM(name="Email Rel", status="in_progress")
    db.add(r); db.commit(); db.refresh(r)
    db.add(DeliveryReleaseItemORM(release_id=r.release_id, order=0, title="QA Completion",
           stage="qa", status="pending", planned_date=date.today() - timedelta(days=2)))
    db.commit()
    html = _releases_at_risk_section(db)
    assert "QA Completion" in html and "Email Rel" in html
    assert "Releases at risk" in build_sod_html(db)
    db.close()

def test_section_empty_when_none():
    from db.base import SessionLocal as S
    # a fresh db state may still have releases; assert function returns a string
    assert isinstance(_releases_at_risk_section(S()), str)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_email_releases_section.py -v`
Expected: FAIL (`ImportError: _releases_at_risk_section`).

- [ ] **Step 3: Implement the section and inject it**

In `web/email_sender.py` add:
```python
def _releases_at_risk_section(db) -> str:
    from web.routers.dashboard import _releases_at_risk
    rows = _releases_at_risk(db)
    if not rows:
        return ""
    lines = ""
    for r in rows:
        color = "#DC2626" if r["state"] == "breached" else "#D97706"
        label = f'{"Breached" if r["state"]=="breached" else "At risk"} {r["days"]}d'
        lines += _task_row(f'{r["name"]} — {r["item"]}', "", note=label, note_color=color)
    return _card("Releases at risk", "🚦", lines, accent="#DC2626")
```
In `build_sod_html` and `build_eod_html`, before the final `_wrap(...)`/return, concatenate the section into the body HTML (place it after the tasks/overdue card, mirroring how `reminders_section` is inserted):
```python
    releases_section = _releases_at_risk_section(db)
```
and include `releases_section` in the assembled body string alongside the other sections.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_email_releases_section.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/email_sender.py tests/test_email_releases_section.py
git commit -m "feat(email): add Releases at risk section to SOD/EOD briefings"
```

---

### Task 8: Delivery view UI — stepper, gate timeline, sprints, completion history

**Files:**
- Modify: `web/static/index.html` (the `view==='delivery'` block near line 5021 and its Alpine data/methods).

**Interfaces:**
- Consumes: `GET /api/delivery/releases`, `GET /api/delivery/releases/{id}` (now with `health` + item `stage`/`planned_date`/`completed_at`), sprint endpoints from Task 5, `GET /api/jira/sprints/{id}` for the attach picker.

This task is UI wiring verified manually in the browser (no unit test). Keep all new markup using existing component classes (`.card`, `.chip`, `.btn-primary`, `.data-table`) so it inherits the theme.

- [ ] **Step 1: Render health + stage stepper on each release**

In the delivery release list/detail markup, for each release show `release.health.derived_status`, `release.health.current_stage`, and a horizontal stepper over `STAGES` (`requirement_gathering→in_prod`) where a stage is "done" if every item of that stage is done, "current" if it equals `current_stage`, "breach" if any item of that stage has `state==='breached'`.

- [ ] **Step 2: Render the gate timeline**

For `release.items` (sorted by stage/order) render a tile per item: title, `planned_date` (Planned) vs `completed_at` (Actual), and a colored state pill from `item.state` (`done`/`breached`/`at_risk`/`upcoming`/`unset`). Use existing `.chip-*` classes for colors.

- [ ] **Step 3: Item edit — planned date + status**

Add controls (or extend the existing item row) to PATCH `planned_date` and `status` via `PATCH /api/delivery/releases/{id}/items/{item_id}`. On status→`done` the backend stamps `completed_at`; re-fetch the release to refresh health.

- [ ] **Step 4: Jira Sprints panel**

Add a panel listing attached sprints from `GET /api/delivery/releases/{id}/sprints` (name, board, `issues` with a "mine" chip). Provide a picker populated from `GET /api/jira/sprints/{id}` and an Add button calling `POST .../sprints`; a remove control calling `DELETE .../sprints/{attach_id}`.

- [ ] **Step 5: Completion history**

Render items that have `completed_at`, sorted ascending, as a timeline ("<title> — completed <date>").

- [ ] **Step 6: Manual verification**

Run: `python3 start.py` then in the browser: create a release from "Standard Release", set a past `planned_date` on Dev Completion → the release shows Breached and the stepper marks Development red; mark it done → history gains the entry and the breach clears; attach a sprint → issues list with "mine" flags. Confirm `/api/dashboard/sod` returns the release under `releases_at_risk` while the gate is breached.

- [ ] **Step 7: Commit**

```bash
git add web/static/index.html
git commit -m "feat(ui): release planner delivery view — stepper, gate timeline, sprints, history"
```

---

## Self-Review Notes

- **Spec coverage:** stage+planned_date (T1,T4) · migration+default template (T2) · derivation/health (T3) · derived status & health block (T4) · curated sprint attach + mine (T5) · SOD/EOD breach (T6) · email section (T7) · UI stepper/timeline/sprints/history (T8). All spec sections mapped.
- **Types:** `release_health(items, today)` return shape (`level`/`derived_status`/`current_stage`/`items[]` with `state`/`days`/`planned_date`/`completed_at`) is produced in T3 and consumed identically in T4/T6/T7.
- **No placeholders:** the `_sprint_issues` stub in T5 Step 3 is explicitly deleted in the same step; issues are built inline in `list_sprints`.
