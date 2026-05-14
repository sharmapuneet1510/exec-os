# Setup and Configuration Guide

Complete guide to installing, configuring, and initializing ExecOS for development, testing, and production use.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Database Setup](#database-setup)
5. [Environment Variables](#environment-variables)
6. [Running the Application](#running-the-application)
7. [Integration Setup](#integration-setup)
8. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements

- **Python:** 3.11 or higher
- **OS:** macOS, Linux, or Windows (with WSL)
- **RAM:** 512 MB (minimum), 2 GB (recommended)
- **Disk Space:** 500 MB (application + database)
- **Internet:** Required for initial setup and integrations

### Optional for Integrations

- **Jira:** Cloud or Server instance with API access
- **GitLab:** GitLab.com or self-hosted GitLab instance
- **Outlook/Gmail:** For email notifications

---

## Installation

### Step 1: Clone or Download the Repository

```bash
cd ~/Workspace/projects/ai-lab/command-center
```

Or clone from git:

```bash
git clone https://github.com/yourusername/command-center.git
cd command-center
```

### Step 2: Verify Python Installation

```bash
python3 --version
# Output should be 3.11 or higher
```

### Step 3: Create Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 4: Install Dependencies

The application auto-installs dependencies on first run via `start.py`. Manual install:

```bash
pip install -r requirements.txt
```

**Dependencies:**

```
fastapi==0.104.1          # Web framework
uvicorn==0.24.0           # ASGI server
sqlalchemy==2.0.23        # ORM
python-dotenv==1.0.0      # Environment variables
pydantic==2.5.0           # Data validation
```

### Step 5: Start the Application

```bash
python3 start.py
```

The application will:
1. Install missing Python dependencies
2. Create the SQLite database at `~/.commanddesk/execos.db`
3. Start FastAPI on `http://localhost:8080`
4. Open the browser automatically

---

## Configuration

### Configuration Hierarchy

Configuration is loaded in this order (later overrides earlier):

1. **Defaults** - Built into application code
2. **.env file** - Environment variables from `.env`
3. **Environment** - System environment variables
4. **Database** - Configuration stored in database (for integrations)

### Configuration Files

#### `.env` (Project Root)

Create a `.env` file in the project root to override defaults:

```bash
# Example .env file
PORT=8080
DATABASE_URL=sqlite:////Users/yourusername/.commanddesk/execos.db
PYTHONUNBUFFERED=1
LOG_LEVEL=info
```

**Common Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| PORT | 8080 | Server port |
| DATABASE_URL | `sqlite://...` | Database connection URL |
| LOG_LEVEL | info | Logging level: debug, info, warning, error |
| PYTHONUNBUFFERED | 1 | Real-time Python output |

#### Database Location

SQLite database is stored at:

```
~/.commanddesk/execos.db
```

To use a different location, set in `.env`:

```bash
DATABASE_URL=sqlite:////custom/path/execos.db
```

For PostgreSQL (production):

```bash
DATABASE_URL=postgresql://user:password@localhost/execos_db
```

---

## Database Setup

### First-Time Initialization

The database is automatically created and initialized on first run via `start.py`:

```python
from db.init_db import create_all
create_all()  # Creates all tables
```

This creates:
- All 30+ tables with proper schema
- Indexes on key fields
- Foreign key relationships
- Default configuration records

### Manual Database Initialization

If you need to reinitialize the database:

```bash
python3 -c "from db.init_db import create_all; create_all()"
```

### Reset Database (Delete All Data)

```bash
python3 reset_data.py
```

This removes the database file and recreates it empty. **Warning:** This is destructive!

### Seed Sample Data

```bash
python3 seed_data.py
```

This populates the database with sample projects, tasks, and team members for testing.

### Database Backup

```bash
# Manual backup
cp ~/.commanddesk/execos.db ~/.commanddesk/execos.db.backup.$(date +%Y%m%d)

# Automated backups
# The backup scheduler runs daily (see deployment section)
```

### Database Inspection

Use any SQLite client to inspect the database:

```bash
# SQLite CLI
sqlite3 ~/.commanddesk/execos.db

# Common commands
.tables                    # List all tables
.schema tasks              # Show tasks table schema
SELECT COUNT(*) FROM tasks;  # Count tasks
.quit                      # Exit
```

---

## Environment Variables

### Email Configuration

For SOD/EOD email notifications:

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password    # Use Gmail App Password
SMTP_MODE=starttls                 # starttls | ssl | plain
RECIPIENT_EMAIL=recipient@example.com
SOD_TIME=08:00                     # Start of day (HH:MM)
EOD_TIME=18:00                     # End of day (HH:MM)
```

**Gmail Setup:**
1. Enable 2-step verification on your Google account
2. Generate an [App Password](https://support.google.com/accounts/answer/185833)
3. Use the app password in `SMTP_PASSWORD`

### Jira Integration

```bash
JIRA_BASE_URL=https://company.atlassian.net
JIRA_PAT=your-personal-access-token
JIRA_PROJECT_KEYS=ENG,OPS,INFRA
```

**Getting a Jira PAT:**
1. Go to your Atlassian account settings
2. Create a new API Token or Personal Access Token
3. Copy the token and use it in `JIRA_PAT`

### GitLab Integration

```bash
GITLAB_BASE_URL=https://gitlab.com
GITLAB_ACCESS_TOKEN=your-access-token
GITLAB_PROJECT_IDS=group/project,another/project
```

### Database Selection

For **development** (SQLite - default):
```bash
DATABASE_URL=sqlite:////Users/username/.commanddesk/execos.db
```

For **production** (PostgreSQL):
```bash
DATABASE_URL=postgresql://user:password@hostname:5432/execos_db
```

For **testing** (In-memory SQLite):
```bash
DATABASE_URL=sqlite:///:memory:
```

---

## Running the Application

### Development Mode

```bash
# Simple start (recommended for first-time setup)
python3 start.py
```

This:
- Auto-installs dependencies
- Creates database if needed
- Starts server on port 8080
- Opens browser automatically
- Runs in foreground (Ctrl+C to stop)

### Alternative: Direct Server Start

```bash
python3 web_server.py
```

Same as `start.py` but doesn't auto-open browser.

### Production Mode

With environment variables:

```bash
PORT=8080 \
PYTHONUNBUFFERED=1 \
python3 web_server.py
```

Or using systemd (see Deployment section).

### Access the Application

- **Web UI:** http://localhost:8080
- **API Docs:** http://localhost:8080/docs (Swagger UI)
- **Health Check:** http://localhost:8080/health

### Stop the Application

Press `Ctrl+C` in the terminal where the server is running.

---

## Integration Setup

### Email Integration (SOD/EOD Summaries)

#### 1. Gmail Setup

```bash
# Create .env file with email settings
cat > .env << 'EOF'
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_MODE=starttls
RECIPIENT_EMAIL=your-email@gmail.com
SOD_TIME=08:00
EOD_TIME=18:00
SOD_ENABLED=true
EOD_ENABLED=true
EOF
```

#### 2. Test Email Configuration

Via API:
```bash
curl -X POST http://localhost:8080/api/email/config \
  -H 'Content-Type: application/json' \
  -d '{
    "recipient_email": "you@example.com",
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "you@gmail.com",
    "smtp_password": "app-password",
    "sod_time": "08:00",
    "eod_time": "18:00"
  }'
```

#### 3. Verify Configuration

```bash
curl http://localhost:8080/api/email/config
```

### Jira Integration

#### 1. Get Jira Credentials

Create a Personal Access Token in Jira:
- Log in to Jira
- Settings → Personal Access Tokens
- Create new token
- Copy the token value

#### 2. Configure via API

```bash
curl -X POST http://localhost:8080/api/jira/config \
  -H 'Content-Type: application/json' \
  -d '{
    "base_url": "https://company.atlassian.net",
    "pat": "your-pat-token",
    "project_keys": ["ENG", "OPS"],
    "enabled": true
  }'
```

#### 3. Test Connection

```bash
curl http://localhost:8080/api/jira/config
```

### GitLab Integration

#### 1. Get GitLab Token

```bash
# Log into GitLab
# Settings → Access Tokens
# Create new token with api, read_api scopes
```

#### 2. Configure via API

```bash
curl -X POST http://localhost:8080/api/gitlab/config \
  -H 'Content-Type: application/json' \
  -d '{
    "base_url": "https://gitlab.com",
    "access_token": "your-token",
    "project_ids": ["group/project"],
    "enabled": true
  }'
```

### Outlook Calendar Integration

#### 1. Get Calendar ICS URL

1. Open Outlook
2. Settings → Calendar → Export
3. Copy ICS feed URL

#### 2. Configure via API

```bash
curl -X POST http://localhost:8080/api/outlook/config \
  -H 'Content-Type: application/json' \
  -d '{
    "ics_url": "your-ics-feed-url",
    "enabled": true,
    "working_start": "09:00",
    "working_end": "18:00"
  }'
