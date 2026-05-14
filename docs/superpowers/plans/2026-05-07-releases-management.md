# Releases Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add complete releases management system with CRUD API and global dashboard view.

**Architecture:** Create dedicated releases router following existing project/tasks patterns. Releases are global (not project-filtered) but can link to projects. Dashboard includes summary card and full releases table with CRUD modals.

**Tech Stack:** FastAPI, SQLAlchemy ORM, Pydantic models, Alpine.js frontend

---

### Task 1: Create Releases Router with Pydantic Models

**Files:**
- Create: `web/routers/releases.py`
- Test: `tests/test_releases_api.py`

- [ ] **Step 1: Write failing test for Pydantic models**

```python
# tests/test_releases_api.py
from datetime import date
from web.routers.releases import ReleaseIn, ReleaseOut

def test_release_in_validation():
    # Valid minimal
    r = ReleaseIn(name="v1.0")
    assert r.name == "v1.0"
    assert r.version == ""
    assert r.status == "planned"

def test_release_in_name_required():
    # Name is required
    try:
        ReleaseIn()
        assert False, "Should require name"
    except Exception:
        pass

def test_release_out_fields():
    data = {
        "release_id": "rel-123",
        "name": "v1.0",
        "version": "1.0.0",
        "project_id": "proj-1",
        "project_name": "My Project",
        "application_id": None,
        "due_date": None,
        "status": "planned",
        "description": "Initial release",
        "days_until_due": None,
        "is_overdue": False,
        "created_at": date(2026, 5, 7),
        "updated_at": date(2026, 5, 7),
    }
    r = ReleaseOut(**data)
    assert r.release_id == "rel-123"
    assert r.status == "planned"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_releases_api.py -v
```

Expected: FAIL - module not found or ReleaseIn/ReleaseOut not defined

- [ ] **Step 3: Create releases router with Pydantic models**

```python
# web/routers/releases.py
from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.base import get_db
from db.models import ReleaseORM, ProjectORM

router = APIRouter(prefix="/api/releases", tags=["releases"])


class ReleaseIn(BaseModel):
    name: str
    version: str = ""
    project_id: Optional[str] = None
    application_id: Optional[str] = None
    due_date: Optional[date] = None
    status: str = "planned"
    description: str = ""


class ReleaseOut(BaseModel):
    release_id: str
    name: str
    version: str
    project_id: Optional[str]
    project_name: Optional[str]
    application_id: Optional[str]
    due_date: Optional[date]
    status: str
    description: str
    days_until_due: Optional[int]
    is_overdue: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


def _bust_dash():
    from web.deps import get_redis
    r = get_redis()
    r.delete("dashboard:operational")
    r.delete("dashboard:executive")


def _to_out(rel: ReleaseORM, db: Session) -> dict:
    today = date.today()
    days_until_due = None
    is_overdue = False
    if rel.due_date:
        days_until_due = (rel.due_date - today).days
        is_overdue = rel.due_date < today and rel.status not in ("completed", "cancelled")
    
    project_name = None
    if rel.project_id:
        proj = db.query(ProjectORM).filter(ProjectORM.project_id == rel.project_id).first()
        if proj:
            project_name = proj.name
    
    return {
        "release_id": rel.release_id,
        "name": rel.name,
        "version": rel.version or "",
        "project_id": rel.project_id,
        "project_name": project_name,
        "application_id": rel.application_id,
        "due_date": rel.due_date,
        "status": rel.status,
        "description": rel.description or "",
        "days_until_due": days_until_due,
        "is_overdue": is_overdue,
        "created_at": rel.created_at,
        "updated_at": rel.updated_at,
    }


@router.get("", response_model=List[ReleaseOut])
def list_releases(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(ReleaseORM)
    if project_id:
        q = q.filter(ReleaseORM.project_id == project_id)
    if status:
        q = q.filter(ReleaseORM.status == status)
    releases = q.order_by(ReleaseORM.due_date.asc(), ReleaseORM.created_at.desc()).all()
    return [_to_out(rel, db) for rel in releases]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_releases_api.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/routers/releases.py tests/test_releases_api.py
git commit -m "feat: add releases router with Pydantic models and list endpoint"
```

---

### Task 2: Implement POST (Create) Endpoint

**Files:**
- Modify: `web/routers/releases.py`
- Modify: `tests/test_releases_api.py`

- [ ] **Step 1: Write failing test for create endpoint**

