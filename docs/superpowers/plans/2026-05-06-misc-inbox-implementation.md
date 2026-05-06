# Misc/Inbox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated Inbox section for unassigned tasks, accessible via sidebar nav and dashboard summary card.

**Architecture:** Misc tasks are identified purely by `project_id IS NULL AND application_id IS NULL`. When a task is updated with a project, the backend auto-assigns the project's application. No special "misc" flag needed. Frontend has a dedicated Inbox nav item + view page + dashboard card.

**Tech Stack:** FastAPI (backend), Alpine.js + Tailwind (frontend), SQLAlchemy ORM

---

## Task 1: Backend — Auto-Assign Application When Project Changes

**Files:**
- Modify: `web/routers/tasks.py:122-140` (update_task function)

When a user updates a task's project_id via PATCH, auto-assign the project's application_id.

- [ ] **Step 1: Read the current update_task function**

File: `web/routers/tasks.py`, lines 122-140

Current code:
```python
@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: str, body: dict, db: Session = Depends(get_db)):
    t = db.query(TaskORM).filter(TaskORM.task_id == task_id).first()
    if not t:
        raise HTTPException(404, "task not found")
    allowed = {"title", "description", "due_date", "reminder_date", "priority", "status", "project_id", "application_id", "assignee_id", "tags"}
    for k, v in body.items():
        if k not in allowed:
            continue
        if k == "tags":
            v = json.dumps(v)
        if k in ("due_date", "reminder_date") and isinstance(v, str):
            v = date.fromisoformat(v) if v else None
        setattr(t, k, v)
    t.updated_at = datetime.utcnow()
    if body.get("status") == "done" and not t.completed_at:
        t.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(t)
```

- [ ] **Step 2: Add auto-assignment logic after the loop**

After the field assignment loop (after `setattr`), add logic to auto-assign application_id if project_id was changed:

```python
@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: str, body: dict, db: Session = Depends(get_db)):
    t = db.query(TaskORM).filter(TaskORM.task_id == task_id).first()
    if not t:
        raise HTTPException(404, "task not found")
    allowed = {"title", "description", "due_date", "reminder_date", "priority", "status", "project_id", "application_id", "assignee_id", "tags"}
    for k, v in body.items():
        if k not in allowed:
            continue
        if k == "tags":
            v = json.dumps(v)
        if k in ("due_date", "reminder_date") and isinstance(v, str):
            v = date.fromisoformat(v) if v else None
        setattr(t, k, v)
    
    # Auto-assign application_id if project_id is set
    if "project_id" in body and body["project_id"]:
        proj = db.query(ProjectORM).filter(ProjectORM.project_id == body["project_id"]).first()
        if proj:
            t.application_id = proj.application_id
    # Clear application_id if project_id is being cleared
    elif "project_id" in body and not body["project_id"]:
        t.application_id = None
    
    t.updated_at = datetime.utcnow()
    if body.get("status") == "done" and not t.completed_at:
        t.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(t)
    _bust_dash()
    return _to_out(t)
```

Note: Import ProjectORM at the top of the file if not already imported:
```python
from db.models import TaskORM, ProjectORM
```

- [ ] **Step 3: Test the endpoint with curl**

Start the dev server:
```bash
python3 start.py
```

Create a test task first (via POST):
```bash
curl -X POST http://localhost:8080/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Task","priority":"medium"}'
```

Note the returned `task_id`.

Get an existing project:
```bash
curl http://localhost:8080/api/projects | jq '.[] | {project_id, application_id}' | head -1
```

Update the task with that project_id:
```bash
curl -X PATCH http://localhost:8080/api/tasks/{task_id} \
  -H "Content-Type: application/json" \
  -d '{"project_id":"proj-xxxxx"}'
```

Verify the response includes the auto-assigned `application_id` matching the project's application_id.

- [ ] **Step 4: Commit**

```bash
git add web/routers/tasks.py
git commit -m "feat: auto-assign application_id when task project changes"
```

---

## Task 2: Frontend — Add Inbox Navigation Item

**Files:**
- Modify: `web/static/index.html` (left nav section, around line 424-450)

- [ ] **Step 1: Find the nav item section**

Search for the nav structure around line 424. Current code looks like:
```html
<div @click="nav('tasks')" :class="navCls('tasks')">
  <div class="nav-icon">✅</div>
  <span style="flex:1">Tasks</span>
</div>
<div @click="nav('projects')" :class="navCls('projects')">
  <div class="nav-icon">📊</div>
  <span style="flex:1">Projects</span>
</div>
```

