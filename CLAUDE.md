# ExecOS — Command Center

## What This Is
ExecOS is a Personal Execution System for leadership roles. It captures, structures, tracks, and drives execution of work using tasks, projects, milestones, commitments, and alerts — all in a local web UI with zero external dependencies.

## Quick Start (no Docker, no infra needed)

```bash
cd /Users/puneetsharma/Workspace/projects/ai-lab/command-center
python3 start.py
```

That's it. `start.py`:
1. Installs missing Python deps automatically
2. Creates the SQLite database at `~/.commanddesk/execos.db`
3. Starts FastAPI on `http://localhost:8080`
4. Opens the browser automatically

## Architecture

```
command-center/
├── start.py               # Single-script entry point — run this
├── web_server.py          # Alternative entry (dev only, same as start.py minus auto-open)
├── requirements.txt       # fastapi, uvicorn, sqlalchemy, pydantic, python-dotenv
├── web/
│   ├── app.py             # FastAPI app — mounts all routers + serves index.html
│   ├── deps.py            # In-memory cache (replaces Redis — no external dep)
│   ├── routers/
│   │   ├── tasks.py       # CRUD /api/tasks
│   │   ├── projects.py    # CRUD /api/projects + health calculation
│   │   ├── milestones.py  # CRUD /api/milestones
│   │   ├── commitments.py # CRUD /api/commitments
│   │   ├── alerts.py      # CRUD /api/alerts
│   │   └── dashboard.py   # /api/dashboard/operational|executive|sod|eod
│   └── static/
│       └── index.html     # Full SPA — Tailwind CSS + Alpine.js (CDN, no build step)
├── db/
│   ├── base.py            # SQLAlchemy engine — SQLite at ~/.commanddesk/execos.db
│   ├── models.py          # ORM: Task, Project, Release, Milestone, Commitment, Alert, AuditLog
│   └── init_db.py         # create_all() called on startup
├── tasks/                 # Legacy Tkinter desktop models/services (JSON-backed, still usable)
├── projects/              # Legacy Tkinter desktop models/services
├── dashboard/             # Legacy dataclass dashboard builders
└── ... (backup, carryforward, focus, audit, escalation, productivity, runtime)
```

## Tech Stack

| Layer    | Technology                                     |
|----------|------------------------------------------------|
| Backend  | FastAPI + Uvicorn (Python 3.11)                |
| Database | SQLite (file: `~/.commanddesk/execos.db`)      |
| Cache    | In-memory dict with TTL (no Redis needed)      |
| ORM      | SQLAlchemy 2.x                                 |
| Frontend | HTML SPA — Tailwind CSS CDN + Alpine.js CDN    |

No Docker. No Postgres. No Redis. No build step.

## Database Schema (SQLite)

Tables auto-created on first run:

| Table        | Key Fields                                                                 |
|--------------|----------------------------------------------------------------------------|
| `tasks`      | task_id, title, description, due_date, priority, status, project_id, tags |
| `projects`   | project_id, name, description, status, owner, due_date                    |
| `milestones` | milestone_id, title, project_id, release_id, due_date, status             |
| `commitments`| commitment_id, title, due_date, status (pending/fulfilled/missed)         |
| `alerts`     | alert_id, title, severity (info/warning/critical), source, is_read        |
| `releases`   | release_id, name, version, project_id, due_date, status                   |
| `audit_logs` | log_id, entity_type, entity_id, action, detail                            |

Priority values: `low`, `medium`, `high`, `critical`
Task status: `todo`, `in_progress`, `done`, `cancelled`
Project status: `active`, `on_hold`, `completed`, `archived`

## API Endpoints

```
GET  /health

# Tasks
GET  /api/tasks?status=&priority=&project_id=
POST /api/tasks
GET  /api/tasks/{id}
PATCH /api/tasks/{id}     ← body: any subset of task fields
DELETE /api/tasks/{id}

# Projects
GET  /api/projects
POST /api/projects
GET  /api/projects/{id}
PATCH /api/projects/{id}
DELETE /api/projects/{id}

# Milestones
GET  /api/milestones?project_id=
POST /api/milestones
PATCH /api/milestones/{id}
DELETE /api/milestones/{id}

# Commitments
GET  /api/commitments
POST /api/commitments
PATCH /api/commitments/{id}
DELETE /api/commitments/{id}

# Alerts
GET  /api/alerts?unread_only=true
POST /api/alerts
PATCH /api/alerts/{id}/read
DELETE /api/alerts/{id}

# Dashboard
GET  /api/dashboard/operational   ← cached 60s in memory
GET  /api/dashboard/executive     ← cached 60s in memory
GET  /api/dashboard/sod           ← live
GET  /api/dashboard/eod           ← live
```

Interactive docs (Swagger): http://localhost:8080/docs

## Web UI Views

| View        | Description                                              |
|-------------|----------------------------------------------------------|
| Dashboard   | Overdue tasks, in-progress, upcoming (7d), milestones    |
| Executive   | Project health bars, commitment risk score, at-risk count|
| Tasks       | Filterable table (search, status, priority), CRUD modals |
| Projects    | Cards with health indicator and progress bar             |
| Milestones  | List with overdue highlighting                           |
| Commitments | Track promises, mark fulfilled/missed                    |
| Alerts      | Severity-tagged alerts, mark read                        |
| Summaries   | SOD (overdue + due today) and EOD (completed + pending)  |

## Requirements Coverage

### Phase 1 MVP — Done
- [x] Task management (create/edit/delete, status, priority, due date, project link)
- [x] Project management (CRUD, health scoring per completion rate + overdue)
- [x] Milestone tracking with overdue detection
- [x] Commitment tracking (pending / fulfilled / missed)
- [x] Alert engine (info / warning / critical, read/delete)
- [x] Operational dashboard (live metrics, overdue, upcoming)
- [x] Executive dashboard (portfolio health, commitment risk score)
- [x] SOD summary (overdue + due today + carry-forward in-progress)
- [x] EOD summary (completed today + still pending)
- [x] Persistent storage (SQLite, no external DB)
- [x] In-memory dashboard caching (60s TTL)

### Phase 2 Backlog
- [ ] Email/Outlook integration + rule engine for auto-task creation
- [ ] Follow-up reminders with scheduled background jobs (APScheduler)
- [ ] Weekly performance summary
- [ ] Desktop notifications (tray)
- [ ] Release management router (ORM table exists, no API yet)
- [ ] Audit log viewer in web UI
- [ ] Risk detection background job
- [ ] Carry-forward logic in web layer (currently only in legacy desktop)
- [ ] Focus mode / quiet hours
- [ ] Backup & restore via web

## Legacy Desktop App

The original Tkinter desktop app (`ui/`, `tasks/`, `projects/`) still works independently using JSON file storage in `~/.commanddesk/`. It is not connected to the SQLite backend. Both coexist without conflict.

## .env (optional overrides)

```
PORT=8080
DATABASE_URL=sqlite:////Users/you/.commanddesk/execos.db
```