```

---

## Troubleshooting

### Port Already in Use

**Error:** `Address already in use`

**Solution:**
```bash
# Find process using port 8080
lsof -i :8080

# Kill the process
kill -9 <PID>

# Or use a different port
PORT=8081 python3 start.py
```

### Database Connection Error

**Error:** `sqlite3.OperationalError: unable to open database file`

**Solution:**
```bash
# Create the .commanddesk directory
mkdir -p ~/.commanddesk

# Verify permissions
ls -la ~/.commanddesk
chmod 755 ~/.commanddesk
```

### Python Version Error

**Error:** `Python 3.11 or higher required`

**Solution:**
```bash
# Check Python version
python3 --version

# Install Python 3.11 or higher
# macOS: brew install python@3.11
# Linux: apt-get install python3.11
# Windows: Download from python.org
```

### Module Not Found

**Error:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or let start.py do it automatically
python3 start.py
```

### Database Locked

**Error:** `database is locked`

**Cause:** Another process is accessing the database

**Solution:**
```bash
# Stop all running instances
ps aux | grep python

# Kill any stray processes
kill -9 <PID>

# Restart
python3 start.py
```

### Email Not Sending

**Issue:** SOD/EOD emails not arriving

**Check:**
1. Email configuration is set: `curl http://localhost:8080/api/email/config`
2. SMTP credentials are correct
3. Email is enabled: `sod_enabled: true`, `eod_enabled: true`
4. Server is running at SOD/EOD time
5. Check application logs for errors

