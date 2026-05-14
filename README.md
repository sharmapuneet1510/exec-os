# ExecOS Command Center

**Personal Execution System for Leadership**

ExecOS is a self-contained, zero-dependency web application for capturing, structuring, tracking, and driving execution of work. It features task management, project health scoring, commitment tracking, alerts, and multi-layer dashboards — all locally hosted with no external dependencies.

**Live Demo:** http://localhost:8080 (after starting the server)  
**API Docs:** http://localhost:8080/docs (Swagger/OpenAPI interactive docs)

---

## Quick Start

### Installation (one command)

```bash
cd /Users/puneetsharma/Workspace/projects/ai-lab/command-center
python3 start.py
```

That's it. `start.py` will:
1. Install Python dependencies automatically (FastAPI, SQLAlchemy, etc.)
2. Create the SQLite database at `~/.commanddesk/execos.db` (on first run)
3. Start the FastAPI server on http://localhost:8080
4. Open your browser automatically

### Requirements

- **Python 3.8+** (check with `python3 --version`)
- **SQLite 3** (included with macOS, Linux)
- **~50 MB disk space** (database + app code)

### No Dependencies Required

- ✅ No Docker needed
- ✅ No PostgreSQL, MySQL, or external database
- ✅ No Redis or cache server
- ✅ No npm/Node.js build step
- ✅ No external APIs or cloud services
- ✅ All CSS/JavaScript served from CDN (Tailwind CSS, Alpine.js)

---

## Architecture

### Technology Stack

| Layer       | Technology                                  |
|-------------|---------------------------------------------|
| **Frontend** | HTML + Tailwind CSS (CDN) + Alpine.js (CDN) |
| **Backend** | FastAPI + Uvicorn (Python)                  |
| **Database** | SQLite (file-based, `~/.commanddesk/execos.db`) |
| **Cache**   | In-memory dict with TTL (no Redis)          |
| **ORM**     | SQLAlchemy 2.x                              |

### Project Structure

```
command-center/
├── start.py                   # Single-script entry point (run this!)
├── web_server.py              # Alternative entry (dev use)
├── requirements.txt           # Python dependencies
├── web/
│   ├── app.py                 # FastAPI app setup & routing
│   ├── deps.py                # Dependencies (in-memory cache)
│   ├── routers/               # API route handlers
│   │   ├── tasks.py           # /api/tasks CRUD
│   │   ├── projects.py        # /api/projects + health scoring
│   │   ├── milestones.py      # /api/milestones CRUD
│   │   ├── commitments.py     # /api/commitments CRUD
│   │   ├── alerts.py          # /api/alerts CRUD
│   │   ├── dashboard.py       # /api/dashboard/* endpoints
│   │   ├── admin_routes.py    # Settings & configuration
│   │   ├── jira_routes.py     # Jira integration
│   │   ├── gitlab_routes.py   # GitLab integration
│   │   ├── team_routes.py     # Team management
│   │   ├── application_routes.py # Applications CRUD
│   │   ├── releases.py        # Release management
│   │   ├── delivery_routes.py # Delivery checklists
│   │   └── ... (more routers)
│   └── static/
│       └── index.html         # SPA with all 27 views
├── db/
│   ├── base.py                # SQLAlchemy engine & session
│   ├── models.py              # ORM models (25+ tables)
│   └── init_db.py             # Database initialization
├── docs/
│   ├── PAGES.md               # Page-by-page documentation
│   ├── API.md                 # Complete API reference
│   └── ... (other docs)
└── ... (legacy Tkinter desktop app, still usable)
```

---

## Features

### Core Pages (27 total)

#### Card-Based (12 pages)
- **My Book of Work** — Tasks assigned to you
- **Day Planner** — Time-block your day (30-min slots)
- **Tasks** — Full task management with filters
- **Projects** — Project CRUD with health scoring
- **Milestones** — Track project milestones
- **Releases** — Manage product releases
- **Commitments** — Track promises & fulfillment
- **Alerts** — System notifications with severity
- **Applications** — Software app configuration
- **Project Tracker** — Project health overview
- **Release Tracker** — Cross-project release timeline
- **Summaries** — SOD (start-of-day) & EOD (end-of-day) digests

#### Dashboard/Grid (3 pages)
- **Dashboard** — Operational metrics & quick tasks
- **Operational** — Team capacity, project health, alerts
- **Executive** — Portfolio health, commitment risk, at-risk projects

#### Form/Admin (4 pages)
- **Admin Settings** — Email, Jira/GitLab, Outlook configuration
- **Email Briefing** — Configure SOD/EOD email times
- **Activity Log** — Audit trail with filtering & CSV export
- **API Tokens** — Generate & revoke API keys (future)

#### Table/List (4 pages)
- **Team List** — Team member CRUD & role management
- **Team Workload** — Capacity utilization by person
- **Resourcing** — Resource allocation across projects
- **Estimate** — Story point estimation & timeline calculation