```python
# Add to tests/test_releases_api.py
from fastapi.testclient import TestClient
from web.app import app

client = TestClient(app)

def test_create_release_minimal():
    response = client.post("/api/releases", json={"name": "v1.0"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "v1.0"
    assert data["status"] == "planned"
    assert data["release_id"]

def test_create_release_full():
    response = client.post("/api/releases", json={
        "name": "v2.0",
        "version": "2.0.0",
        "project_id": None,
        "due_date": "2026-06-01",
        "status": "in_progress",
        "description": "Major release",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "v2.0"
    assert data["version"] == "2.0.0"
    assert data["status"] == "in_progress"

def test_create_release_empty_name():
    response = client.post("/api/releases", json={"name": ""})
    assert response.status_code == 400

def test_create_release_invalid_project():
    response = client.post("/api/releases", json={
        "name": "v1.0",
        "project_id": "nonexistent-proj"
    })
    assert response.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_releases_api.py::test_create_release_minimal -v
```

Expected: FAIL - endpoint not implemented

- [ ] **Step 3: Implement POST endpoint**

Add to `web/routers/releases.py`:

```python
@router.post("", response_model=ReleaseOut, status_code=201)
def create_release(body: ReleaseIn, db: Session = Depends(get_db)):
    if not body.name.strip():
        raise HTTPException(400, "name must not be empty")
    
    # Validate project_id if provided
    if body.project_id:
        project = db.query(ProjectORM).filter(ProjectORM.project_id == body.project_id).first()
        if not project:
            raise HTTPException(400, "project not found")
    
    rel = ReleaseORM(
        name=body.name.strip(),
        version=body.version,
        project_id=body.project_id,
        application_id=body.application_id,
        due_date=body.due_date,
        status=body.status,
        description=body.description,
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)
    _bust_dash()
    return _to_out(rel, db)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_releases_api.py::test_create_release_minimal tests/test_releases_api.py::test_create_release_full tests/test_releases_api.py::test_create_release_empty_name tests/test_releases_api.py::test_create_release_invalid_project -v
```

Expected: PASS (4/4)

- [ ] **Step 5: Commit**

```bash
git add web/routers/releases.py tests/test_releases_api.py
git commit -m "feat: implement POST /api/releases create endpoint with validation"
```

---

### Task 3: Implement GET/{id}, PATCH, DELETE Endpoints

**Files:**
- Modify: `web/routers/releases.py`
- Modify: `tests/test_releases_api.py`

- [ ] **Step 1: Write failing tests for remaining CRUD operations**

```python
# Add to tests/test_releases_api.py

def test_get_release():
    # First create one
    create_resp = client.post("/api/releases", json={"name": "v1.0"})
    release_id = create_resp.json()["release_id"]
    
    # Get it
    response = client.get(f"/api/releases/{release_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["release_id"] == release_id
    assert data["name"] == "v1.0"

def test_get_release_not_found():
    response = client.get("/api/releases/nonexistent")
    assert response.status_code == 404

def test_update_release():
    create_resp = client.post("/api/releases", json={"name": "v1.0", "status": "planned"})
    release_id = create_resp.json()["release_id"]
    
    response = client.patch(f"/api/releases/{release_id}", json={
        "status": "in_progress",
        "description": "Now in progress"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"
    assert data["description"] == "Now in progress"
    assert data["name"] == "v1.0"  # Unchanged

def test_update_release_not_found():
    response = client.patch("/api/releases/nonexistent", json={"status": "completed"})
    assert response.status_code == 404

def test_delete_release():
    create_resp = client.post("/api/releases", json={"name": "v1.0"})
    release_id = create_resp.json()["release_id"]
    
    response = client.delete(f"/api/releases/{release_id}")
    assert response.status_code == 204
    
    # Verify deleted
    get_resp = client.get(f"/api/releases/{release_id}")
    assert get_resp.status_code == 404

def test_delete_release_not_found():
    response = client.delete("/api/releases/nonexistent")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_releases_api.py::test_get_release -v
```

Expected: FAIL - endpoints not implemented

- [ ] **Step 3: Implement GET/{id}, PATCH, DELETE endpoints**

Add to `web/routers/releases.py`:

```python
@router.get("/{release_id}", response_model=ReleaseOut)
def get_release(release_id: str, db: Session = Depends(get_db)):
    rel = db.query(ReleaseORM).filter(ReleaseORM.release_id == release_id).first()
    if not rel:
        raise HTTPException(404, "release not found")
    return _to_out(rel, db)


@router.patch("/{release_id}", response_model=ReleaseOut)
def update_release(release_id: str, body: dict, db: Session = Depends(get_db)):
    rel = db.query(ReleaseORM).filter(ReleaseORM.release_id == release_id).first()
    if not rel:
        raise HTTPException(404, "release not found")
    
    allowed = {"name", "version", "project_id", "application_id", "due_date", "status", "description"}
    for k, v in body.items():
        if k not in allowed:
            continue
        if k == "due_date" and isinstance(v, str):
            v = date.fromisoformat(v) if v else None
        setattr(rel, k, v)
    
    # Validate project_id if changed
    if "project_id" in body and body["project_id"]:
        project = db.query(ProjectORM).filter(ProjectORM.project_id == body["project_id"]).first()
        if not project:
            raise HTTPException(400, "project not found")
    
    rel.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rel)
    _bust_dash()
    return _to_out(rel, db)


@router.delete("/{release_id}", status_code=204)
def delete_release(release_id: str, db: Session = Depends(get_db)):
    rel = db.query(ReleaseORM).filter(ReleaseORM.release_id == release_id).first()
    if not rel:
        raise HTTPException(404, "release not found")
    db.delete(rel)
    db.commit()
    _bust_dash()
```

- [ ] **Step 4: Run all CRUD tests to verify they pass**

```bash
pytest tests/test_releases_api.py -v
```

Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add web/routers/releases.py tests/test_releases_api.py
git commit -m "feat: implement GET/{id}, PATCH, DELETE endpoints for releases"
```

---

### Task 4: Mount Releases Router in FastAPI App

**Files:**
- Modify: `web/app.py`

- [ ] **Step 1: Add router import and mount**

In `web/app.py`, add at the top with other imports:

```python
from web.routers import releases
```

Then in the app initialization section, add with other routers:

```python
app.include_router(releases.router)
```

- [ ] **Step 2: Test all endpoints work end-to-end**

```bash
python3 start.py &
sleep 3
curl -X POST http://localhost:8080/api/releases -H "Content-Type: application/json" -d '{"name":"v1.0"}'
curl http://localhost:8080/api/releases
pkill -f "python3 start.py"
```

Expected: Both requests return 200/201 with JSON data

- [ ] **Step 3: Commit**

```bash
git add web/app.py
git commit -m "feat: mount releases router in FastAPI app"
```

---

### Task 5: Add Releases View to Dashboard UI

**Files:**
- Modify: `web/static/index.html`

- [ ] **Step 1: Add Releases navigation item**

Find the navigation section in `web/static/index.html` and add after Projects:

```html
<a href="#" @click="page='releases'" 
   :class="page==='releases' ? 'bg-indigo-100 text-indigo-900' : 'text-gray-600 hover:text-gray-900'"
   class="block px-4 py-2 font-medium">📦 Releases</a>
```

- [ ] **Step 2: Add Releases page HTML structure**

Add after the Projects view section:

```html
<div x-show="page==='releases'" class="space-y-4">
  <div class="flex justify-between items-center">
    <h2 class="text-2xl font-bold">Releases</h2>
    <button @click="openReleaseModal()" class="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700">
      Create Release
    </button>
  </div>
  
  <div class="bg-white rounded-lg shadow">
    <div class="p-4 border-b space-y-3">
      <input type="text" 
        v-model="releaseSearchTerm"
        placeholder="Search releases..."
        class="w-full px-3 py-2 border rounded">
      <select v-model="releaseStatusFilter" class="w-full px-3 py-2 border rounded">
        <option value="">All Statuses</option>
        <option value="planned">Planned</option>
        <option value="in_progress">In Progress</option>
        <option value="completed">Completed</option>
        <option value="cancelled">Cancelled</option>
      </select>
    </div>
    
    <table class="w-full text-sm">
      <thead class="bg-gray-50 border-b">
        <tr>
          <th class="px-4 py-2 text-left font-semibold">Name</th>
          <th class="px-4 py-2 text-left font-semibold">Version</th>
          <th class="px-4 py-2 text-left font-semibold">Project</th>
          <th class="px-4 py-2 text-left font-semibold">Due Date</th>
          <th class="px-4 py-2 text-left font-semibold">Status</th>
          <th class="px-4 py-2 text-left font-semibold">Actions</th>
        </tr>
      </thead>
      <tbody>
        <template x-for="rel in filteredReleases" :key="rel.release_id">
          <tr class="border-b hover:bg-gray-50">
            <td class="px-4 py-2">
              <a href="#" @click="openReleaseModal(rel)" class="text-indigo-600 hover:underline" x-text="rel.name"></a>
            </td>
            <td class="px-4 py-2" x-text="rel.version || '—'"></td>
            <td class="px-4 py-2" x-text="rel.project_name || '—'"></td>
            <td class="px-4 py-2">
              <span :class="rel.is_overdue ? 'text-red-600 font-semibold' : rel.days_until_due <= 7 ? 'text-yellow-600' : ''"
                x-text="rel.due_date || '—'"></span>
            </td>
            <td class="px-4 py-2">
              <span :class="{
                'bg-blue-100 text-blue-800': rel.status === 'planned',
                'bg-yellow-100 text-yellow-800': rel.status === 'in_progress',
                'bg-green-100 text-green-800': rel.status === 'completed',
                'bg-gray-100 text-gray-800': rel.status === 'cancelled'
              }" class="px-2 py-1 rounded text-xs font-semibold" x-text="rel.status"></span>
            </td>
            <td class="px-4 py-2 space-x-2">
              <button @click="openReleaseModal(rel)" class="text-indigo-600 hover:text-indigo-800">✏️</button>
              <button @click="deleteRelease(rel.release_id)" class="text-red-600 hover:text-red-800">🗑️</button>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</div>
