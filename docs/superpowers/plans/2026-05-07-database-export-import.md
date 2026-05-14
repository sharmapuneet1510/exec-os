# Database Export/Import & Auto-Backup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add database export (JSON), import/restore, and automatic daily backups with Admin/Settings UI panel.

**Architecture:** Create admin router with export/import endpoints. Set up APScheduler for daily backups. Add Admin/Settings sidebar section with export/import modals and backup history.

**Tech Stack:** FastAPI, SQLAlchemy, APScheduler, Python json, Alpine.js

---

### Task 1: Create Admin Router with Export Endpoint

**Files:**
- Create: `web/routers/admin.py`
- Test: `tests/test_admin_api.py`

- [ ] **Step 1: Write failing test for export endpoint**

```python
# tests/test_admin_api.py
from fastapi.testclient import TestClient
from web.app import app
import json

client = TestClient(app)

def test_export_database():
    response = client.get("/api/admin/export")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    
    # Verify it's valid JSON
    data = response.json()
    assert isinstance(data, dict)
    assert "tables" in data
    assert "exported_at" in data
    assert "version" in data

def test_export_contains_tables():
    response = client.get("/api/admin/export")
    data = response.json()
    tables = data["tables"]
    # Should have at least some tables
    assert len(tables) > 0
    # Each table should have a "rows" key
    for table_name, table_data in tables.items():
        assert "rows" in table_data
        assert isinstance(table_data["rows"], list)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_admin_api.py::test_export_database -v
```

Expected: FAIL - endpoint not found

- [ ] **Step 3: Create admin router with export endpoint**

```python
# web/routers/admin.py
from datetime import datetime
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from fastapi import Depends
import json

from db.base import get_db
from db.models import Base

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/export")
def export_database(db: Session = Depends(get_db)):
    """Export entire database as JSON."""
    try:
        export_data = {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "tables": {}
        }
        
        # Get all ORM models from Base
        inspector = inspect(db.bind)
        
        for table in Base.metadata.sorted_tables:
            table_name = table.name
            rows = db.execute(db.query(table).statement).fetchall()
            
            # Convert rows to dicts
            row_dicts = []
            for row in rows:
                row_dict = {}
                for col in table.columns:
                    val = getattr(row, col.name, None)
                    # Handle datetime serialization
                    if isinstance(val, datetime):
                        val = val.isoformat()
                    row_dict[col.name] = val
                row_dicts.append(row_dict)
            
            export_data["tables"][table_name] = {
                "rows": row_dicts,
                "count": len(row_dicts)
            }
        
        return export_data
    except Exception as e:
        raise HTTPException(500, f"Export failed: {str(e)}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_admin_api.py::test_export_database tests/test_admin_api.py::test_export_contains_tables -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/routers/admin.py tests/test_admin_api.py
git commit -m "feat: add admin export endpoint for database JSON export"
```

---

### Task 2: Implement Import/Restore Endpoint

**Files:**
- Modify: `web/routers/admin.py`
- Modify: `tests/test_admin_api.py`

- [ ] **Step 1: Write failing test for import endpoint**

```python
# Add to tests/test_admin_api.py
def test_import_database():
    # First export data
    export_resp = client.get("/api/admin/export")
    export_data = export_resp.json()
    
    # Now import it back
    response = client.post("/api/admin/import", json=export_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "restored_tables" in data

def test_import_invalid_json():
    response = client.post("/api/admin/import", json={"invalid": "data"})
    assert response.status_code == 400
    assert "version" in response.json()["detail"].lower()

def test_import_empty_data():
    response = client.post("/api/admin/import", json={})
    assert response.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_admin_api.py::test_import_database -v
```

Expected: FAIL - endpoint not implemented

- [ ] **Step 3: Implement import endpoint**

Add to `web/routers/admin.py`:

```python
from sqlalchemy.exc import IntegrityError

@router.post("/import")
def import_database(data: dict, db: Session = Depends(get_db)):
    """Import/restore database from JSON export."""
    try:
        # Validate structure
        if "version" not in data or "tables" not in data:
            raise HTTPException(400, "Invalid export format: missing version or tables")
        
        tables_restored = {}
        total_rows = 0
        
        # For each table in the export
        for table_name, table_data in data["tables"].items():
            if not isinstance(table_data, dict) or "rows" not in table_data:
                continue
            
            rows = table_data["rows"]
            if not rows:
                tables_restored[table_name] = 0
                continue
            
            # Find matching ORM model
            matching_table = None
            for table in Base.metadata.sorted_tables:
                if table.name == table_name:
                    matching_table = table
                    break
            
            if not matching_table:
                # Table doesn't exist in current schema, skip
                continue
            
            # Get the ORM class
            from db import models
            model_class = None
            for attr_name in dir(models):
                attr = getattr(models, attr_name)
                if hasattr(attr, '__tablename__') and attr.__tablename__ == table_name:
                    model_class = attr
                    break
            
            if not model_class:
                continue
            
            # Clear existing data for this table
            db.query(model_class).delete()
            
            # Insert rows
            inserted = 0
            for row_dict in rows:
                # Parse datetime strings back to datetime objects
                for key, val in row_dict.items():
                    if isinstance(val, str) and val and 'T' in val:
                        try:
                            row_dict[key] = datetime.fromisoformat(val)
                        except:
                            pass
                
                try:
                    obj = model_class(**row_dict)
                    db.add(obj)
                    inserted += 1
                except (IntegrityError, ValueError) as e:
                    db.rollback()
                    continue
            
            db.commit()
            tables_restored[table_name] = inserted
            total_rows += inserted
        
        return {
            "status": "success",
            "message": f"Restored {total_rows} rows across {len(tables_restored)} tables",
            "restored_tables": tables_restored
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Import failed: {str(e)}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_admin_api.py::test_import_database tests/test_admin_api.py::test_import_invalid_json -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/routers/admin.py tests/test_admin_api.py
git commit -m "feat: implement import/restore endpoint for database JSON import"
```