- [ ] **Step 2: Add Inbox nav item between Tasks and Projects**

Insert this HTML between the Tasks and Projects nav items:

```html
<div @click="nav('inbox')" :class="navCls('inbox')">
  <div class="nav-icon">📥</div>
  <span style="flex:1">Inbox</span>
</div>
```

- [ ] **Step 3: Find and update the navCls function**

Search for `navCls(` function (around line 4700+). Add 'inbox' to the checks:

Current logic checks things like `page === 'tasks'`, `page === 'projects'`. The function should already handle any page name, so verify it includes something like:

```javascript
navCls(name) {
  let cls = "nav-item";
  if(this.page === name) cls += " nav-item-active";
  return cls;
}
```

If it exists, no changes needed. If not, add it.

- [ ] **Step 4: Verify the nav item appears**

The nav system should already route based on `this.page`. We'll add the Inbox view content in Task 3.

- [ ] **Step 5: Commit**

```bash
git add web/static/index.html
git commit -m "feat: add Inbox nav item to sidebar"
```

---

## Task 3: Frontend — Create Inbox View Page

**Files:**
- Modify: `web/static/index.html` (add new view section and Alpine.js component)

The Inbox view should display unassigned tasks (project_id = null) in a table similar to the Tasks view.

- [ ] **Step 1: Add Inbox view HTML section**

Find where the Tasks view ends (search for `x-show="page === 'tasks'"`, around line 600-800). After that section closes, add:

```html
<!-- ══ INBOX VIEW ══ -->
<div x-show="page === 'inbox'" style="flex:1;display:flex;flex-direction:column;">
  <div style="padding:20px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;">
    <h2 style="margin:0;font-size:24px;font-weight:800;">Inbox</h2>
    <button @click="openTaskModal()" class="btn-primary">+ New</button>
  </div>
  <div style="flex:1;overflow:auto;padding:20px;">
    <div style="margin-bottom:20px;display:flex;gap:12px;flex-wrap:wrap;">
      <input type="text" x-model="inboxFilters.search" placeholder="Search inbox..." class="input" style="flex:1;min-width:200px;" />
      <select x-model="inboxFilters.priority" class="input">
        <option value="">All Priorities</option>
        <option value="critical">Critical</option>
        <option value="high">High</option>
        <option value="medium">Medium</option>
        <option value="low">Low</option>
      </select>
    </div>
    <table class="tasks-table">
      <thead>
        <tr>
          <th>Title</th>
          <th>Priority</th>
          <th>Due Date</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <template x-for="t in inboxTasks" :key="t.task_id">
          <tr>
            <td x-text="t.title"></td>
            <td><span :class="'priority-'+t.priority" x-text="t.priority"></span></td>
            <td x-text="t.due_date || '-'"></td>
            <td x-text="t.status"></td>
            <td style="display:flex;gap:8px;">
              <button @click="openTaskModal(t)" class="btn-icon" title="Edit">✏️</button>
              <button @click="deleteTask(t.task_id)" class="btn-icon" title="Delete" style="color:#ef4444;">🗑</button>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
    <div x-show="inboxTasks.length === 0" style="text-align:center;padding:40px;color:var(--text-2);">
      <p>No inbox tasks. You're all caught up! 🎉</p>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Add inboxTasks computed property**

Find the data() function (around line 4520). Add these properties to the returned object:

```javascript
inboxFilters: { search: '', priority: '' },
inboxTasks: [],
```

- [ ] **Step 3: Add inboxTasks filtering logic**

Find the filterTasks() function (around line 4747). Add this computed method to the app object (in the methods section, around line 4680+):

```javascript
filterInbox() {
  let ts = this.tasks.filter(t => !t.project_id && !t.application_id);
  if(this.inboxFilters.search) {
    const q = this.inboxFilters.search.toLowerCase();
    ts = ts.filter(t => t.title.toLowerCase().includes(q) || t.description.toLowerCase().includes(q));
  }
  if(this.inboxFilters.priority) {
    ts = ts.filter(t => t.priority === this.inboxFilters.priority);
  }
  this.inboxTasks = ts.sort((a,b) => {
    if(a.due_date && b.due_date) return new Date(a.due_date) - new Date(b.due_date);
    if(a.due_date) return -1;
    if(b.due_date) return 1;
    return 0;
  });
}
```

- [ ] **Step 4: Call filterInbox whenever tasks or filters change**

In the loadTasks() function (around line 4683), after loading tasks, add:
```javascript
await this.loadTasks(); 
this.filterInbox();
```

In the data() initialization (where you set up watchers if using Alpine), add a watcher for the filter inputs. Find where x-model="inboxFilters.search" is used and add @change="filterInbox()" to the input:

```html
<input type="text" x-model="inboxFilters.search" @change="filterInbox()" placeholder="Search inbox..." ... />
<select x-model="inboxFilters.priority" @change="filterInbox()" class="input">
```

- [ ] **Step 5: Test the Inbox view**

Start the dev server:
```bash
python3 start.py
```

Navigate to http://localhost:8080, click "Inbox" in the left nav. You should see:
- Empty state message (if no unassigned tasks exist)
- Search and priority filter inputs
- "+ New" button

Create a task without a project (click "+ New" from Inbox, don't select a project), and verify it appears in the Inbox table.

- [ ] **Step 6: Commit**

```bash
git add web/static/index.html
git commit -m "feat: add Inbox view page with task table and filters"
```

---

## Task 4: Frontend — Update Task Modal for Inbox Context

**Files:**
- Modify: `web/static/index.html` (task modal section, around line 4143-4220)

When creating/editing a task from Inbox, hide the Project and Application dropdowns (they're null by definition).

- [ ] **Step 1: Update openTaskModal function**

Find the openTaskModal function (around line 4755). Update it to set an "inboxMode" flag:

```javascript
openTaskModal(task) {
  const inboxMode = this.page === 'inbox';
  if(task) {
    this.taskModal={open:true,editing:true,inboxMode:inboxMode,data:{...task,due_date:task.due_date||'',reminder_date:task.reminder_date||'',project_id:task.project_id||'',application_id:task.application_id||''}};
  } else {
    this.taskModal={open:true,editing:false,inboxMode:inboxMode,data:{title:'',description:'',priority:'medium',status:'todo',due_date:'',reminder_date:'',project_id:'',application_id:''}};
  }
}
```

- [ ] **Step 2: Add inboxMode to taskModal data**

In the data() function (around line 4521), update taskModal initialization:

```javascript
taskModal: { open:false, editing:false, inboxMode:false, data:{} },
```

- [ ] **Step 3: Hide Project and Application dropdowns in Inbox mode**

Find the task modal HTML (around line 4198-4210). Wrap the Application and Project selects in conditional visibility:

```html
<!-- Application dropdown — hidden in Inbox -->
<div x-show="!taskModal.inboxMode">
  <label style="display:block;font-size:12px;font-weight:600;color:var(--text-2);margin-bottom:6px;">Application</label>
  <select x-model="taskModal.data.application_id" @change="taskModal.data.project_id=''" class="input">
    <option value="">Select application...</option>
    <template x-for="a in apps" :key="a.application_id">
      <option :value="a.application_id" x-text="a.name"></option>
    </template>
  </select>
