# Releases Management Implementation

**Date:** 2026-05-07  
**Feature:** Add releases CRUD API and global dashboard view  
**Status:** Design approved

## Overview

Implement complete releases management system: API router with CRUD endpoints for global release tracking, and dashboard UI for viewing, creating, and editing releases. Releases belong to projects, track versions and status, and appear as a global list (not filtered by project).

## Current State → New State

| Aspect | Current | New |
|--------|---------|-----|
| Releases | ORM model exists, no API | Full CRUD API in `web/routers/releases.py` |
| Dashboard | No releases section | Global releases list with summary card |
| Features | None | Create/edit/delete releases, filter by status, search by name |

## Architecture

### API Endpoints

**Base path:** `/api/releases`

#### List Releases
```
GET /api/releases?project_id=<id>&status=<status>
```
- Returns: `List[ReleaseOut]` (all releases, optionally filtered)
- Query params (optional):
  - `project_id` — filter to specific project
  - `status` — filter by status (planned, in_progress, completed, cancelled)
- Response includes: release_id, name, version, project_id, project_name, application_id, due_date, status, description, created_at, updated_at, days_until_due

#### Create Release
```
POST /api/releases
Body: ReleaseIn
```
- Fields:
  - `name` (required, string, non-empty)
  - `version` (optional, string, default "")
  - `project_id` (optional, string, must exist in projects table if provided)
  - `application_id` (optional, string)
  - `due_date` (optional, date)
  - `status` (optional, string, default "planned")
  - `description` (optional, string, default "")
- Returns: `ReleaseOut` (201 Created)

#### Get Release
```
GET /api/releases/{release_id}
```
- Returns: `ReleaseOut` or 404

#### Update Release
```
PATCH /api/releases/{release_id}
Body: dict (partial ReleaseIn)
```
- Allowed fields: name, version, project_id, application_id, due_date, status, description
- Returns: `ReleaseOut` or 404

#### Delete Release
```
DELETE /api/releases/{release_id}
```
- Returns: 204 No Content or 404

### Pydantic Models

**ReleaseIn** (request):
```python
class ReleaseIn(BaseModel):
    name: str
    version: str = ""
    project_id: Optional[str] = None
    application_id: Optional[str] = None
    due_date: Optional[date] = None
    status: str = "planned"
    description: str = ""
```

**ReleaseOut** (response):
```python
class ReleaseOut(BaseModel):
    release_id: str
    name: str
    version: str
    project_id: Optional[str]
    project_name: Optional[str]  # Joined from ProjectORM
    application_id: Optional[str]
    due_date: Optional[date]
    status: str
    description: str
    days_until_due: Optional[int]  # Calculated
    is_overdue: bool  # Calculated
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
```

### Status Values

Valid status values (no validation constraint, can transition freely):
- `planned` — scheduled but not started
- `in_progress` — actively being worked on
- `completed` — finished and deployed
- `cancelled` — no longer needed

### Dashboard UI

**Navigation:**
- Add "Releases" nav item (icon: 📦 or 🚀) alongside Tasks, Projects, etc.

**Releases View:**
- Header: "Releases" title with "Create Release" button
- Table columns:
  - **Name** — text, clickable to open detail modal
  - **Version** — version string
  - **Project** — linked project name or "—" if unassigned
  - **Due Date** — formatted date with overdue/due-today highlighting
  - **Status** — badge (color-coded: planned=blue, in_progress=yellow, completed=green, cancelled=gray)
  - **Actions** — edit and delete icons
- **Sorting:** by due_date (ascending), then by created_at
- **Filtering:** 
  - Status filter (dropdown: all/planned/in_progress/completed/cancelled)
  - Search by name (fuzzy match)

**Create/Edit Modal:**
- Form fields:
  - Name (required text input)
  - Version (optional text input)
  - Project (optional dropdown, linked to projects)
  - Due Date (optional date picker)
  - Status (dropdown: planned/in_progress/completed/cancelled)
  - Description (optional textarea)
- Submit button validates name is non-empty
- On success: close modal, refresh table, show success message

**Summary Card:**
- Location: dashboard home card
- Shows:
  - Total releases
  - Counts by status (planned, in_progress, completed, cancelled)
  - Count of overdue releases
  - "View all" link to Releases view

### Data Flow

1. **Mutations trigger cache bust** — any create/update/delete calls `_bust_dash()` to clear dashboard caches
2. **Project lookup** — GET releases joins with ProjectORM to populate project_name
3. **Calculated fields**:
   - `days_until_due` = due_date - today (null if no due_date)
   - `is_overdue` = due_date < today and status != completed|cancelled
4. **Foreign key handling**:
   - If project_id provided, must exist in projects table (400 error if not)
   - If project is deleted, release retains orphaned project_id (no cascade delete, release survives)

### Error Handling

| Scenario | Response |
|----------|----------|
| Empty name | 400: "name must not be empty" |
| Invalid project_id | 400: "project not found" |
| Release not found | 404: "release not found" |
| Delete non-existent release | 404: "release not found" |
| Update non-existent release | 404: "release not found" |

### Testing

1. **CRUD operations:**
   - Create release with all fields → verify stored correctly
   - Create release with minimal fields → defaults applied
   - Update release → only specified fields change
   - Delete release → removed from DB
   - Get non-existent release → 404

2. **Validation:**
   - Empty name → 400 error
   - Invalid project_id → 400 error
   - Valid project_id → stored correctly

3. **Filtering:**
   - Filter by status → returns only matching releases
   - Filter by project_id → returns only that project's releases
   - Search by name → fuzzy match works

4. **Dashboard:**
   - Summary card shows correct counts
   - Table displays all releases in correct order
   - Create/edit modals save changes correctly
   - Delete removes from table

5. **Cache:**
   - Dashboard cache clears on release mutation
   - Subsequent dashboard load shows new data

## Success Criteria

- [x] Releases API fully functional (CRUD endpoints working)
- [x] All validation errors return appropriate 4xx codes
- [x] Dashboard displays global release list with filters and search
- [x] Create/edit/delete modals work end-to-end
- [x] Summary card shows release statistics
- [x] Dashboard cache busts on mutations
- [x] All tests passing (no regressions)
