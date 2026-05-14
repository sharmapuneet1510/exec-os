# ExecOS Developer Guide

Complete guide for developers working on ExecOS features, pages, and API endpoints.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Adding a New Page](#adding-a-new-page)
3. [Adding API Endpoints](#adding-api-endpoints)
4. [Database Modifications](#database-modifications)
5. [Frontend Patterns](#frontend-patterns)
6. [Backend Patterns](#backend-patterns)
7. [Testing](#testing)
8. [Common Tasks](#common-tasks)
9. [Code Organization](#code-organization)

---

## Project Structure

### Directory Hierarchy

```
command-center/
├── README.md                      # Project overview & quick start
├── CLAUDE.md                      # Developer instructions
├── start.py                       # Entry point (run this!)
├── requirements.txt               # Python dependencies
│
├── web/
│   ├── app.py                     # FastAPI app setup, routing
│   ├── deps.py                    # Shared dependencies (cache, session)
│   ├── routers/                   # API endpoints organized by feature
│   │   ├── tasks.py               # Task CRUD: /api/tasks
│   │   ├── projects.py            # Project CRUD: /api/projects
│   │   ├── milestones.py          # Milestone CRUD: /api/milestones
│   │   ├── commitments.py         # Commitment CRUD: /api/commitments
│   │   ├── alerts.py              # Alert CRUD: /api/alerts
│   │   ├── dashboard.py           # Dashboard endpoints
│   │   ├── admin_routes.py        # Settings & config
│   │   ├── team_routes.py         # Team member CRUD
│   │   ├── application_routes.py  # Application CRUD
│   │   ├── releases.py            # Release management
│   │   ├── jira_routes.py         # Jira integration
│   │   ├── gitlab_routes.py       # GitLab integration
│   │   └── ... (more routers)
│   └── static/
│       └── index.html             # SPA (all 27 pages)
│
├── db/
│   ├── base.py                    # SQLAlchemy setup, engine, session
│   ├── models.py                  # ORM models (25+ tables)
│   └── init_db.py                 # Database initialization (create_all)
│
├── docs/
│   ├── PAGES.md                   # Page-by-page documentation
│   ├── API.md                     # REST API reference
│   ├── DEVELOPER_GUIDE.md         # This file
│   └── superpowers/
│       ├── specs/                 # Design specifications
│       └── plans/                 # Implementation plans
│
└── tasks/ projects/ ...           # Legacy desktop app (Tkinter)
```

---

## Adding a New Page

### Step-by-Step

#### 1. Design the Page
Document in `docs/PAGES.md`:
- View ID (e.g., `my-work`, `tasks`, `projects`)
- Purpose and description
- UI structure (layout, components)
- Database schema (tables, queries)
- Files to modify

#### 2. Create the Frontend View
Edit `/web/static/index.html`:

```html
<!-- Add to <main> section -->
<div x-show="view === 'new-page-id'" style="flex:1;overflow-y:auto;padding:var(--content-padding-top) var(--content-padding-sides);box-sizing:border-box;">
  <h1 style="padding:var(--header-padding-top) var(--header-padding-sides) var(--header-padding-bottom);">Page Title</h1>
  
  <!-- Page content here -->
  <div style="display:flex;flex-direction:column;gap:var(--card-gap);">
    <!-- Cards or content -->
  </div>
</div>
```

**CSS Variable Rules:**
- Headers: `padding: var(--header-padding-top) var(--header-padding-sides) var(--header-padding-bottom);`
- Content areas: `padding: var(--content-padding-top) var(--content-padding-sides);`
- Card gaps: `gap: var(--card-gap);`
- Card styling: `padding: var(--card-padding); border: var(--card-border-width) solid; border-left: var(--card-accent-border-width) solid;`

#### 3. Create Backend Router
Create `/web/routers/new_page_routes.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.base import get_db
from db.models import YourORM
from typing import List, Optional

router = APIRouter(prefix="/api/new-endpoint", tags=["new_page"])

@router.get("/")
async def list_items(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    """List all items with pagination"""
    items = db.query(YourORM).offset(skip).limit(limit).all()
    return {"items": items, "total": len(items), "skip": skip, "limit": limit}

@router.post("/")
async def create_item(item: YourSchema, db: Session = Depends(get_db)):
    """Create new item"""
    db_item = YourORM(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.get("/{item_id}")
async def get_item(item_id: str, db: Session = Depends(get_db)):
    """Get specific item"""
    item = db.query(YourORM).filter(YourORM.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.patch("/{item_id}")
async def update_item(item_id: str, item: YourSchemaUpdate, db: Session = Depends(get_db)):
    """Update item (partial)"""
    db_item = db.query(YourORM).filter(YourORM.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    update_data = item.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_item, field, value)
    
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/{item_id}")
async def delete_item(item_id: str, db: Session = Depends(get_db)):
    """Delete item"""
    db_item = db.query(YourORM).filter(YourORM.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db.delete(db_item)
    db.commit()
    return {"status": "deleted"}
```

#### 4. Register the Router
Edit `/web/app.py`:

```python
from web.routers import new_page_routes

# Add to app setup
app.include_router(new_page_routes.router)
```

#### 5. Create ORM Model (if needed)
Edit `/db/models.py`:

```python
class YourORM(Base):
    __tablename__ = "your_table_name"
    
    id = Column(String, primary_key=True, default=_uuid)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

Database will auto-create table on next run.

#### 6. Create Pydantic Schema (optional)
In router file:

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class YourSchema(BaseModel):
    title: str
    description: Optional[str] = None
    
    class Config:
        from_attributes = True

class YourSchemaUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        from_attributes = True
```

#### 7. Document the Page
Update `docs/PAGES.md` with:
- View ID and purpose
- UI structure (layout, sections)
- Database schema (tables, queries)
- Files modified
- API endpoints
- Key features

---

## Adding API Endpoints

### Endpoint Patterns

**List Endpoints:**
```python
@router.get("/")
async def list_items(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = None
):
    query = db.query(ItemORM)
    if status:
        query = query.filter(ItemORM.status == status)
    if search:
        query = query.filter(ItemORM.title.like(f"%{search}%"))
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return {"items": items, "total": total, "skip": skip, "limit": limit}
```

**Create Endpoints:**
```python
@router.post("/")
async def create_item(item: ItemSchema, db: Session = Depends(get_db)):
    db_item = ItemORM(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
```

**Get Endpoints:**
```python
@router.get("/{item_id}")
async def get_item(item_id: str, db: Session = Depends(get_db)):
    item = db.query(ItemORM).filter(ItemORM.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return item
```

**Update Endpoints:**
```python
@router.patch("/{item_id}")
async def update_item(
    item_id: str,
    item: ItemSchemaUpdate,
    db: Session = Depends(get_db)
):
    db_item = db.query(ItemORM).filter(ItemORM.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Not found")
    
    for field, value in item.dict(exclude_unset=True).items():
        setattr(db_item, field, value)
    
    db.commit()
    db.refresh(db_item)
    return db_item
```

**Delete Endpoints:**
```python
@router.delete("/{item_id}")
async def delete_item(item_id: str, db: Session = Depends(get_db)):
    db_item = db.query(ItemORM).filter(ItemORM.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Not found")
    
    db.delete(db_item)
    db.commit()
    return {"status": "deleted"}
```

### Response Codes

- **200 OK** — Successful GET/PATCH
- **201 Created** — Successful POST
- **204 No Content** — Successful DELETE
- **400 Bad Request** — Invalid input
- **404 Not Found** — Resource not found
- **500 Internal Server Error** — Unexpected error

---

## Database Modifications

### Adding a Table

1. **Create ORM Model** in `/db/models.py`:

```python
class NewTableORM(Base):
    __tablename__ = "new_table"
    
    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

2. **Table Auto-Creates** on first run (SQLAlchemy `create_all()` in `/db/init_db.py`)

3. **Query Examples**:

```python
# Create
new_item = NewTableORM(name="Example")
db.add(new_item)
db.commit()

# Read
item = db.query(NewTableORM).filter(NewTableORM.id == item_id).first()
all_items = db.query(NewTableORM).all()

# Update
item.name = "Updated"
db.commit()

# Delete
db.delete(item)
db.commit()

# Filter & Order
items = db.query(NewTableORM)\
    .filter(NewTableORM.status == "active")\
    .order_by(NewTableORM.created_at.desc())\
    .all()

# Join
results = db.query(NewTableORM, OtherORM)\
    .join(OtherORM, NewTableORM.other_id == OtherORM.id)\
    .all()

# Count
count = db.query(NewTableORM).filter(...).count()

# Paginate
items = db.query(NewTableORM).offset(skip).limit(limit).all()
```

### Field Types

```python
# Text fields
name = Column(String(255))           # Max 255 chars
description = Column(Text)           # Unlimited text
code = Column(String(50))            # Short code

# Numeric
count = Column(Integer)              # Whole numbers
percentage = Column(Integer)         # 0-100

# Dates & Times
due_date = Column(Date)              # YYYY-MM-DD
created_at = Column(DateTime)        # With timestamp

# Boolean
is_active = Column(Boolean, default=True)
is_read = Column(Boolean, default=False)

# JSON (stored as Text)
tags = Column(Text, default="[]")    # Store as JSON string
metadata = Column(Text, default="{}")

# Foreign Keys
project_id = Column(String, ForeignKey("projects.project_id", ondelete="CASCADE"))
user_id = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
```

### Relationships

```python
# One-to-Many
class ProjectORM(Base):
    __tablename__ = "projects"
    project_id = Column(String, primary_key=True)
    tasks = relationship("TaskORM", back_populates="project")

class TaskORM(Base):
    __tablename__ = "tasks"
    project_id = Column(String, ForeignKey("projects.project_id"))
    project = relationship("ProjectORM", back_populates="tasks")

# Usage
project = db.query(ProjectORM).first()
tasks = project.tasks  # Lazy-loaded or eager

# Many-to-Many (requires association table)
# Define in models.py then query
```

---

## Frontend Patterns

### Page Structure

```html
<div x-show="view === 'page-id'" style="flex:1;overflow-y:auto;padding:var(--content-padding-top) var(--content-padding-sides);box-sizing:border-box;">
  <!-- Header -->
  <h1 style="padding:var(--header-padding-top) var(--header-padding-sides) var(--header-padding-bottom);margin:0;">Page Title</h1>
  
  <!-- Filter Bar (optional) -->
  <div style="display:flex;gap:var(--card-gap);margin-bottom:var(--card-gap);">
    <input type="text" placeholder="Search..." x-model="search" style="padding:8px;border:1px solid #ddd;border-radius:4px;flex:1;">
    <button @click="applyFilters()" style="padding:8px 16px;background:#0066cc;color:white;border:none;border-radius:4px;cursor:pointer;">Filter</button>
  </div>
  
  <!-- Content Area -->
  <div style="display:flex;flex-direction:column;gap:var(--card-gap);">
    <!-- Cards -->
    <template x-for="item in items" :key="item.id">
      <div style="padding:var(--card-padding);border:var(--card-border-width) solid #ddd;border-left:var(--card-accent-border-width) solid #0066cc;border-radius:var(--card-border-radius);">
        <h3 style="margin:0 0 8px;">{{ item.title }}</h3>
        <p style="margin:0;color:#666;">{{ item.description }}</p>
      </div>
    </template>
  </div>
</div>
```

### Alpine.js Patterns

**Data Binding:**
```html
<input type="text" x-model="formData.title">
<p x-text="formData.title"></p>
```

**Conditional Rendering:**
```html
<div x-show="isLoading">Loading...</div>
<div x-show="!isLoading">Content</div>
```

**Loops:**
```html
<template x-for="item in items" :key="item.id">
  <div x-text="item.name"></div>
</template>
```

**Event Handling:**
```html
<button @click="handleClick()">Click me</button>
<input @change="handleChange($event)" type="text">
```

**Fetch Data:**
```javascript
// In x-init or @click handler
let response = await fetch('/api/items?status=todo');
let data = await response.json();
items = data.items;
```

### Styling Patterns

```html
<!-- Use Tailwind classes -->
<div class="flex gap-4 p-4 bg-blue-50 rounded">
  <h2 class="text-lg font-bold">Title</h2>
  <p class="text-gray-600">Subtitle</p>
</div>

<!-- Inline styles for dynamic content -->
<div style="display:flex;gap:var(--card-gap);">
  <!-- Content -->
</div>

<!-- Semantic variables for consistent spacing -->
<div style="padding:var(--content-padding-top) var(--content-padding-sides);">
  <!-- Content -->
</div>
```

---

## Backend Patterns

### Router Structure

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.base import get_db
from db.models import ItemORM
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/items", tags=["items"])

# Schemas
class ItemCreate(BaseModel):
    title: str
    description: Optional[str] = None
    
class ItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

# Endpoints
@router.get("/")
async def list_items(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None
):
    """List items with pagination and filtering"""
    query = db.query(ItemORM)
    
    if status:
        query = query.filter(ItemORM.status == status)
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return {"items": items, "total": total, "page": skip // limit + 1, "page_size": limit}

@router.post("/", status_code=201)
async def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """Create new item"""
    db_item = ItemORM(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.get("/{item_id}")
async def get_item(item_id: str, db: Session = Depends(get_db)):
    """Get specific item"""
    item = db.query(ItemORM).filter(ItemORM.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.patch("/{item_id}")
async def update_item(item_id: str, item: ItemUpdate, db: Session = Depends(get_db)):
    """Update item (partial)"""
    db_item = db.query(ItemORM).filter(ItemORM.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    for field, value in item.dict(exclude_unset=True).items():
        setattr(db_item, field, value)
    
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/{item_id}", status_code=204)
async def delete_item(item_id: str, db: Session = Depends(get_db)):
    """Delete item"""
    db_item = db.query(ItemORM).filter(ItemORM.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db.delete(db_item)
    db.commit()
```

### Error Handling

```python
# Return standard errors
raise HTTPException(status_code=400, detail="Invalid input")
raise HTTPException(status_code=404, detail="Not found")
raise HTTPException(status_code=409, detail="Conflict")

# Validation errors (automatic from Pydantic)
class Item(BaseModel):
    title: str  # Required
    priority: str = "medium"  # Optional with default
    due_date: Optional[str] = None  # Optional
```

---

## Testing

### Manual Testing

1. **Start server:**
   ```bash
   python3 start.py
   ```

2. **Interactive API docs:**
   ```
   http://localhost:8080/docs
   ```

3. **Test with curl:**
   ```bash
   curl http://localhost:8080/api/tasks
   curl -X POST http://localhost:8080/api/tasks \
     -H "Content-Type: application/json" \
     -d '{"title":"Test Task"}'
   ```

### Automated Testing (optional setup)

```bash
# Create tests/ directory
mkdir -p tests

# Create test file: tests/test_tasks.py
```

```python
import pytest
from fastapi.testclient import TestClient
from web.app import app

client = TestClient(app)

def test_list_tasks():
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert "items" in response.json()

def test_create_task():
    response = client.post("/api/tasks", json={"title": "Test"})
    assert response.status_code == 201
    assert response.json()["title"] == "Test"
```

Run tests:
```bash
pip install pytest
pytest tests/
```

---

## Common Tasks

### Update Styling Across All Pages

Edit `<style>` block in `/web/static/index.html`:

```css
:root {
  --header-padding-top: 0px;
  --header-padding-bottom: 10px;
  --header-padding-sides: 20px;
  --content-padding-top: 24px;
  --content-padding-sides: 28px;
  --card-gap: 12px;
  --card-padding: 10px 14px;
  --card-border-width: 1px;
  --card-accent-border-width: 2px;
  --card-border-radius: 10px;
}
```

### Add a Filter to a List

```python
# In router
@router.get("/")
async def list_items(
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None
):
    query = db.query(ItemORM)
    
    if status:
        query = query.filter(ItemORM.status == status)
    if priority:
        query = query.filter(ItemORM.priority == priority)
    if search:
        query = query.filter(ItemORM.title.like(f"%{search}%"))
    
    return {"items": query.all()}
```

### Add a New Status to a Model

1. Update ORM model in `/db/models.py`:
   ```python
   status = Column(String(50), default="pending")  # Add to field docs
   ```

2. Add validation in Pydantic schema:
   ```python
   from enum import Enum
   
   class StatusEnum(str, Enum):
       PENDING = "pending"
       ACTIVE = "active"
       COMPLETED = "completed"
   
   class ItemSchema(BaseModel):
       status: StatusEnum = StatusEnum.PENDING
   ```

### Cache a Query Result

```python
from web.deps import cache

@router.get("/expensive-operation")
async def expensive_query(db: Session = Depends(get_db)):
    # Check cache first
    cached = cache.get("expensive_key")
    if cached:
        return cached
    
    # Do expensive operation
    result = db.query(ItemORM).all()  # Expensive
    
    # Cache for 60 seconds
    cache.set("expensive_key", result, ttl=60)
    
    return result
```

---

## Code Organization

### Naming Conventions

- **Files:** `snake_case` (e.g., `task_routes.py`, `email_config.py`)
- **Classes:** `PascalCase` (e.g., `TaskORM`, `TaskSchema`)
- **Functions:** `snake_case` (e.g., `list_tasks`, `create_task`)
- **Variables:** `snake_case` (e.g., `task_id`, `due_date`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `DEFAULT_LIMIT`, `MAX_RETRIES`)
- **HTML IDs:** `kebab-case` (e.g., `task-form`, `filter-button`)
- **CSS Classes:** `kebab-case` (e.g., `task-card`, `header-title`)

### Imports Organization

```python
# 1. Standard library
import os
from datetime import datetime
from typing import Optional, List

# 2. Third-party
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

# 3. Local
from db.base import get_db
from db.models import TaskORM
```

### Comment Style

- No comments unless WHY is non-obvious
- Use clear names instead of explaining WHAT
- Document unusual constraints or gotchas

```python
# Good: Explains WHY
# Exclude soft-deleted items from public lists
db.query(ItemORM).filter(ItemORM.deleted_at == None)

# Bad: Explains WHAT (redundant)
# Filter items where deleted_at is null
db.query(ItemORM).filter(ItemORM.deleted_at == None)
```

---

## Troubleshooting Development

### Syntax Errors

```bash
# Check syntax
python3 -m py_compile web/routers/new_routes.py
```

### Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt

# Check Python path
echo $PYTHONPATH
```

### Database Issues

```bash
# Reset database
rm ~/.commanddesk/execos.db
python3 start.py  # Recreates with empty schema

# Check if tables exist
sqlite3 ~/.commanddesk/execos.db ".tables"
```

### API Not Responding

```bash
# Check if server is running
curl http://localhost:8080/health

# Check logs in terminal for error messages
# Restart server
python3 start.py
```

---

## Next Steps

- Read `docs/PAGES.md` for page-specific details
- Read `docs/API.md` for API reference
- Check existing routers for patterns
- Use `/docs` (Swagger) for testing endpoints
