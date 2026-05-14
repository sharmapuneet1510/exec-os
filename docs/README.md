# ExecOS Documentation

Complete documentation for the ExecOS Personal Execution System. Choose your starting point based on your role.

## Quick Links by Role

### 👤 End Users

Getting started with ExecOS as a user:

1. **[Setup and Configuration](SETUP_AND_CONFIGURATION.md)** — Installation, running the app, basic setup
2. **[API Documentation](API.md)** — If integrating with external systems
3. **[PAGES.md](PAGES.md)** — Guide to all 27 pages and features

**Quick Start:** 
```bash
python3 start.py
```
Open `http://localhost:8080` in your browser.

---

### 🛠️ Backend Developers

Building APIs and features:

1. **[Developer Guide](DEVELOPER_GUIDE.md)** — Project structure, adding endpoints, patterns
2. **[Database Schema](DATABASE_SCHEMA.md)** — Complete database reference
3. **[API Documentation](API.md)** — Endpoint specifications
4. **[Deployment & Operations](DEPLOYMENT_AND_OPERATIONS.md)** — Production setup

**Quick Start:**
```bash
python3 start.py
```
Then access Swagger docs at `http://localhost:8080/docs`

---

### 🎨 Frontend Developers

Building UI and components:

1. **[Frontend Components](FRONTEND_COMPONENTS.md)** — Page structure, Alpine.js patterns, styling
2. **[Developer Guide](DEVELOPER_GUIDE.md)** — Adding new pages
3. **[Setup and Configuration](SETUP_AND_CONFIGURATION.md)** — Initial setup

**Tech Stack:** HTML + Alpine.js + Tailwind CSS (CDN, no build step)

**Quick Start:**
```bash
python3 start.py
# Edit web/static/index.html directly
# Refresh browser to see changes
```

---

### 🚀 DevOps / Operations

Deploying and operating ExecOS:

1. **[Deployment & Operations](DEPLOYMENT_AND_OPERATIONS.md)** — Production setup, monitoring, backups
2. **[Setup and Configuration](SETUP_AND_CONFIGURATION.md)** — Configuration options, troubleshooting
3. **[Database Schema](DATABASE_SCHEMA.md)** — Database optimization, maintenance

**Key Topics:**
- Systemd/Docker deployment
- PostgreSQL setup
- Backup strategies
- Security hardening
- Monitoring and logging

---

### 📖 Architects / Technical Leads

Understanding the full system:

Read in this order:
1. **[API Documentation](API.md)** — Understand endpoints
2. **[Database Schema](DATABASE_SCHEMA.md)** — Data model
3. **[Developer Guide](DEVELOPER_GUIDE.md)** — Code organization
4. **[Frontend Components](FRONTEND_COMPONENTS.md)** — UI architecture
5. **[Deployment & Operations](DEPLOYMENT_AND_OPERATIONS.md)** — Production concerns

---

## Documentation Map

| Document | Purpose | Audience |
|----------|---------|----------|
| **[API.md](API.md)** | REST API reference with all endpoints, request/response schemas, examples | Backend devs, integrators |
| **[DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)** | Complete SQLite/PostgreSQL schema reference with all tables and relationships | Developers, DBAs, architects |
| **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** | How to develop features, add endpoints, modify code | Backend & frontend developers |
| **[FRONTEND_COMPONENTS.md](FRONTEND_COMPONENTS.md)** | Frontend architecture, Alpine.js patterns, component development | Frontend developers, UI designers |
| **[SETUP_AND_CONFIGURATION.md](SETUP_AND_CONFIGURATION.md)** | Installation, configuration, troubleshooting, local development | Everyone during setup |
| **[DEPLOYMENT_AND_OPERATIONS.md](DEPLOYMENT_AND_OPERATIONS.md)** | Production deployment, monitoring, backups, scaling | DevOps, operations teams |
| **[PAGES.md](PAGES.md)** | Description of all 27 pages and their features | Product managers, users |

---

## System Overview

### Architecture at a Glance

