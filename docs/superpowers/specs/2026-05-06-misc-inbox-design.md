# Misc/Inbox Section Design

**Date:** 2026-05-06  
**Feature:** Dedicated inbox for random, unassigned tasks  
**Status:** Design approved

## Overview

Add a dedicated Inbox section for tasks that aren't assigned to any project. Misc tasks are completely unassigned (`project_id IS NULL` and `application_id IS NULL`) until they're promoted to a real project-based task.

The Inbox appears as:
1. A navigation item in the left sidebar
2. A summary card on the operational dashboard with priority breakdown and due-date urgency indicators

## Core Concept: What is a Misc Task?

A misc task is defined by:
- `project_id IS NULL`
- `application_id IS NULL`

No special flag or "misc" column needed. This is purely based on the absence of project/application assignment.

### Task Lifecycle

**Creation:** User creates a task without selecting a project → lands in Inbox automatically  
**In Inbox:** Task sits unassigned, can be filtered by priority and due date  
**Promotion:** User edits task, selects a project → system auto-assigns the project's application_id, task moves out of Inbox into Projects view  
**Demotion:** User edits task, removes the project → task returns to Inbox

## UI Components

### 1. Sidebar Navigation Entry

**Location:** Left nav, between "Tasks" and "Projects"  
**Label:** "Inbox"  
**Icon:** Suggested 📥 or 🎯  
**Click behavior:** Navigate to the Inbox view (similar to Tasks and Projects)  
**Styling:** Match existing nav item styling (purple gradient, text truncation, hover effects)

### 2. Inbox View (Full Page)

**URL:** `/inbox` (or nav item routes to this)  
**Scope:** Display only tasks where `project_id IS NULL AND application_id IS NULL`

**Layout:**
- Header: "Inbox" title with task count badge
- Quick create button: "+ Add to Inbox" (opens task modal without Project/Application fields)
- Filterable table:
  - **Columns:** Title, Priority, Due Date, Assignee, Actions (✏️ Edit, 🗑 Delete)
  - **Search:** Filter by task title/description
  - **Priority filter:** Dropdown to show Critical/High/Medium/Low only
  - **Sort:** By due date (soonest first)

**Interaction:**
- Click row or edit button → opens task modal
- Modal shows: Title, Description, Priority, Status, Due Date, Reminder Date, Assignee, Tags
- Modal DOES NOT show: Project, Application (these are null by definition)
- If user adds a project during edit → task is immediately removed from Inbox view (refresh on save)

### 3. Dashboard Card (Operational View)

**Location:** Operational dashboard, alongside other summary cards  
**Title:** "Inbox"  
**Display Content:**
- **Priority Breakdown:** "2 critical, 1 high, 2 medium" (count of tasks by priority)
- **Due Urgency Indicator:**
  - If any tasks are overdue: Red badge with count, e.g., "1 overdue"
  - If any tasks are due today: Yellow badge with count, e.g., "2 due today"
  - If neither: Display total count in neutral color

**Example card display:**
```
┌─────────────────┐
│ Inbox           │
│ 2 critical      │
│ 1 high          │
│ 2 medium        │
│                 │
│ 1 overdue ❌    │
│ 2 due today ⚠️  │
└─────────────────┘
```

**Click behavior:** Navigate to full Inbox view

**Caching:** Same as operational dashboard (60s TTL in-memory cache)

## API Changes

**No new endpoints needed.** Use existing task endpoints with filter:

### List Inbox Tasks
```
GET /api/tasks?project_id=null
```
(Backend filters where `project_id IS NULL AND application_id IS NULL`)

### Create Misc Task
```
POST /api/tasks
{
  "title": "...",
  "description": "...",
  "priority": "medium",
  "status": "todo",
  "project_id": null,
  "application_id": null,
  "assignee_id": null,
  "tags": [],
  "due_date": null
}
```

### Promote Misc Task (Update with Project)
```
PATCH /api/tasks/{task_id}
{
  "project_id": "proj-123"
}
```
Backend **must** auto-set `application_id` from `projects.application_id` when project_id is updated.

## Database Schema

**No changes required.** Tasks table already has:
- `project_id` (nullable)
- `application_id` (nullable)

Misc tasks are identified by querying `WHERE project_id IS NULL AND application_id IS NULL`.

## Implementation Sequence

1. **Backend:** Update task update endpoint to auto-assign application_id when project_id changes
2. **Frontend:** Add Inbox nav item, implement Inbox view page
3. **Frontend:** Add Inbox card to operational dashboard with priority/due breakdown
4. **Frontend:** Update task modal to omit Project/Application fields when creating/editing in Inbox

## Success Criteria

- [x] Users can create tasks without a project (lands in Inbox)
- [x] Inbox appears in left nav and links to dedicated view
- [x] Inbox view shows all unassigned tasks with filters (priority, search)
- [x] Dashboard card shows priority breakdown + due urgency
- [x] Editing a misc task + adding a project moves it out of Inbox
- [x] Removing a project from a task moves it back to Inbox

## Edge Cases

**What if user creates a task with project but no application?**  
→ System auto-assigns the project's application_id. Task is not a misc task.

**What if user creates a task with application but no project?**  
→ This shouldn't happen (application only via project selection). UI doesn't allow this. If it does via API, task does not appear in Inbox (has application_id set).

**What if application_id is set but project_id is null?**  
→ Not a misc task by definition. Would not appear in Inbox. (Shouldn't occur in normal flow.)

## Future Enhancements (Out of Scope)

- Drag-drop to assign projects to misc tasks
- Bulk operations (mark done, assign multiple to project)
- Smart inbox (auto-categorization or quick-add suggestions)
- Email forwarding to inbox (Phase 2)