</div>

<!-- Project dropdown — hidden in Inbox -->
<div x-show="!taskModal.inboxMode">
  <label style="display:block;font-size:12px;font-weight:600;color:var(--text-2);margin-bottom:6px;">Project</label>
  <select x-model="taskModal.data.project_id" class="input">
    <option value="">Select project...</option>
    <template x-for="p in projects.filter(p=>!taskModal.data.application_id || p.application_id===taskModal.data.application_id)" :key="p.project_id">
      <option :value="p.project_id" x-text="p.name"></option>
    </template>
  </select>
</div>
```

- [ ] **Step 4: Test creating an Inbox task**

Navigate to Inbox, click "+ New". Verify:
- Modal opens with inboxMode = true
- Application and Project dropdowns are **hidden**
- Title, Description, Priority, Status, Due Date, Reminder, Assignee, Tags fields are visible
- Click Save creates a task with project_id=null and application_id=null

Then navigate to the Tasks view, edit the same task, and verify the Application and Project dropdowns **are visible** (inboxMode=false).

- [ ] **Step 5: Commit**

```bash
git add web/static/index.html
git commit -m "feat: hide project/app fields in task modal when in Inbox"
```

---

## Task 5: Frontend — Add Inbox Dashboard Card

**Files:**
- Modify: `web/static/index.html` (operational dashboard section)

Add an Inbox card to the operational dashboard showing priority breakdown and due-date urgency.

- [ ] **Step 1: Find the operational dashboard section**

Search for the dashboard view (around line 500-600, look for `x-show="page === 'dashboard'"`). Find where the cards are rendered (look for existing cards like Tasks, Projects, Overdue, etc.).

- [ ] **Step 2: Add inboxStats to data**

In the data() function (around line 4521), add:

```javascript
inboxStats: {
  critical: 0,
  high: 0,
  medium: 0,
  low: 0,
  overdue: 0,
  dueToday: 0,
}
```

- [ ] **Step 3: Add method to calculate Inbox stats**

Add this method to the app's methods section (around line 4680+):

```javascript
calculateInboxStats() {
  const today = new Date().toISOString().split('T')[0];
  const inbox = this.tasks.filter(t => !t.project_id && !t.application_id);
  
  this.inboxStats = {
    critical: inbox.filter(t => t.priority === 'critical').length,
    high: inbox.filter(t => t.priority === 'high').length,
    medium: inbox.filter(t => t.priority === 'medium').length,
    low: inbox.filter(t => t.priority === 'low').length,
    overdue: inbox.filter(t => t.due_date && t.due_date < today && t.status !== 'done').length,
    dueToday: inbox.filter(t => t.due_date === today && t.status !== 'done').length,
  };
}
```

- [ ] **Step 4: Call calculateInboxStats in loadTasks**

In loadTasks() (around line 4683), after loading tasks and filtering:

```javascript
async loadTasks() {
  try { 
    this.tasks = await fetch('/api/tasks').then(r => r.json()); 
    this.filterTasks();
    this.filterInbox();
    this.calculateInboxStats();
  } catch(e) {}
}
```

- [ ] **Step 5: Add Inbox card to operational dashboard**

Find the dashboard card section (around line 520-580). Add this card among the other summary cards (good place is after the Overdue/Due Today cards):

```html
<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:16px;cursor:pointer;" @click="nav('inbox')">
  <div style="font-size:13px;font-weight:700;color:#16a34a;margin-bottom:12px;">INBOX</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
    <div>
      <div style="font-size:11px;color:var(--text-2);margin-bottom:4px;">Critical</div>
      <div style="font-size:20px;font-weight:800;" x-text="inboxStats.critical"></div>
    </div>
    <div>
      <div style="font-size:11px;color:var(--text-2);margin-bottom:4px;">High</div>
      <div style="font-size:20px;font-weight:800;" x-text="inboxStats.high"></div>
    </div>
    <div>
      <div style="font-size:11px;color:var(--text-2);margin-bottom:4px;">Medium</div>
      <div style="font-size:20px;font-weight:800;" x-text="inboxStats.medium"></div>
    </div>
    <div>
      <div style="font-size:11px;color:var(--text-2);margin-bottom:4px;">Low</div>
      <div style="font-size:20px;font-weight:800;" x-text="inboxStats.low"></div>
    </div>
  </div>
  <div style="border-top:1px solid #bbf7d0;padding-top:12px;display:flex;gap:12px;">
    <div x-show="inboxStats.overdue > 0" style="display:flex;align-items:center;gap:6px;font-size:12px;color:#dc2626;">
      <span style="font-weight:700;" x-text="inboxStats.overdue + ' overdue'"></span>❌
    </div>
    <div x-show="inboxStats.dueToday > 0" style="display:flex;align-items:center;gap:6px;font-size:12px;color:#f59e0b;">
      <span style="font-weight:700;" x-text="inboxStats.dueToday + ' due today'"></span>⚠️
    </div>
  </div>