```
┌─────────────────────────────────────────────────────────┐
│  Web Browser (Chrome, Firefox, Safari)                   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Single Page Application (SPA)                    │   │
│  │  - 27 Pages (HTML + Alpine.js)                   │   │
│  │  - Tailwind CSS styling (CDN)                    │   │
│  │  - Fetch API calls to backend                    │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↕ HTTP/JSON
┌─────────────────────────────────────────────────────────┐
│  FastAPI Backend (Python 3.11)                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │  API Routers                                      │   │
│  │  - Tasks, Projects, Releases, Milestones         │   │
│  │  - Teams, Resources, Commitments, Alerts         │   │
│  │  - Estimations, Delivery, Jira, GitLab          │   │
│  │  - Email, Settings, Dashboard                    │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  SQLAlchemy ORM                                   │   │
│  │  - 30+ database tables                           │   │
│  │  - Relationships, constraints, indexes           │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↕ SQL
┌─────────────────────────────────────────────────────────┐
│  Database                                                │
│  ┌──────────────────────────────────────────────────┐   │
│  │  SQLite (Development)                            │   │
│  │  Location: ~/.commanddesk/execos.db              │   │
│  └──────────────────────────────────────────────────┘   │
│  OR                                                      │
│  ┌──────────────────────────────────────────────────┐   │
│  │  PostgreSQL (Production)                         │   │
│  │  Standard connection string                      │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Details |
|-------|-----------|---------|
| **Frontend** | HTML + Alpine.js + Tailwind | Single HTML file, CDN-based, no build |
| **Backend** | FastAPI + Uvicorn | Python 3.11+, async handlers |
| **ORM** | SQLAlchemy 2.0 | Type-safe, SQL-based queries |
| **Database** | SQLite (dev) / PostgreSQL (prod) | File-based or client-server |
| **Server** | Uvicorn | ASGI application server |
| **Cache** | In-memory dict | 60-second TTL for dashboards |
| **Scheduling** | APScheduler | SOD/EOD email notifications |

---

## Key Concepts

### Core Entities

- **Tasks** — Work items with priority, status, due dates
- **Projects** — Container for related tasks, health scoring
- **Releases** — Version deployments with milestones
- **Milestones** — Key checkpoints within projects
- **Commitments** — Promises tracked as pending/fulfilled/missed
- **Alerts** — Notifications with severity levels
- **Team Members** — People with capacity allocation
- **Applications** — Products/services being managed

### Key Features

- **Dashboard** — Overview of workload, overdue, upcoming
- **SOD/EOD** — Start and end of day summaries via email
- **Integrations** — Jira, GitLab, Outlook, Email
- **Estimations** — Work effort calculation
- **Delivery** — Release checklists and tracking
- **Activity Logs** — Full audit trail of changes

---

## Development Workflow

### Local Development

```bash
# 1. Clone and navigate
cd command-center

# 2. Start server
python3 start.py

# 3. Open in browser
open http://localhost:8080

# 4. Access API docs
open http://localhost:8080/docs

# 5. Edit files and test
# Frontend: Edit web/static/index.html
# Backend: Edit web/routers/*.py
# Refresh browser or restart server
```

### Making Changes

**Frontend Changes (HTML/CSS/JavaScript):**
1. Edit `web/static/index.html`
2. Refresh browser (Ctrl+Shift+R for hard refresh)
3. Done! (No build step)

**Backend Changes (Python):**
1. Edit files in `web/routers/`
2. Stop and restart server (`Ctrl+C`, then `python3 start.py`)
3. Refresh browser or re-test API

**Database Changes:**
1. Modify `db/models.py`
2. Delete database: `rm ~/.commanddesk/execos.db`
3. Restart server (creates new schema)

---

## Deployment at a Glance

### Single User (Desktop)

```bash
python3 start.py
```

### Team (Local Network)

```bash
# On server machine
python3 start.py