**Debug:**
```bash
# Test SMTP connection manually
python3 -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your-email@gmail.com', 'app-password')
print('SMTP connection successful!')
server.quit()
"
```

### Slow Dashboard Loading

**Cause:** Large number of tasks/projects

**Solution:**
1. Cache is 60 seconds - wait for refresh
2. Archive old completed projects
3. Clean up old completed tasks
4. Consider PostgreSQL for larger datasets

### Browser Not Opening

**Issue:** `start.py` runs but browser doesn't open

**Solution:**
```bash
# Manually open browser
open http://localhost:8080

# Or check logs for actual URL
```

### Integrations Not Working

**Check:**
1. Integration is enabled: `/api/{jira,gitlab,email}/config`
2. Credentials are valid (test in original system)
3. Network connectivity to external service
4. Firewall not blocking connections
5. Check application logs for detailed errors

---

## Quick Start Checklist

- [ ] Python 3.11+ installed
- [ ] Project directory accessible
- [ ] Run `python3 start.py`
- [ ] Database created at `~/.commanddesk/execos.db`
- [ ] Server running on `http://localhost:8080`
- [ ] Browser opened to web UI
- [ ] Can create a test task
- [ ] Swagger docs accessible at `/docs`

## Next Steps

1. **Development:** See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
2. **Deployment:** See [DEPLOYMENT_AND_OPERATIONS.md](DEPLOYMENT_AND_OPERATIONS.md)
3. **API Usage:** See [API.md](API.md)
4. **Database:** See [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)