</div>
```

- [ ] **Step 6: Test the dashboard card**

Start the dev server:
```bash
python3 start.py
```

Navigate to Dashboard. You should see the Inbox card showing:
- Priority counts (critical, high, medium, low)
- Red "overdue" badge if any tasks are overdue
- Yellow "due today" badge if any tasks are due today
- Clicking the card should navigate to the Inbox view

Create some unassigned test tasks with different priorities and due dates to verify the stats update correctly.

- [ ] **Step 7: Commit**

```bash
git add web/static/index.html
git commit -m "feat: add Inbox summary card to operational dashboard"
```

---

## Summary

**Architecture changes:**
- No database schema changes (misc = project_id IS NULL)
- Backend: Auto-assign application_id when project_id is set
- Frontend: Inbox nav item, dedicated view page, dashboard card, modal context awareness

**Files modified:**
- `web/routers/tasks.py` — Auto-assignment logic
- `web/static/index.html` — All frontend components

**Key concepts:**
- Inbox = unassigned tasks (no project, no app)
- Promotion: Add project → auto-assign app, move out of Inbox
- Demotion: Remove project → move back to Inbox
- Dashboard card shows priority breakdown + due urgency

**Testing checklist:**
- [ ] Create task in Inbox (no project/app)
- [ ] Filter Inbox by priority and search
- [ ] Edit Inbox task, add project → auto-assigns app
- [ ] Remove project from task → returns to Inbox
- [ ] Dashboard card shows correct stats
- [ ] All tests pass: `pytest tests/ -v`