#### Specialized (4 pages)
- **Sprint Board** — Kanban board (Jira integration)
- **Proj Planner** — Project timeline with Gantt chart
- **Delivery** — Release delivery checklist
- **Inbox** — Unified notifications (alerts, tasks, reminders)

### Key Capabilities

✅ **Task Management**
- Status tracking (todo, in_progress, done, cancelled)
- Priority levels (low, medium, high, critical)
- Project linking & team assignment
- Flexible tagging system
- Due date & reminder support

✅ **Project Health Scoring**
- Auto-calculated based on task completion %
- Overdue task detection
- At-risk project identification
- Portfolio-level aggregation

✅ **Multi-Layer Dashboards**
- **Operational:** Live task metrics, overdue count, team workload
- **Executive:** Portfolio health, commitment risk score, blockers
- **SOD/EOD:** Daily summaries with auto-categorization

✅ **Commitment Tracking**
- Promise status tracking (pending, fulfilled, missed)
- Fulfillment rate & risk scoring
- Executive dashboard integration

✅ **Alert System**
- Severity levels (info, warning, critical)
- Auto-generation on task overdue, upcoming milestones
- Snooze functionality
- Source-based grouping (system, user, integration)

✅ **Integration Support** (configuration ready)
- **Jira:** Sprint board sync, issue status updates
- **GitLab:** Merge request tracking
- **Outlook:** Calendar import (ICS feed)
- **Email:** Scheduled SOD/EOD briefings

✅ **Flexible Data Models**
- 25+ ORM models with proper relationships
- Audit logging for all changes
- Support for custom tags, metadata
- Historical data retention

---

## Database Schema

### Core Tables

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `tasks` | Work items | task_id, title, due_date, priority, status, project_id, assignee_id |
| `projects` | Project containers | project_id, name, status, owner, due_date |
| `milestones` | Project milestones | milestone_id, title, project_id, release_id, due_date, status |
| `releases` | Product releases | release_id, name, version, application_id, status, uat_date, sign_off_date |
| `commitments` | Promises & commitments | commitment_id, title, due_date, status (pending/fulfilled/missed) |
| `alerts` | Notifications | alert_id, title, severity (info/warning/critical), source, is_read |
| `team_members` | People | member_id, name, email, role, max_concurrent_tasks |
| `resource_allocations` | Project staffing | allocation_id, member_id, project_id, allocation_pct, start_date, end_date |

### Configuration Tables

| Table | Purpose |
|-------|---------|
| `email_config` | SMTP settings, SOD/EOD schedule |
| `jira_config` | Jira base URL, token, project keys |
| `gitlab_config` | GitLab URL, token, project IDs |
| `outlook_config` | Calendar feed URL, working hours |
| `sprint_config` | Sprint board settings |

### Audit & Activity Tables

| Table | Purpose |
|-------|---------|
| `audit_logs` | Old-style audit trail (entity_type, action, detail) |
| `entity_activity_logs` | New-style activity log (JSON change tracking) |
| `activity_logs` | HTTP request logging (method, endpoint, status, duration) |

### Full Schema Reference

See `docs/PAGES.md` for detailed schema documentation per page.

---

## API Overview

### RESTful Endpoints

All endpoints follow REST conventions:

```
GET    /api/tasks?status=&priority=&project_id=
POST   /api/tasks
GET    /api/tasks/{task_id}
PATCH  /api/tasks/{task_id}
DELETE /api/tasks/{task_id}

GET    /api/projects?status=active
POST   /api/projects
GET    /api/projects/{project_id}
PATCH  /api/projects/{project_id}
DELETE /api/projects/{project_id}
GET    /api/projects/{project_id}/health

... (and similar for milestones, releases, commitments, alerts, team, etc.)

GET    /api/dashboard/operational   (cached, 60s TTL)
GET    /api/dashboard/executive     (cached, 60s TTL)
GET    /api/dashboard/sod           (live)
GET    /api/dashboard/eod           (live)
```

### Interactive API Docs

```
http://localhost:8080/docs        (Swagger UI)
http://localhost:8080/redoc       (ReDoc)
```

Full OpenAPI 3.0 specification with request/response examples.

---

## Configuration

### Environment Variables (optional)

Create a `.env` file in the project root:

```bash
PORT=8080                                              # Server port
DATABASE_URL=sqlite:////Users/you/.commanddesk/execos.db  # Database path
```

If `.env` doesn't exist, defaults are used.

### Admin Settings (via UI)

Configure at http://localhost:8080 → Admin:

- **Email:** SMTP settings, SOD/EOD schedule
- **Jira:** Base URL, PAT token, project keys
- **GitLab:** Instance URL, access token, project IDs
- **Outlook:** ICS feed URL, working hours
- **Database:** Backup/restore (future)