```

- [ ] **Step 3: Add Releases modal HTML**

Add after Projects modal:

```html
<div x-show="showReleaseModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
  <div class="bg-white rounded-lg p-6 w-96 max-h-96 overflow-y-auto">
    <h3 class="text-lg font-bold mb-4" x-text="editingRelease?.release_id ? 'Edit Release' : 'Create Release'"></h3>
    
    <div class="space-y-3">
      <div>
        <label class="block text-sm font-semibold mb-1">Name</label>
        <input type="text" v-model="releaseForm.name" class="w-full px-3 py-2 border rounded" placeholder="Release name">
      </div>
      
      <div>
        <label class="block text-sm font-semibold mb-1">Version</label>
        <input type="text" v-model="releaseForm.version" class="w-full px-3 py-2 border rounded" placeholder="e.g. 1.0.0">
      </div>
      
      <div>
        <label class="block text-sm font-semibold mb-1">Project</label>
        <select v-model="releaseForm.project_id" class="w-full px-3 py-2 border rounded">
          <option value="">— Unassigned —</option>
          <template x-for="proj in projects" :key="proj.project_id">
            <option :value="proj.project_id" x-text="proj.name"></option>
          </template>
        </select>
      </div>
      
      <div>
        <label class="block text-sm font-semibold mb-1">Due Date</label>
        <input type="date" v-model="releaseForm.due_date" class="w-full px-3 py-2 border rounded">
      </div>
      
      <div>
        <label class="block text-sm font-semibold mb-1">Status</label>
        <select v-model="releaseForm.status" class="w-full px-3 py-2 border rounded">
          <option value="planned">Planned</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>
      
      <div>
        <label class="block text-sm font-semibold mb-1">Description</label>
        <textarea v-model="releaseForm.description" class="w-full px-3 py-2 border rounded" rows="3"></textarea>
      </div>
    </div>
    
    <div class="flex justify-end gap-2 mt-4">
      <button @click="showReleaseModal=false" class="px-4 py-2 text-gray-600 border rounded hover:bg-gray-50">Cancel</button>
      <button @click="saveRelease()" class="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700">Save</button>
    </div>
  </div>