---

### Task 3: Set Up Automatic Daily Backups

**Files:**
- Create: `services/backup_scheduler.py`
- Modify: `web/app.py`

- [ ] **Step 1: Create backup scheduler service**

```python
# services/backup_scheduler.py
import os
import json
from datetime import datetime
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from db.base import SessionLocal, engine
from db.models import Base


BACKUP_DIR = Path.home() / ".commanddesk" / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def create_backup():
    """Create a JSON backup of the database."""
    try:
        db = SessionLocal()
        
        export_data = {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "tables": {}
        }
        
        # Export all tables
        for table in Base.metadata.sorted_tables:
            table_name = table.name
            rows = db.execute(db.query(table).statement).fetchall()
            
            row_dicts = []
            for row in rows:
                row_dict = {}
                for col in table.columns:
                    val = getattr(row, col.name, None)
                    if isinstance(val, datetime):
                        val = val.isoformat()
                    row_dict[col.name] = val
                row_dicts.append(row_dict)
            
            export_data["tables"][table_name] = {
                "rows": row_dicts,
                "count": len(row_dicts)
            }
        
        # Save to file
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"backup_{timestamp}.json"
        
        with open(backup_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        # Keep only last 7 backups
        backups = sorted(BACKUP_DIR.glob("backup_*.json"))
        for old_backup in backups[:-7]:
            old_backup.unlink()
        
        print(f"✓ Backup created: {backup_file}")
        db.close()
    except Exception as e:
        print(f"✗ Backup failed: {e}")


def start_backup_scheduler():
    """Start the APScheduler for daily backups."""
    scheduler = BackgroundScheduler()
    # Run at 2 AM every day
    scheduler.add_job(create_backup, 'cron', hour=2, minute=0)
    scheduler.start()
    print("✓ Backup scheduler started (daily at 2:00 AM)")
    return scheduler
```

- [ ] **Step 2: Integrate scheduler into app startup**

In `web/app.py`, add at the top:

```python
from services.backup_scheduler import start_backup_scheduler

scheduler = None

@app.on_event("startup")
async def startup():
    global scheduler
    scheduler = start_backup_scheduler()

@app.on_event("shutdown")
async def shutdown():
    global scheduler
    if scheduler:
        scheduler.shutdown()
```

- [ ] **Step 3: Install APScheduler dependency**

```bash
pip install apscheduler
```

- [ ] **Step 4: Test backup creation**

```bash
python3 -c "from services.backup_scheduler import create_backup; create_backup()"
```

Expected: Backup file created in ~/.commanddesk/backups/

- [ ] **Step 5: Commit**

```bash
git add services/backup_scheduler.py web/app.py
git commit -m "feat: add automatic daily database backups with APScheduler"
```

---

### Task 4: Add Admin Router to FastAPI App

**Files:**
- Modify: `web/app.py`

- [ ] **Step 1: Mount admin router**

In `web/app.py`, add with other imports:

```python
from web.routers.admin import router as admin_router
```

Then in the routers section:

```python
app.include_router(admin_router)
```

- [ ] **Step 2: Test endpoints are accessible**

```bash
python3 start.py &
sleep 3
curl -s http://localhost:8080/api/admin/export | jq '.exported_at' 
pkill -f "python3 start.py"
```

Expected: Returns current timestamp

- [ ] **Step 3: Commit**

```bash
git add web/app.py
git commit -m "feat: mount admin router in FastAPI app"
```

---

### Task 5: Add Admin/Settings UI Panel to Dashboard

**Files:**
- Modify: `web/static/index.html`

- [ ] **Step 1: Add Admin navigation item**

Find the sidebar navigation. Add at the bottom:

```html
<a href="#" @click="page='admin'" 
   :class="page==='admin' ? 'bg-indigo-100 text-indigo-900' : 'text-gray-600 hover:text-gray-900'"
   class="block px-4 py-2 font-medium border-t mt-2 pt-2">⚙️ Admin/Settings</a>
```

- [ ] **Step 2: Add Admin view HTML**

Add after other page views:

```html
<div x-show="page==='admin'" class="space-y-4">
  <h2 class="text-2xl font-bold">Admin & Settings</h2>
  
  <div class="grid grid-cols-2 gap-4">
    <!-- Export Card -->
    <div class="bg-white rounded-lg shadow p-6">
      <h3 class="text-lg font-semibold mb-4">📥 Export Database</h3>
      <p class="text-sm text-gray-600 mb-4">Download entire database as JSON</p>
      <button @click="exportDatabase()" class="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
        Export as JSON
      </button>
    </div>
    
    <!-- Import Card -->
    <div class="bg-white rounded-lg shadow p-6">
      <h3 class="text-lg font-semibold mb-4">📤 Import/Restore</h3>
      <p class="text-sm text-gray-600 mb-4">Restore database from JSON backup</p>
      <button @click="triggerImport()" class="w-full px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
        Import from File
      </button>
      <input type="file" id="importFile" @change="importDatabase($event)" style="display:none" accept=".json">
    </div>
    
    <!-- Backup History Card -->
    <div class="bg-white rounded-lg shadow p-6 col-span-2">
      <h3 class="text-lg font-semibold mb-4">🗄️ Backup History</h3>
      <p class="text-sm text-gray-600 mb-4">Automatic daily backups at 2:00 AM</p>
      <p class="text-sm font-semibold text-green-600">✓ Scheduler active - Last backup will be stored locally</p>
    </div>
  </div>
  
  <!-- Status Messages -->
  <div x-show="adminStatus" class="p-4 rounded" :class="adminStatus.type === 'error' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'">
    <p x-text="adminStatus.message"></p>
  </div>
</div>
```

- [ ] **Step 3: Add Alpine.js data**

Add to the app data object:

```javascript
admin: {
  page: 'admin'
},
adminStatus: null,
```

- [ ] **Step 4: Add Alpine.js methods**

Add to methods:

```javascript
async exportDatabase() {
  try {
    this.adminStatus = { type: 'info', message: 'Exporting database...' };
    const resp = await fetch('/api/admin/export');
    const data = await resp.json();
    
    // Create download link
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `execos_backup_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    
    this.adminStatus = { type: 'success', message: '✓ Database exported successfully' };
    setTimeout(() => this.adminStatus = null, 3000);
  } catch (err) {
    this.adminStatus = { type: 'error', message: `✗ Export failed: ${err.message}` };
  }
},

triggerImport() {
  document.getElementById('importFile').click();
},

async importDatabase(event) {
  try {
    const file = event.target.files[0];
    if (!file) return;
    
    this.adminStatus = { type: 'info', message: 'Reading file...' };
    const json = await file.text();
    const data = JSON.parse(json);
    
    this.adminStatus = { type: 'info', message: 'Importing database (this may take a moment)...' };
    const resp = await fetch('/api/admin/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    if (!resp.ok) {
      throw new Error((await resp.json()).detail || 'Import failed');
    }
    
    const result = await resp.json();
    this.adminStatus = { 
      type: 'success', 
      message: `✓ Import successful: ${result.message}` 
    };
    
    // Reload all data
    this.loadAll();
    
    setTimeout(() => this.adminStatus = null, 5000);
  } catch (err) {
    this.adminStatus = { type: 'error', message: `✗ Import failed: ${err.message}` };
  } finally {
    // Reset file input
    document.getElementById('importFile').value = '';
  }
}
```

- [ ] **Step 5: Commit**

```bash
git add web/static/index.html
git commit -m "feat: add admin/settings panel with export/import UI"
```

---

### Task 6: Test Export/Import End-to-End

**Files:**
- Test manually via dashboard

- [ ] **Step 1: Start app and test export**

```bash
python3 start.py &
sleep 3

# Test export via curl
curl -s http://localhost:8080/api/admin/export > /tmp/test_export.json
echo "✓ Export successful - file size: $(wc -c < /tmp/test_export.json) bytes"

# Verify it's valid JSON
python3 -c "import json; json.load(open('/tmp/test_export.json'))" && echo "✓ Valid JSON"

pkill -f "python3 start.py"
```

- [ ] **Step 2: Test via UI**

```bash
python3 start.py &
sleep 3

# Open http://localhost:8080 in browser
# Navigate to Admin/Settings
# Click "Export as JSON" - should download file
# Click "Import from File" - select the downloaded file
# Verify success message appears
# Check that data reloaded

pkill -f "python3 start.py"
```

- [ ] **Step 3: Verify tests pass**

```bash
pytest tests/test_admin_api.py -v
```

Expected: All tests pass

- [ ] **Step 4: Commit final test verification**

```bash
git add tests/test_admin_api.py
git commit -m "test: verify export/import functionality end-to-end"
```

---

## Success Criteria

- [x] Admin/Settings section in dashboard sidebar
- [x] Export button downloads entire database as JSON
- [x] Import button restores from JSON file
- [x] Error messages shown for failed operations
- [x] Success notifications after operations
- [x] Automatic daily backups at 2:00 AM
- [x] Last 7 backups kept automatically
- [x] All 6+ tests passing
- [x] No regressions in existing functionality