---

## Usage Examples

### Create a Task
```bash
curl -X POST http://localhost:8080/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Implement user authentication",
    "due_date": "2026-05-20",
    "priority": "high",
    "project_id": "550e8400-e29b-41d4-a716-446655440001"
  }'
```

### List Tasks
```bash
curl "http://localhost:8080/api/tasks?status=todo,in_progress&priority=high&sort_by=due_date"
```

### Get Operational Dashboard
```bash
curl "http://localhost:8080/api/dashboard/operational"
```

### Update Task Status
```bash
curl -X PATCH http://localhost:8080/api/tasks/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'
```

See `docs/API.md` for complete API reference.

---

## Development

### Running in Dev Mode

```bash
python3 start.py
```

Server runs at http://localhost:8080 with auto-reload on file changes.

### Project Structure for Developers

**Adding a new page:**
1. Add view section in `/web/static/index.html` with `x-show="view === 'page-name'"`
2. Create `/web/routers/your_routes.py` with endpoints
3. Register router in `/web/app.py`
4. Document in `docs/PAGES.md` and `docs/API.md`

**Adding a database table:**
1. Create ORM model in `/db/models.py`
2. Create router with CRUD endpoints
3. Register in app
4. Database auto-creates on next run (SQLAlchemy `create_all()`)

**CSS Variables (consistent spacing):**
All pages use semantic CSS variables defined in `<style>` block:
```css
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
```

### Tech Stack Details

**FastAPI:**
- Automatic OpenAPI/Swagger docs
- Type hints with Pydantic
- Async support (uses async database drivers)
- CORS enabled for CDN assets

**Tailwind CSS (CDN):**
- No build step needed
- Full utility-first CSS framework
- Responsive design (sm:, md:, lg: breakpoints)
- Dark mode support (future)

**Alpine.js (CDN):**
- Lightweight reactive framework
- `x-data`, `x-show`, `x-for`, `x-if` for DOM manipulation
- Event handling (`@click`, `@change`)
- Minimal dependencies

**SQLAlchemy 2.x:**
- Modern async support
- Declarative ORM models
- Relationship management
- Query builder for complex queries

---

## File Organization for New Features

When adding functionality, organize files as follows:

```
Feature: Task Reminders
├── Database: Add ReminderORM in db/models.py
├── Backend: Create web/routers/reminders.py
├── Frontend: Add section in web/static/index.html
├── Documentation: Update docs/PAGES.md and docs/API.md
└── Tests: Add tests/test_reminders.py
```

---

## Troubleshooting

### Port Already in Use

```bash
# Change port via environment variable
PORT=8081 python3 start.py
```

### Database Lock

If you get "database is locked" error:

```bash
# Make sure only one instance is running
# And no external processes are accessing ~/.commanddesk/execos.db
lsof ~/.commanddesk/execos.db  # Check who's accessing
```

### Slow Startup

First run is slow due to dependency installation. Subsequent runs are fast (<1 second).

### Missing Dependencies

If `ImportError: No module named 'fastapi'`:

```bash
python3 -m pip install -r requirements.txt
```

---

## Database Location

SQLite database is stored at:

```
~/.commanddesk/execos.db
```

To reset the database:

```bash
rm ~/.commanddesk/execos.db
python3 start.py
```

---

## Next Steps

### Immediate (MVP+)
- [ ] Email briefing scheduler (APScheduler)
- [ ] Outlook calendar import
- [ ] Jira sprint sync with auth
- [ ] GitLab merge request tracking

### Short Term (Phase 2)
- [ ] Desktop notifications
- [ ] Web push notifications
- [ ] Background job framework
- [ ] Data backup & restore

### Medium Term
- [ ] Multi-user support with auth
- [ ] Team collaboration features
- [ ] Advanced reporting & analytics
- [ ] Mobile app (React Native)

### Long Term
- [ ] Machine learning for estimation
- [ ] AI-powered risk detection
- [ ] Real-time sync across devices
- [ ] Offline support

---

## Documentation

- **`docs/PAGES.md`** — Complete page-by-page documentation with DB schema, UI structure, API endpoints for all 27 pages
- **`docs/API.md`** — Full REST API reference with examples and error handling
- **`CLAUDE.md`** — Project setup and developer guidelines
- **`start.py`** — Documented entry point script

---

## License

Internal project for ExecOS team.

---

## Support

For issues or feature requests:
1. Check `docs/PAGES.md` for page-specific details
2. Check `docs/API.md` for API reference
3. Run http://localhost:8080/docs for interactive API testing
4. Check git log for recent changes: `git log --oneline`

---

## Getting Started Now

```bash
cd /Users/puneetsharma/Workspace/projects/ai-lab/command-center
python3 start.py
```

Browser opens automatically at http://localhost:8080. Interactive API docs available at http://localhost:8080/docs.

Enjoy! 🚀