</div>
```

- [ ] **Step 4: Add Alpine.js data and methods for releases**

Add to the Alpine.js `data()` object:

```javascript
releases: [],
releaseSearchTerm: '',
releaseStatusFilter: '',
showReleaseModal: false,
releaseForm: {
  name: '',
  version: '',
  project_id: '',
  due_date: '',
  status: 'planned',
  description: '',
},
editingRelease: null,
```

Add computed property for filtered releases:

```javascript
get filteredReleases() {
  return this.releases.filter(rel => {
    const matchesSearch = rel.name.toLowerCase().includes(this.releaseSearchTerm.toLowerCase());
    const matchesStatus = !this.releaseStatusFilter || rel.status === this.releaseStatusFilter;
    return matchesSearch && matchesStatus;
  });
}
```

Add methods:

```javascript
async loadReleases() {
  const resp = await fetch('/api/releases');
  this.releases = await resp.json();
},
openReleaseModal(rel = null) {
  this.editingRelease = rel;
  if (rel) {
    this.releaseForm = {
      name: rel.name,
      version: rel.version,
      project_id: rel.project_id || '',
      due_date: rel.due_date || '',
      status: rel.status,
      description: rel.description,
    };
  } else {
    this.releaseForm = {
      name: '',
      version: '',
      project_id: '',
      due_date: '',
      status: 'planned',
      description: '',
    };
  }
  this.showReleaseModal = true;
},
async saveRelease() {
  if (!this.releaseForm.name.trim()) {
    alert('Name is required');
    return;
  }
  
  const url = this.editingRelease 
    ? `/api/releases/${this.editingRelease.release_id}`
    : '/api/releases';
  const method = this.editingRelease ? 'PATCH' : 'POST';
  
  const resp = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(this.releaseForm),
  });
  
  if (resp.ok) {
    this.showReleaseModal = false;
    this.loadReleases();
  } else {
    alert('Error saving release');
  }
},
async deleteRelease(releaseId) {
  if (!confirm('Delete this release?')) return;
  
  const resp = await fetch(`/api/releases/${releaseId}`, { method: 'DELETE' });
  if (resp.ok) {
    this.loadReleases();
  } else {
    alert('Error deleting release');
  }
},
```

Call `loadReleases()` in the initialization section (where projects/tasks are loaded).

- [ ] **Step 5: Commit**

```bash
git add web/static/index.html
git commit -m "feat: add Releases view to dashboard with CRUD modals"
```

---

### Task 6: Add Release Summary Card to Dashboard Home

**Files:**
- Modify: `web/static/index.html`
- Modify: `web/routers/dashboard.py`

- [ ] **Step 1: Add release stats to dashboard endpoint**

In `web/routers/dashboard.py`, find the operational dashboard function and add release stats:

```python
def _releases_stats(db: Session):
    releases = db.query(ReleaseORM).all()
    return {
        "total": len(releases),
        "planned": sum(1 for r in releases if r.status == "planned"),
        "in_progress": sum(1 for r in releases if r.status == "in_progress"),
        "completed": sum(1 for r in releases if r.status == "completed"),
        "cancelled": sum(1 for r in releases if r.status == "cancelled"),
        "overdue": sum(1 for r in releases if r.due_date and r.due_date < date.today() and r.status not in ("completed", "cancelled")),
    }
```

Add to the operational dashboard response:

```python
response_data["releases_stats"] = _releases_stats(db)
```

- [ ] **Step 2: Add release card to dashboard HTML**

Add after projects card in the dashboard home view:

```html
<div class="bg-white rounded-lg shadow p-6">
  <div class="flex justify-between items-center mb-4">
    <h3 class="text-lg font-semibold">📦 Releases</h3>
    <a href="#" @click="page='releases'" class="text-indigo-600 hover:underline text-sm">View all</a>
  </div>
  
  <div class="space-y-2 text-sm">
    <div class="flex justify-between">
      <span class="text-gray-600">Total</span>
      <span class="font-semibold" x-text="dashboard.releases_stats?.total || 0"></span>
    </div>
    <div class="flex justify-between">
      <span class="text-gray-600">Planned</span>
      <span class="font-semibold text-blue-600" x-text="dashboard.releases_stats?.planned || 0"></span>
    </div>
    <div class="flex justify-between">
      <span class="text-gray-600">In Progress</span>
      <span class="font-semibold text-yellow-600" x-text="dashboard.releases_stats?.in_progress || 0"></span>
    </div>
    <div class="flex justify-between">
      <span class="text-gray-600">Completed</span>
      <span class="font-semibold text-green-600" x-text="dashboard.releases_stats?.completed || 0"></span>
    </div>
    <div class="flex justify-between pt-2 border-t">
      <span class="text-red-600 font-semibold">Overdue</span>
      <span class="font-semibold text-red-600" x-text="dashboard.releases_stats?.overdue || 0"></span>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Test dashboard loads release stats**

```bash
python3 start.py &
sleep 3
curl http://localhost:8080/api/dashboard/operational | jq '.releases_stats'
pkill -f "python3 start.py"
```

Expected: JSON with releases_stats showing counts

- [ ] **Step 4: Commit**

```bash
git add web/routers/dashboard.py web/static/index.html
git commit -m "feat: add releases summary card to dashboard home"
```

---
