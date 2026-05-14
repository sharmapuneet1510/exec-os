# ExecOS Pages Documentation

Complete documentation for all 27 pages in ExecOS with database schema, UI structure, and backend API details.

## Table of Contents

### Card-Based Pages (12 pages)
1. [My Book of Work](#my-book-of-work)
2. [Day Planner](#day-planner)
3. [Tasks](#tasks)
4. [Projects](#projects)
5. [Milestones](#milestones)
6. [Releases](#releases)
7. [Commitments](#commitments)
8. [Alerts](#alerts)
9. [Applications](#applications)
10. [Project Tracker](#project-tracker)
11. [Release Tracker](#release-tracker)
12. [Summaries](#summaries)

### Dashboard/Grid Pages (3 pages)
13. [Dashboard](#dashboard)
14. [Operational](#operational)
15. [Executive](#executive)

### Form/Admin Pages (4 pages)
16. [Admin Settings](#admin-settings)
17. [Email Briefing](#email-briefing)
18. [Activity Log](#activity-log)
19. [API Tokens](#api-tokens)

### Table/List Pages (4 pages)
20. [Team List](#team-list)
21. [Team Workload](#team-workload)
22. [Resourcing](#resourcing)
23. [Estimate](#estimate)

### Specialized Pages (4 pages)
24. [Sprint Board](#sprint-board)
25. [Proj Planner](#proj-planner)
26. [Delivery](#delivery)
27. [Inbox](#inbox)

---

## Card-Based Pages

### My Book of Work
**View ID:** `my-work`  
**Purpose:** Display tasks assigned to current user with quick action buttons

#### UI Structure
- Header: "My Book of Work" with filter/sort options
- Main content: Card grid layout
  - Each card displays: task title, project, due date, priority badge, status indicator
  - Card actions: Edit, Complete, Postpone, Delete

#### Database Schema
```sql
-- Primary table: tasks
SELECT task_id, title, description, due_date, priority, status, project_id, tags
FROM tasks
WHERE status != 'done'  -- Active tasks only
ORDER BY due_date ASC;

-- Related: projects
SELECT project_id, name FROM projects;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "My Work View" (~line 1200)
- **Backend:** `/web/routers/tasks.py` - GET /api/tasks endpoint
- **Styling:** CSS variables in `<style>` block (header-padding, card-gap, card-padding)

#### API Endpoints
```
GET    /api/tasks?status=todo,in_progress&sort=due_date
GET    /api/tasks/{task_id}
PATCH  /api/tasks/{task_id}
DELETE /api/tasks/{task_id}
POST   /api/tasks
```

#### Key Features
- Filter by priority, status, project
- Sort by due date, priority, created date
- Quick actions: Edit, Complete, Postpone
- Bulk status update

---

### Day Planner
**View ID:** `planner`  
**Purpose:** Time-block based daily planning view

#### UI Structure
- Header: Date selector, add event button
- Main content: Timeline grid
  - Time slots: 30-min or 1-hour intervals
  - Drag-and-drop to reschedule
  - Color-coded by type (task, meeting, break, focus)

#### Database Schema
```sql
-- Primary table: day_plan_items
SELECT item_id, plan_date, time_start, time_end, title, item_type, 
       task_id, notes, completed, source
FROM day_plan_items
WHERE plan_date = CURRENT_DATE
ORDER BY time_start ASC;

-- Related: tasks
SELECT task_id, title, priority, due_date FROM tasks;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Day Planner View" (~line 1350)
- **Backend:** `/web/routers/planner_routes.py` - GET /api/day-plan endpoints
- **Styling:** Use `--content-padding-*` and `--card-gap` variables

#### API Endpoints
```
GET    /api/day-plan?date=YYYY-MM-DD
POST   /api/day-plan
GET    /api/day-plan/{item_id}
PATCH  /api/day-plan/{item_id}
DELETE /api/day-plan/{item_id}
```

#### Key Features
- Drag-and-drop rescheduling
- Auto-fill from calendar (Outlook ICS)
- Break detection and reminders
- Daily completion tracking

---

### Tasks
**View ID:** `tasks`  
**Purpose:** Comprehensive task management with advanced filtering and CRUD

#### UI Structure
- Header: "Tasks" with search bar, filter dropdowns (status, priority, project)
- Main content: 
  - Table or card grid view (user preference)
  - Sortable columns: Title, Project, Due Date, Priority, Status
  - Modal for create/edit task

#### Database Schema
```sql
-- Primary table: tasks
SELECT task_id, title, description, due_date, priority, status, 
       project_id, assignee_id, tags, created_at, completed_at
FROM tasks
ORDER BY due_date ASC;

-- Related: projects
SELECT project_id, name FROM projects WHERE status = 'active';

-- Related: team_members
SELECT member_id, name, email FROM team_members WHERE is_active = TRUE;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Tasks View" (~line 1450)
- **Backend:** `/web/routers/tasks.py` - All task CRUD endpoints
- **Styling:** Apply `--card-padding`, `--card-border-width` variables

#### API Endpoints
```
GET    /api/tasks?status=&priority=&project_id=&assignee_id=&search=
POST   /api/tasks
GET    /api/tasks/{task_id}
PATCH  /api/tasks/{task_id}
DELETE /api/tasks/{task_id}
GET    /api/tasks/search?q=query
```

#### Key Features
- Advanced filtering (multi-select)
- Bulk operations (change status, priority, assign)
- Task cloning and templates
- Custom tagging system
- Due date and priority indicators

---

### Projects
**View ID:** `projects`  
**Purpose:** View and manage all projects

#### UI Structure
- Header: "Projects" with "New Project" button
- Main content: Project cards
  - Each card: name, description, status badge, owner, progress bar
  - Quick actions: Edit, View Tasks, Archive/Delete

#### Database Schema
```sql
-- Primary table: projects
SELECT project_id, name, description, status, owner, 
       start_date, due_date, created_at, updated_at
FROM projects
ORDER BY updated_at DESC;

-- Count tasks per project
SELECT project_id, COUNT(*) as total_tasks,
       COUNT(CASE WHEN status = 'done' THEN 1 END) as completed_tasks
FROM tasks
GROUP BY project_id;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Projects View" (~line 1600)
- **Backend:** `/web/routers/projects.py` - GET /api/projects endpoint
- **Styling:** Card border styling with `--card-accent-border-width` for left border

#### API Endpoints
```
GET    /api/projects?status=active,on_hold
POST   /api/projects
GET    /api/projects/{project_id}
PATCH  /api/projects/{project_id}
DELETE /api/projects/{project_id}
GET    /api/projects/{project_id}/health
```

#### Key Features
- Project health scoring (based on task completion %)
- Progress tracking
- Team member assignment
- Milestone association
- Custom tags

---

### Milestones
**View ID:** `milestones`  
**Purpose:** Track project milestones

#### UI Structure
- Header: "Milestones" with "New Milestone" button
- Main content: List view
  - Columns: Title, Project, Release, Due Date, Status, Days Remaining
  - Overdue highlighting (red background for past due_date)

#### Database Schema
```sql
-- Primary table: milestones
SELECT milestone_id, title, description, project_id, release_id, 
       due_date, status, created_at
FROM milestones
ORDER BY due_date ASC;

-- Join with projects and releases
SELECT m.*, p.name as project_name, r.name as release_name
FROM milestones m
LEFT JOIN projects p ON m.project_id = p.project_id
LEFT JOIN releases r ON m.release_id = r.release_id;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Milestones View" (~line 1750)
- **Backend:** `/web/routers/milestones.py` - Milestone CRUD endpoints
- **Styling:** Apply overdue styling (red border/background) in CSS

#### API Endpoints
```
GET    /api/milestones?project_id=&status=
POST   /api/milestones
GET    /api/milestones/{milestone_id}
PATCH  /api/milestones/{milestone_id}
DELETE /api/milestones/{milestone_id}
```

#### Key Features
- Overdue detection and highlighting
- Release association
- Status tracking (pending, in_progress, completed, at_risk)
- Days remaining calculation

---

### Releases
**View ID:** `releases`  
**Purpose:** Manage product releases and versions

#### UI Structure
- Header: "Releases" with "New Release" button
- Main content: Card or timeline view
  - Card fields: Version, Project, Status, UAT Date, Sign-off Date
  - Timeline showing release schedule

#### Database Schema
```sql
-- Primary table: releases
SELECT release_id, name, version, project_id, due_date, 
       start_date, uat_date, sign_off_date, status, created_at
FROM releases
ORDER BY due_date ASC;

-- Count milestones per release
SELECT release_id, COUNT(*) as milestone_count
FROM milestones
GROUP BY release_id;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Release Tracker View" (~line 1900)
- **Backend:** `/web/routers/releases.py` - Release CRUD endpoints
- **Styling:** Timeline layout styling in CSS

#### API Endpoints
```
GET    /api/releases?project_id=&status=
POST   /api/releases
GET    /api/releases/{release_id}
PATCH  /api/releases/{release_id}
DELETE /api/releases/{release_id}
GET    /api/releases/{release_id}/milestones
```

#### Key Features
- Version management
- Release status tracking (planned, in_progress, released, rollback)
- Date milestones (UAT, Sign-off)
- Milestone grouping
- Release notes

---

### Commitments
**View ID:** `commitments`  
**Purpose:** Track promises and commitments

#### UI Structure
- Header: "Commitments" with "New Commitment" button
- Main content: List or card view
  - Status indicator: Pending (yellow), Fulfilled (green), Missed (red)
  - Fields: Title, Due Date, Status, Days Remaining

#### Database Schema
```sql
-- Primary table: commitments
SELECT commitment_id, title, description, due_date, status, 
       task_id, project_id, created_at
FROM commitments
ORDER BY due_date ASC;

-- Status values: 'pending' | 'fulfilled' | 'missed'
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Commitments View" (~line 2050)
- **Backend:** `/web/routers/commitments.py` - Commitment CRUD endpoints
- **Styling:** Status-based color coding (yellow/green/red)

#### API Endpoints
```
GET    /api/commitments?status=
POST   /api/commitments
GET    /api/commitments/{commitment_id}
PATCH  /api/commitments/{commitment_id}
DELETE /api/commitments/{commitment_id}
```

#### Key Features
- Status tracking (pending, fulfilled, missed)
- Fulfillment rate calculation
- Risk scoring for missed commitments
- Executive dashboard integration

---

### Alerts
**View ID:** `alerts`  
**Purpose:** System and user alerts/notifications

#### UI Structure
- Header: "Alerts" with filter dropdown (All, Unread, Critical, Warning, Info)
- Main content: List view
  - Alert cards: Title, Message, Severity badge, Timestamp
  - Actions: Mark Read, Snooze, Delete
  - Auto-clear for read alerts

#### Database Schema
```sql
-- Primary table: alerts
SELECT alert_id, title, message, severity, source, 
       is_read, is_snoozed, snoozed_until, created_at
FROM alerts
WHERE is_snoozed = FALSE OR snoozed_until < CURRENT_TIMESTAMP
ORDER BY created_at DESC;

-- Severity values: 'info' | 'warning' | 'critical'
-- Source values: 'system' | 'user' | 'integration'
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Alerts View" (~line 2150)
- **Backend:** `/web/routers/alerts.py` - Alert CRUD endpoints
- **Styling:** Severity-based coloring in CSS

#### API Endpoints
```
GET    /api/alerts?unread_only=true&severity=
POST   /api/alerts
GET    /api/alerts/{alert_id}
PATCH  /api/alerts/{alert_id}/read
DELETE /api/alerts/{alert_id}
POST   /api/alerts/{alert_id}/snooze?until=ISO_DATE_TIME
```

#### Key Features
- Severity filtering (Info, Warning, Critical)
- Auto-read on view
- Snooze functionality with time range
- Bulk operations (mark all read)
- Source-based grouping

---

### Applications
**View ID:** `applications`  
**Purpose:** Manage software applications and their configurations

#### UI Structure
- Header: "Applications" with "New Application" button
- Main content: Card grid
  - Card fields: App name, Code, Status, Owner, Jira/GitLab config status
  - Color-coded status badges (active=green, on_hold=yellow, archived=gray)

#### Database Schema
```sql
-- Primary table: applications
SELECT application_id, name, code, description, owner, status,
       jira_project_key, created_at, updated_at
FROM applications
ORDER BY name ASC;

-- Related configs
SELECT * FROM app_jira_configs WHERE application_id = ?;
SELECT * FROM app_gitlab_configs WHERE application_id = ?;
SELECT * FROM app_sprint_configs WHERE application_id = ?;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Applications View" (~line 2250)
- **Backend:** `/web/routers/application_routes.py` - Application CRUD endpoints
- **Styling:** Status badge styling with CSS variables

#### API Endpoints
```
GET    /api/applications?status=active
POST   /api/applications
GET    /api/applications/{application_id}
PATCH  /api/applications/{application_id}
DELETE /api/applications/{application_id}
POST   /api/applications/{app_id}/jira-config
POST   /api/applications/{app_id}/gitlab-config
```

#### Key Features
- Multi-status support (active, on_hold, archived)
- Jira/GitLab integration configuration
- Sprint tracking per application
- Application code/shorthand
- Team owner assignment

---

### Project Tracker
**View ID:** `project-tracker`  
**Purpose:** High-level project status and health

#### UI Structure
- Header: "Project Tracker" with health indicator legend
- Main content: Grid or table
  - Columns: Project Name, Status, Health Score (%), Tasks Complete (%), Owner
  - Health bars showing completion percentage
  - Last updated timestamp

#### Database Schema
```sql
-- Projects with task statistics
SELECT p.project_id, p.name, p.status, p.owner,
       COUNT(t.task_id) as total_tasks,
       COUNT(CASE WHEN t.status = 'done' THEN 1 END) as completed_tasks,
       ROUND(100.0 * COUNT(CASE WHEN t.status = 'done' THEN 1 END) / 
             NULLIF(COUNT(t.task_id), 0), 2) as health_pct
FROM projects p
LEFT JOIN tasks t ON p.project_id = t.project_id
GROUP BY p.project_id, p.name, p.status, p.owner
ORDER BY health_pct DESC;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Project Tracker View" (~line 2350)
- **Backend:** `/web/routers/projects.py` - Enhanced GET /api/projects endpoint
- **Styling:** Health bar progress indicator

#### API Endpoints
```
GET    /api/projects?include_health=true
GET    /api/projects/{project_id}/health
GET    /api/projects/{project_id}/stats
```

#### Key Features
- Health score calculation (task completion %)
- Progress bar visualization
- Overdue task count
- Team member count
- Last updated indicator

---

### Release Tracker
**View ID:** `release-tracker`  
**Purpose:** Track all releases across applications

#### UI Structure
- Header: "Release Tracker" with application filter
- Main content: Timeline or table view
  - Columns: Release Version, Application, Status, UAT Date, Release Date
  - Status indicators: Planned (gray), In Progress (blue), Released (green), Rollback (red)

#### Database Schema
```sql
-- Releases with application and milestone info
SELECT r.release_id, r.name, r.version, r.status, 
       a.name as application_name, r.uat_date, r.due_date,
       COUNT(m.milestone_id) as milestone_count
FROM releases r
LEFT JOIN applications a ON r.application_id = a.application_id
LEFT JOIN milestones m ON r.release_id = m.release_id
GROUP BY r.release_id, r.name, r.version, r.status, a.name, r.uat_date, r.due_date
ORDER BY r.due_date DESC;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Release Tracker View" (~line 2450)
- **Backend:** `/web/routers/releases.py` - Enhanced release listing
- **Styling:** Timeline or Gantt chart visualization

#### API Endpoints
```
GET    /api/releases?include_stats=true
GET    /api/releases/{release_id}/progress
```

#### Key Features
- Status-based filtering
- Timeline visualization
- Milestone inclusion count
- Application grouping
- Date range filtering

---

### Summaries
**View ID:** `summaries`  
**Purpose:** SOD (Start of Day) and EOD (End of Day) summaries

#### UI Structure
- Header: "Summaries" with SOD/EOD tabs
- Main content: 
  - SOD: Overdue tasks, Due today, Carry-forward in-progress
  - EOD: Completed today, Still pending

#### Database Schema
```sql
-- SOD Summary (Overdue + Due Today + Carry-forward)
SELECT 'overdue' as type, task_id, title, priority FROM tasks
WHERE due_date < CURRENT_DATE AND status != 'done'
UNION ALL
SELECT 'due-today', task_id, title, priority FROM tasks
WHERE due_date = CURRENT_DATE AND status != 'done'
UNION ALL
SELECT 'carry-forward', task_id, title, priority FROM tasks
WHERE created_at < CURRENT_DATE AND status = 'in_progress';

-- EOD Summary (Completed Today + Pending)
SELECT 'completed' as type, task_id, title, priority FROM tasks
WHERE completed_at >= CURRENT_DATE
UNION ALL
SELECT 'pending', task_id, title, priority FROM tasks
WHERE status IN ('todo', 'in_progress');
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Summaries View" (~line 2550)
- **Backend:** `/web/routers/dashboard.py` - /api/dashboard/sod and /api/dashboard/eod
- **Styling:** Section headers with dividers

#### API Endpoints
```
GET    /api/dashboard/sod
GET    /api/dashboard/eod
```

#### Key Features
- Automatic categorization
- Quick completion marking
- Carry-forward detection
- Email integration (SOD/EOD emails)
- Print-friendly format

---

## Dashboard/Grid Pages

### Dashboard
**View ID:** `dashboard`  
**Purpose:** Operational dashboard with key metrics

#### UI Structure
- Header: "Dashboard" with date/time, refresh button
- Grid layout (4 columns):
  - Card 1: Key Metrics (Total Tasks, Completed, Overdue)
  - Card 2: Overdue Tasks (list)
  - Card 3: In Progress (list)
  - Card 4: Due This Week (list)

#### Database Schema
```sql
-- Key metrics
SELECT COUNT(*) as total_tasks FROM tasks WHERE status != 'done';
SELECT COUNT(*) as overdue FROM tasks WHERE due_date < CURRENT_DATE AND status != 'done';
SELECT COUNT(*) as in_progress FROM tasks WHERE status = 'in_progress';
SELECT COUNT(*) as due_this_week FROM tasks 
WHERE due_date BETWEEN CURRENT_DATE AND CURRENT_DATE + 7 AND status != 'done';
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Dashboard View" (~line 100-300)
- **Backend:** `/web/routers/dashboard.py` - GET /api/dashboard/operational
- **Styling:** Grid layout with card gaps

#### API Endpoints
```
GET    /api/dashboard/operational
GET    /api/dashboard/stats
```

#### Key Features
- Live metric updates
- Caching (60-second TTL)
- Color-coded indicators
- Quick action buttons
- Mobile-responsive grid

---

### Operational
**View ID:** `operational`  
**Purpose:** Operational status and metrics

#### UI Structure
- Header: "Operational Dashboard"
- Multiple stat tiles:
  - Team capacity utilization
  - Project health overview
  - Alert count by severity
  - Task completion trend

#### Database Schema
```sql
-- Team capacity
SELECT COUNT(DISTINCT assignee_id) as team_size,
       COUNT(*) as total_assigned_tasks,
       ROUND(100.0 * COUNT(*) / COUNT(DISTINCT assignee_id), 2) as avg_tasks_per_person
FROM tasks WHERE assignee_id IS NOT NULL AND status != 'done';

-- Project health
SELECT p.project_id, p.name, 
       COUNT(CASE WHEN t.status = 'done' THEN 1 END) / COUNT(*) * 100 as health_pct
FROM projects p
LEFT JOIN tasks t ON p.project_id = t.project_id
GROUP BY p.project_id;

-- Alerts by severity
SELECT severity, COUNT(*) as count FROM alerts WHERE is_read = FALSE GROUP BY severity;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Operational View" (~line 400-600)
- **Backend:** `/web/routers/dashboard.py` - Enhanced operational metrics
- **Styling:** Stat tile styling with color indicators

#### API Endpoints
```
GET    /api/dashboard/operational
GET    /api/dashboard/operational/metrics
```

#### Key Features
- Real-time metric calculation
- Team capacity overview
- Alert aggregation
- Trend indicators
- Drill-down capability to detail views

---

### Executive
**View ID:** `executive`  
**Purpose:** Executive-level portfolio view

#### UI Structure
- Header: "Executive Dashboard"
- Portfolio cards showing:
  - Project health bars (overall portfolio health %)
  - Commitment risk score
  - At-risk projects count
  - Portfolio metrics

#### Database Schema
```sql
-- Portfolio health
SELECT COUNT(*) as total_projects,
       COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
       ROUND(100.0 * COUNT(CASE WHEN status = 'completed' THEN 1 END) / COUNT(*), 2) as portfolio_health_pct
FROM projects WHERE status != 'archived';

-- Commitment risk
SELECT COUNT(*) as total_commitments,
       COUNT(CASE WHEN status = 'missed' THEN 1 END) as missed_commitments,
       ROUND(100.0 * COUNT(CASE WHEN status = 'missed' THEN 1 END) / COUNT(*), 2) as missed_pct
FROM commitments;

-- At-risk projects (>30% overdue tasks)
SELECT p.project_id, p.name,
       COUNT(CASE WHEN t.due_date < CURRENT_DATE AND t.status != 'done' THEN 1 END) as overdue_count
FROM projects p
LEFT JOIN tasks t ON p.project_id = t.project_id
GROUP BY p.project_id, p.name
HAVING COUNT(CASE WHEN t.due_date < CURRENT_DATE AND t.status != 'done' THEN 1 END) > 0;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Executive View" (~line 700-900)
- **Backend:** `/web/routers/dashboard.py` - GET /api/dashboard/executive
- **Styling:** Executive dashboard color scheme (professional)

#### API Endpoints
```
GET    /api/dashboard/executive
GET    /api/dashboard/executive/portfolio-health
GET    /api/dashboard/executive/commitment-risk
```

#### Key Features
- Portfolio health aggregation
- Commitment risk scoring
- At-risk identification
- Executive summary cards
- Drill-down to project level

---

## Form/Admin Pages

### Admin Settings
**View ID:** `admin`  
**Purpose:** System configuration and admin controls

#### UI Structure
- Tabbed interface:
  - Tab 1: Email Settings (SMTP config)
  - Tab 2: Jira/GitLab Integration
  - Tab 3: Outlook Calendar Integration
  - Tab 4: Database Management
- Each tab has form fields and Save button

#### Database Schema
```sql
-- Email configuration
SELECT * FROM email_config WHERE id = 1;

-- Jira configuration
SELECT * FROM jira_config WHERE id = 1;

-- GitLab configuration
SELECT * FROM gitlab_config WHERE id = 1;

-- Outlook configuration
SELECT * FROM outlook_config WHERE id = 1;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Admin View" (~line 1000-1200)
- **Backend:** `/web/routers/admin_routes.py` - Settings CRUD endpoints
- **Styling:** Form styling with input fields, buttons

#### API Endpoints
```
GET    /api/admin/config
PATCH  /api/admin/config/email
PATCH  /api/admin/config/jira
PATCH  /api/admin/config/gitlab
PATCH  /api/admin/config/outlook
POST   /api/admin/sync-jira
POST   /api/admin/sync-gitlab
```

#### Key Features
- Multi-tab configuration interface
- Encryption for sensitive fields (SMTP password, tokens)
- Integration health checks
- Sync triggers
- Backup/restore functionality

---

### Email Briefing
**View ID:** `email-briefing`  
**Purpose:** Configure SOD/EOD email briefings

#### UI Structure
- Form fields:
  - Recipient email address
  - SOD enabled/time (HH:MM)
  - EOD enabled/time (HH:MM)
  - Filter by priority (All, High+, Critical only)
- Preview button to see email template
- Save button

#### Database Schema
```sql
-- Email configuration (subset of email_config)
SELECT recipient_email, sod_enabled, sod_time, eod_enabled, eod_time,
       reminder_priority_filter
FROM email_config
WHERE id = 1;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Email Briefing View" (~line 1250)
- **Backend:** `/web/routers/admin_routes.py` - Email config endpoints
- **Styling:** Form layout with time picker

#### API Endpoints
```
GET    /api/admin/config/email
PATCH  /api/admin/config/email
POST   /api/admin/send-test-email
```

#### Key Features
- Scheduled email triggers (SOD/EOD)
- Custom time scheduling
- Priority filtering
- Email template preview
- Test email sending

---

### Activity Log
**View ID:** `activity-log`  
**Purpose:** View all system activity and audit trail

#### UI Structure
- Header: Filter bar (date range, entity type, action, user)
- Main content: Table view
  - Columns: Timestamp, Entity Type, Action, User, Description, Details
  - Pagination (50 items per page)
  - Export to CSV button

#### Database Schema
```sql
-- Activity logs with pagination
SELECT activity_id, entity_type, entity_id, action, description, 
       details, created_at
FROM entity_activity_logs
ORDER BY created_at DESC
LIMIT 50 OFFSET 0;

-- Filter by entity type
SELECT DISTINCT entity_type FROM entity_activity_logs;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Activity Log View" (~line 1350)
- **Backend:** `/web/routers/activity_routes.py` - Activity log queries
- **Styling:** Table styling with alternating row colors

#### API Endpoints
```
GET    /api/activity-logs?entity_type=&action=&date_from=&date_to=&page=1
GET    /api/activity-logs/export
```

#### Key Features
- Multi-field filtering
- Pagination with adjustable page size
- CSV export
- JSON details expansion
- Sortable columns

---

### API Tokens
**View ID:** `api-tokens`  
**Purpose:** Manage API authentication tokens

#### UI Structure
- Header: "API Tokens" with "Generate New Token" button
- Main content: Table of tokens
  - Columns: Token Name, Created Date, Last Used, Scope, Actions (Revoke, Copy)
- Modal for creating new token (shows token once after creation)

#### Database Schema
```sql
-- Note: API tokens should be stored in a dedicated table
-- CREATE TABLE api_tokens (
--   token_id STRING PRIMARY KEY,
--   name VARCHAR(255),
--   token_hash TEXT (bcrypt or similar),
--   scope TEXT (JSON array),
--   created_at DATETIME,
--   last_used_at DATETIME,
--   is_revoked BOOLEAN
-- )
SELECT token_id, name, scope, created_at, last_used_at, is_revoked
FROM api_tokens
WHERE is_revoked = FALSE
ORDER BY created_at DESC;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "API Tokens View" (~line 1450)
- **Backend:** `/web/routers/auth_routes.py` - Token management endpoints
- **Styling:** Modal styling for token creation

#### API Endpoints
```
GET    /api/auth/tokens
POST   /api/auth/tokens
DELETE /api/auth/tokens/{token_id}
POST   /api/auth/tokens/{token_id}/revoke
```

#### Key Features
- Token generation with random string
- Scope-based access control
- Token revocation
- Usage tracking (last used)
- One-time display after creation

---

## Table/List Pages

### Team List
**View ID:** `team-list`  
**Purpose:** Manage team members and assignments

#### UI Structure
- Header: "Team List" with "Add Team Member" button
- Main content: Table
  - Columns: Name, Email, Role, Active Status, Task Count, Max Concurrent
  - Search bar for quick filter
  - Edit/Delete actions

#### Database Schema
```sql
-- Team members with task statistics
SELECT m.member_id, m.name, m.email, m.role, m.is_active, 
       m.max_concurrent_tasks,
       COUNT(DISTINCT t.task_id) as current_task_count
FROM team_members m
LEFT JOIN tasks t ON m.member_id = t.assignee_id AND t.status != 'done'
WHERE m.is_team_member = TRUE
GROUP BY m.member_id
ORDER BY m.name ASC;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Team List View" (~line 1600)
- **Backend:** `/web/routers/team_routes.py` - Team member CRUD endpoints
- **Styling:** Table styling with inline edit capability

#### API Endpoints
```
GET    /api/team-members?include_stats=true
POST   /api/team-members
GET    /api/team-members/{member_id}
PATCH  /api/team-members/{member_id}
DELETE /api/team-members/{member_id}
```

#### Key Features
- Team member CRUD
- Role management
- Task count tracking
- Capacity limit configuration
- Active/inactive toggling

---

### Team Workload
**View ID:** `team-workload`  
**Purpose:** Monitor team capacity and workload

#### UI Structure
- Header: "Team Workload" with view toggle (card/table)
- Main content: 
  - Each team member card/row showing:
    - Name, Current Task Count, Capacity %
    - Visual bar showing utilization (e.g., 6/8 tasks)
    - Average priority of assigned tasks
- Color-coded: Green (< 75%), Yellow (75-90%), Red (> 90%)

#### Database Schema
```sql
-- Team workload with capacity calculation
SELECT m.member_id, m.name, m.max_concurrent_tasks,
       COUNT(DISTINCT CASE WHEN t.status != 'done' THEN t.task_id END) as current_tasks,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN t.status != 'done' THEN t.task_id END) / 
             NULLIF(m.max_concurrent_tasks, 1), 2) as capacity_pct,
       AVG(CASE WHEN t.priority = 'critical' THEN 4
                WHEN t.priority = 'high' THEN 3
                WHEN t.priority = 'medium' THEN 2
                ELSE 1 END) as avg_priority
FROM team_members m
LEFT JOIN tasks t ON m.member_id = t.assignee_id
WHERE m.is_active = TRUE
GROUP BY m.member_id, m.name, m.max_concurrent_tasks
ORDER BY capacity_pct DESC;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Team Workload View" (~line 1750)
- **Backend:** `/web/routers/team_routes.py` - Workload calculation
- **Styling:** Capacity bar styling with color coding

#### API Endpoints
```
GET    /api/team-members/workload
GET    /api/team-members/{member_id}/workload
```

#### Key Features
- Real-time capacity calculation
- Color-coded utilization indicator
- Average priority tracking
- Reassignment suggestion
- Capacity exceeded alerting

---

### Resourcing
**View ID:** `resourcing`  
**Purpose:** Manage resource allocation across projects

#### UI Structure
- Header: "Resourcing" with date range picker
- Main content: Resource allocation table
  - Columns: Team Member, Project, Allocation %, Start Date, End Date, Role
  - Modal for adding/editing allocation

#### Database Schema
```sql
-- Resource allocations by date range
SELECT ra.allocation_id, m.name as member_name, p.name as project_name,
       ra.allocation_pct, ra.start_date, ra.end_date, ra.role,
       ra.notes
FROM resource_allocations ra
JOIN team_members m ON ra.member_id = m.member_id
JOIN projects p ON ra.project_id = p.project_id
WHERE ra.start_date <= CURRENT_DATE AND ra.end_date >= CURRENT_DATE
ORDER BY m.name, ra.start_date;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Resourcing View" (~line 1900)
- **Backend:** `/web/routers/resourcing_routes.py` - Resource allocation endpoints
- **Styling:** Timeline-style visualization for allocation periods

#### API Endpoints
```
GET    /api/resource-allocations?date_from=&date_to=
POST   /api/resource-allocations
GET    /api/resource-allocations/{allocation_id}
PATCH  /api/resource-allocations/{allocation_id}
DELETE /api/resource-allocations/{allocation_id}
```

#### Key Features
- Date range allocation
- Percentage-based allocation
- Role assignment per allocation
- Conflict detection (>100% allocation)
- Historical tracking

---

### Estimate
**View ID:** `estimate`  
**Purpose:** Create and manage task effort estimates

#### UI Structure
- Header: "Estimate" with "New Estimate" button
- Main content: Estimate cards or table
  - Card fields: Title, Story Points, Complexity, Testing Effort, Total Days
  - Calculation summary showing breakdown

#### Database Schema
```sql
-- Estimates with calculated fields
SELECT estimation_id, title, story_points, complexity, testing_effort,
       has_release_paperwork, velocity, start_date,
       dev_days, testing_days, paperwork_days, holiday_buffer_days,
       total_working_days, estimated_end_date, created_at
FROM estimations
ORDER BY created_at DESC;

-- Calculation formula:
-- dev_days = CEIL(story_points / velocity)
-- testing_days = estimated testing effort in days
-- paperwork_days = 1 if has_release_paperwork else 0
-- holiday_buffer_days = number of holidays in date range
-- total_working_days = dev_days + testing_days + paperwork_days + holiday_buffer_days
-- estimated_end_date = start_date + total_working_days
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Estimate View" (~line 2050)
- **Backend:** `/web/routers/estimate_routes.py` - Estimation calculation
- **Styling:** Form layout with calculation display

#### API Endpoints
```
GET    /api/estimations?project_id=
POST   /api/estimations
GET    /api/estimations/{estimation_id}
PATCH  /api/estimations/{estimation_id}
DELETE /api/estimations/{estimation_id}
POST   /api/estimations/{estimation_id}/calculate
```

#### Key Features
- Effort breakdown calculation
- Holiday accounting
- Velocity-based calculation
- Complexity adjustments
- Accuracy tracking (estimated vs actual)

---

## Specialized Pages

### Sprint Board
**View ID:** `sprint-board`  
**Purpose:** Kanban board for sprint tasks (Jira integration)

#### UI Structure
- Header: Sprint selector dropdown, Team view toggle
- Main content: Kanban columns
  - Columns: To Do | In Progress | In Review | Done
  - Drag-and-drop between columns
  - Cards show: Issue key, Title, Assignee, Priority

#### Database Schema
```sql
-- Mock Jira issues (for development/demo)
SELECT issue_id, key, summary, assignee_email, status, priority, 
       project_key, created_at
FROM mock_jira_issues
ORDER BY status, priority DESC;

-- Sprint configuration
SELECT * FROM sprint_config WHERE id = 1;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Sprint Board View" (~line 2150)
- **Backend:** `/web/routers/jira_routes.py` - Jira integration endpoints
- **Styling:** Kanban column styling with drag-drop support

#### API Endpoints
```
GET    /api/jira/sprints
GET    /api/jira/sprints/{sprint_id}/issues
PATCH  /api/jira/issues/{issue_id}/status
GET    /api/jira/config
```

#### Key Features
- Jira sync integration
- Kanban-style drag-drop
- Status updates reflected in Jira
- Team filtering
- Issue detail modal

---

### Proj Planner
**View ID:** `proj-planner`  
**Purpose:** Project planning with milestones and tasks

#### UI Structure
- Header: "Project Planner" with project selector
- Main content: 
  - Left sidebar: Project details, milestone list
  - Main area: Gantt chart showing milestones and tasks
  - Drag to reschedule tasks

#### Database Schema
```sql
-- Project estimation details
SELECT est_id, name, start_date, end_date_constraint, 
       jira_project_key, application_id
FROM proj_estimates;

-- Milestones for estimation
SELECT ms_id, est_id, name, execution_type, order
FROM proj_est_milestones;

-- Tasks within milestones
SELECT task_id, ms_id, name, duration_days, execution_type, 
       order, assignee, jira_key
FROM proj_est_tasks;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Proj Planner View" (~line 2250)
- **Backend:** `/web/routers/planning_routes.py` - Project planning endpoints
- **Styling:** Gantt chart visualization (timeline-based)

#### API Endpoints
```
GET    /api/proj-estimates
POST   /api/proj-estimates
GET    /api/proj-estimates/{est_id}
GET    /api/proj-estimates/{est_id}/milestones
GET    /api/proj-estimates/{est_id}/timeline
```

#### Key Features
- Milestone sequencing (sequential/parallel)
- Task dependency management
- Timeline visualization (Gantt)
- Resource assignment
- Timeline calculations

---

### Delivery
**View ID:** `delivery`  
**Purpose:** Release delivery checklist and coordination

#### UI Structure
- Header: "Delivery" with release selector
- Main content: Checklist view
  - Sections: Pre-release | Release | Post-release
  - Each item: Checkbox, Title, Description, Responsible Role, Assignee, Status
  - Overall progress bar

#### Database Schema
```sql
-- Delivery release with items
SELECT dr.release_id, dr.name, dr.version, dr.application_id,
       dr.template_id, dr.target_date, dr.status, dr.release_manager
FROM delivery_releases dr;

-- Delivery items (checklist)
SELECT dri.item_id, dri.release_id, dri.order, dri.title, 
       dri.description, dri.category, dri.responsible_role, 
       dri.status, dri.assignee, dri.completed_at
FROM delivery_release_items dri
ORDER BY dri.order ASC;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Delivery View" (~line 2350)
- **Backend:** `/web/routers/delivery_routes.py` - Delivery checklist endpoints
- **Styling:** Checklist styling with progress tracking

#### API Endpoints
```
GET    /api/delivery-releases
POST   /api/delivery-releases
GET    /api/delivery-releases/{release_id}
GET    /api/delivery-releases/{release_id}/items
PATCH  /api/delivery-releases/{release_id}/items/{item_id}
```

#### Key Features
- Release template support
- Pre/Release/Post-release phases
- Checklist progress tracking
- Assignment and responsibility tracking
- Status workflow (pending → in_progress → done)

---

### Inbox
**View ID:** `inbox`  
**Purpose:** Centralized inbox for notifications and quick actions

#### UI Structure
- Header: "Inbox" with filter tabs (All, Alerts, Tasks, Reminders)
- Main content: List of items
  - Item types: Alerts (red/yellow/blue), Tasks (light blue), Reminders (purple)
  - Each item: Title, Source, Timestamp, Action buttons (Archive, Snooze)
- Bulk actions: Select all, Mark all as read

#### Database Schema
```sql
-- Union of multiple notification types
-- Alerts
SELECT 'alert' as type, alert_id, title, message as content, 
       severity, created_at
FROM alerts WHERE is_read = FALSE AND is_snoozed = FALSE

UNION ALL

-- Tasks (user-assigned, due soon)
SELECT 'task', task_id, title, description, 
       CASE WHEN priority = 'critical' THEN 'critical'
            WHEN priority = 'high' THEN 'warning'
            ELSE 'info' END as severity,
       due_date
FROM tasks WHERE assignee_id = ? AND status != 'done' 
       AND due_date <= CURRENT_DATE + 3

UNION ALL

-- Reminders
SELECT 'reminder', reminder_id, title, description, priority, 
       trigger_date
FROM reminders WHERE is_active = TRUE

ORDER BY created_at DESC;
```

#### Files to Modify/Update
- **UI:** `/web/static/index.html` - Section: "Inbox View" (~line 2450)
- **Backend:** `/web/routers/inbox_routes.py` - Inbox aggregation endpoints
- **Styling:** Item type coloring and icons

#### API Endpoints
```
GET    /api/inbox?type=&unread_only=true
GET    /api/inbox/items/{item_id}
POST   /api/inbox/items/{item_id}/archive
POST   /api/inbox/items/{item_id}/snooze
POST   /api/inbox/mark-all-read
```

#### Key Features
- Multi-source notification aggregation
- Type-based filtering and coloring
- Snooze functionality
- Bulk operations (mark read, archive)
- Quick action buttons per item

---

## CSS Variables (All Pages)

The following semantic CSS variables are used across all 27 pages:

```css
:root {
  /* Semantic spacing for page structure */
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

*, *::before, *::after {
  box-sizing: border-box;
}
```

Apply these variables to:
- All section headers: `padding: var(--header-padding-top) var(--header-padding-sides) var(--header-padding-bottom)`
- All content areas: `padding: var(--content-padding-top) var(--content-padding-sides)`
- All flex containers with gaps: `gap: var(--card-gap)`
- All cards: `padding: var(--card-padding); border: var(--card-border-width) solid; border-left: var(--card-accent-border-width) solid`

---

## File Organization Summary

### Frontend Files
- **Main:** `/web/static/index.html` - SPA with all 27 views
- **Assets:** `/web/static/assets/` - CSS, images, icons

### Backend Files
- **Main app:** `/web/app.py` - FastAPI app setup
- **Routers:**
  - `/web/routers/tasks.py` - Task CRUD
  - `/web/routers/projects.py` - Project CRUD
  - `/web/routers/milestones.py` - Milestone CRUD
  - `/web/routers/commitments.py` - Commitment CRUD
  - `/web/routers/alerts.py` - Alert CRUD
  - `/web/routers/dashboard.py` - Dashboard endpoints (operational, executive, sod, eod)
  - `/web/routers/admin_routes.py` - Admin settings
  - `/web/routers/jira_routes.py` - Jira integration
  - `/web/routers/gitlab_routes.py` - GitLab integration
  - `/web/routers/team_routes.py` - Team management
  - `/web/routers/application_routes.py` - Application CRUD
  - `/web/routers/releases.py` - Release management
  - `/web/routers/delivery_routes.py` - Delivery checklist
  - `/web/routers/planning_routes.py` - Project planning
  - `/web/routers/estimate_routes.py` - Estimation
  - `/web/routers/activity_routes.py` - Activity logging
  - `/web/routers/inbox_routes.py` - Inbox aggregation

### Database Files
- **Models:** `/db/models.py` - All ORM models
- **Base:** `/db/base.py` - SQLAlchemy setup
- **Init:** `/db/init_db.py` - Database initialization

---

## Next Steps

1. **Update each page view** in `/web/static/index.html` to apply semantic CSS variables
2. **Create router files** for missing pages (use existing pattern)
3. **Implement caching** for dashboard endpoints (60-second TTL)
4. **Add error handling** in all endpoints
5. **Create API documentation** (see API.md in this docs folder)