# Access from other machines
http://server-ip:8080
```

### Production (Cloud)

1. Use PostgreSQL instead of SQLite
2. Deploy with systemd or Docker
3. Setup nginx reverse proxy with HTTPS
4. Configure backups and monitoring
5. See [DEPLOYMENT_AND_OPERATIONS.md](DEPLOYMENT_AND_OPERATIONS.md)

---

## Common Tasks

### Add a New Page

1. See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) → Adding a New Page
2. Add page `<div>` to `index.html`
3. Add navigation button
4. Implement Alpine.js component
5. Test in browser

### Add an API Endpoint

1. See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) → Adding API Endpoints
2. Create new router or add to existing
3. Include in `web/app.py`
4. Test with `curl` or Swagger UI
5. Document in [API.md](API.md)

### Backup Database

```bash
# One-time backup
cp ~/.commanddesk/execos.db ~/.commanddesk/execos.db.backup

# Automated backup (see ops guide)
```

### Integrate with Jira

1. Get Jira Personal Access Token
2. Call API: `POST /api/jira/config`
3. Enable integration
4. See integration in Jira settings page

---

## Troubleshooting

### Server Won't Start

See [SETUP_AND_CONFIGURATION.md](SETUP_AND_CONFIGURATION.md) → Troubleshooting

### API Returns 404

1. Check endpoint path in [API.md](API.md)
2. Verify server is running
3. Check Network tab in DevTools
4. Review application logs

### Frontend Component Not Working

1. Check browser console (F12)
2. Verify Alpine.js is loaded (check Network tab)
3. Inspect element in DevTools
4. Check Tailwind classes are applied

### Database Locked

See [SETUP_AND_CONFIGURATION.md](SETUP_AND_CONFIGURATION.md) → Database Locked

---

## FAQ

**Q: Do I need Node.js or npm?**  
A: No! ExecOS uses CDN-based libraries. No build step or npm needed.

**Q: Can I use PostgreSQL?**  
A: Yes! Set `DATABASE_URL=postgresql://...` environment variable.

**Q: How do I scale to many users?**  
A: Use PostgreSQL, add web server redundancy, implement caching. See ops guide.

**Q: Is authentication supported?**  
A: Not in Phase 1. Coming in Phase 2. Currently all endpoints are public.

**Q: Can I modify the database schema?**  
A: Yes! Edit `db/models.py` and recreate database. See developer guide.

**Q: What's included in the one HTML file?**  
A: All 27 pages, all JavaScript, Tailwind CSS setup, Alpine.js components.

**Q: Can I export data?**  
A: Yes, via API or direct SQLite/PostgreSQL access.

**Q: Is there a mobile app?**  
A: Not yet. Web UI is responsive and works on mobile.

---

## Getting Help

### Documentation Resources

- **API**: See [API.md](API.md) for complete endpoint reference
- **Database**: See [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for data model
- **Development**: See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for coding patterns
- **Operations**: See [DEPLOYMENT_AND_OPERATIONS.md](DEPLOYMENT_AND_OPERATIONS.md) for deployment

### Browser Developer Tools

- **Network Tab**: See all API calls and responses
- **Console**: Check for JavaScript errors
- **Elements**: Inspect HTML and Tailwind classes
- **Application Tab**: View localStorage and cookies

### Debug Environment

```bash
# Check Python version
python3 --version

# Check dependencies
pip list | grep fastapi

# Check database file
ls -lh ~/.commanddesk/execos.db

# Check network connectivity
curl http://localhost:8080/health
```

---

## Contributing / Reporting Issues

When reporting issues, include:

1. **Error message** — Exact error text
2. **Steps to reproduce** — How to make it happen again
3. **Environment** — Python version, OS, browser
4. **Logs** — Check console or server logs
5. **Screenshot** — Visual issues

---

## Documentation Maintenance

Documentation is kept in `docs/` folder alongside code.

**When making changes:**
- Update relevant documentation file
- Keep examples current and tested
- Add new sections for new features
- Cross-link related sections

**Build quality docs:**
- Write for your future self
- Include examples and code snippets
- Explain the "why" not just the "what"
- Keep it organized and searchable

---

## Feedback

Have suggestions for improving documentation?

- Check existing docs for your answer first
- If missing, add to this README
- Keep examples simple and clear
- Link related sections

---

**Last Updated:** May 14, 2026  
**ExecOS Version:** 1.0.0  
**Python:** 3.11+
