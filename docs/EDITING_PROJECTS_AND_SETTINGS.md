# Editing Projects, Applications & General Settings

Complete guide to managing projects, applications, and viewing system settings in ExecOS.

## Table of Contents

1. [Editing Projects](#editing-projects)
2. [Deleting Applications (with Cascade)](#deleting-applications-with-cascade)
3. [General Settings](#general-settings)
4. [Database Configuration](#database-configuration)
5. [Backup Management](#backup-management)

---

## Editing Projects

### Via Web UI

**1. Open Projects Page**
- Click "Projects" in the left navigation
- View all projects in card or list format

**2. Click Edit on a Project**
- Each project card has an edit button (pencil icon)
- Or click on the project name to open details

**3. Update Project Details**
- **Name** — Project title (required)
- **Description** — Project details/notes
- **Status** — active, on_hold, completed, archived
- **Owner** — Person responsible for project
- **Due Date** — Target completion date
- **Tags** — Searchable labels
- **Application** — Link to parent application

**4. Save Changes**
- Click "Save" button
- Project updates immediately
- Health score recalculates based on task completion

### Via API

**Get Project**
```bash
curl http://localhost:8080/api/projects/{project_id}
```

**Update Project**
```bash
curl -X PATCH http://localhost:8080/api/projects/{project_id} \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Updated Project Name",
    "status": "active",
    "owner": "John Doe",
    "due_date": "2026-06-30",
    "tags": ["important", "customer-facing"]
  }'
```

**Fields You Can Update:**
- `name` — Project name
- `description` — Project description
- `status` — active|on_hold|completed|archived
- `owner` — Owner name
- `due_date` — Date string (YYYY-MM-DD)
- `tags` — Array of strings
- `application_id` — Parent application UUID

### Project Health Scoring

Projects automatically calculate a **health score** based on:

| Metric | Impact |
|--------|--------|
| Overdue Tasks | Red (critical) |
| Completion Rate ≥ 80% | Green |
| Completion Rate 50-80% | Yellow |
| Completion Rate < 50% | Red |
| No Tasks | Grey |

The health score updates automatically when:
- A task is created/deleted
- A task status changes
- A task due date passes

---

## Deleting Applications (with Cascade)

### What is Cascade Delete?

When you delete an Application, everything underneath gets deleted automatically:

```
Application
  └── Projects (DELETED)
      └── Tasks (DELETED)
      └── Releases (DELETED)
      └── Milestones (DELETED)
```

This prevents orphaned data and keeps your system clean.

### Delete via Web UI

**1. Open Applications Page**
- Click "Applications" in left navigation
- See all applications listed

**2. Click Delete Button**
- Red "Delete" button on each application card
- Confirmation dialog appears

**3. Confirm Deletion**
- Dialog shows: "Delete application and all child projects?"
- Click "Delete" to proceed
- Click "Cancel" to keep the application

**4. Cascade Happens Automatically**
- Application deleted
- All linked projects deleted
- All tasks in those projects deleted
- All releases/milestones deleted
- Complete cleanup in one action

### Delete via API

```bash
# Delete application (cascades to projects and tasks)
curl -X DELETE http://localhost:8080/api/applications/{app_id}
```

**What Gets Deleted:**
- Application record
- All projects with `application_id = {app_id}`
- All tasks in those projects
- All releases linked to those projects
- All milestones linked to those projects

**What Does NOT Get Deleted:**
- Team members
- Alerts (unless specifically linked)
- Activity logs (audit trail preserved)

### Recovery from Accidental Deletion

**If you delete by mistake:**

1. **Check Backup**
   ```bash
   ls -la ~/.commanddesk/execos.db.backup.*
   ```

2. **Stop the Application**
   ```bash
   Ctrl+C  # or systemctl stop execos
   ```

3. **Restore from Backup**
   ```bash
   cp ~/.commanddesk/execos.db.backup.20260514 ~/.commanddesk/execos.db
   ```

4. **Restart**
   ```bash
   python3 start.py
   ```

See [Backup Management](#backup-management) section below.

---

## General Settings

### Access General Settings

**In Web UI:**
1. Click "Settings" in left navigation
2. Click "General Settings" tab
3. View system configuration

**Via API:**
```bash
curl http://localhost:8080/api/settings/general
```

### What's Shown

#### Database Section
Shows your database configuration:

```json
{
  "type": "sqlite",              // or "postgresql"
  "path": "/Users/you/.commanddesk/execos.db",  // Full file path
  "url_masked": "sqlite://..."   // Connection string (masked)
}
```

**For SQLite:** Shows the exact file location where your data is stored

**For PostgreSQL:** Shows the database name (password masked for security)

#### Backup Section
Backup configuration and recommendations:

```json
{
  "enabled": true,
  "location": "/Users/you/.commanddesk/",
  "schedule": "Daily at 2:00 AM",
  "retention_days": 30,
  "recommendation": "Backup execos.db file daily to external storage"
}
```

**Actions to Take:**
1. ✅ Copy the database file regularly
2. ✅ Store backups in cloud (Google Drive, Dropbox, etc.)
3. ✅ Test restore procedure quarterly
4. ✅ Keep 30+ days of backups

#### System Section
System information:

```json
{
  "python_version": "3.11.5",
  "config_file": "/path/to/.env"
}
```

---

## Database Configuration

### Check Current Database

**View Database Path:**
1. Open Settings → General Settings
2. Look for "Database" section
3. Copy the path shown

**In Terminal:**
```bash
# Check what database you're using
echo $DATABASE_URL

# Or check the .env file
cat .env | grep DATABASE_URL
```

### Change Database Location

**For SQLite (File-Based):**

1. **Stop the application**
   ```bash
   Ctrl+C
   ```

2. **Edit .env file**
   ```bash
   nano .env
   ```

3. **Update DATABASE_URL**
   ```bash
   # Old location
   DATABASE_URL=sqlite:////Users/you/.commanddesk/execos.db

   # New location (example: external drive)
   DATABASE_URL=sqlite:////Volumes/ExternalDrive/execos.db
   ```

4. **Create directory if needed**
   ```bash
   mkdir -p /Volumes/ExternalDrive
   ```

5. **Copy existing database (optional)**
   ```bash
   # Backup current database
   cp ~/.commanddesk/execos.db /Volumes/ExternalDrive/

   # Or start fresh
   # (Application will create new database on startup)
   ```

6. **Restart application**
   ```bash
   python3 start.py
   ```

**For PostgreSQL (Server-Based):**

1. **Create PostgreSQL database**
   ```bash
   sudo -u postgres createdb execos_db
   createuser -P execos_user  # Set password when prompted
   ```

2. **Edit .env**
   ```bash
   DATABASE_URL=postgresql://execos_user:password@localhost/execos_db
   ```

3. **Restart**
   ```bash
   python3 start.py
   ```

See [DEPLOYMENT_AND_OPERATIONS.md](DEPLOYMENT_AND_OPERATIONS.md) for more details.

---

## Backup Management

### Manual Backup

**One-Time Backup (SQLite):**
```bash
# Create backup with timestamp
cp ~/.commanddesk/execos.db ~/.commanddesk/execos_$(date +%Y%m%d_%H%M%S).db

# Verify backup exists
ls -lh ~/.commanddesk/execos*.db
```

**Backup to Cloud:**
```bash
# Copy to Google Drive (via rclone or manual)
cp ~/.commanddesk/execos.db ~/Google\ Drive/Backups/execos_$(date +%Y%m%d).db

# Or copy to Dropbox
cp ~/.commanddesk/execos.db ~/Dropbox/Backups/
```

### Automated Backup (Linux/macOS)

**Create backup script:**
```bash
#!/bin/bash
# backup_execos.sh

BACKUP_DIR="$HOME/Backups/execos"
DB_PATH="$HOME/.commanddesk/execos.db"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"
cp "$DB_PATH" "$BACKUP_DIR/execos_$DATE.db"

# Keep only last 30 days
find "$BACKUP_DIR" -name "execos_*.db" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/execos_$DATE.db"
```

**Make executable:**
```bash
chmod +x backup_execos.sh
```

**Schedule with cron (daily at 2 AM):**
```bash
crontab -e

# Add line:
0 2 * * * /home/user/backup_execos.sh >> /var/log/execos_backup.log 2>&1
```

### Backup Locations Recommended

**Local (Quick Recovery):**
- `/Users/you/Backups/execos/` — External SSD
- `~/Documents/Backups/` — On same machine

**Cloud (Disaster Recovery):**
- Google Drive — Auto-synced
- Dropbox — File-level versioning
- AWS S3 — Long-term storage
- OneDrive — Microsoft ecosystem

### Verify Backup Works

**Test Restore Process:**

1. **List backups**
   ```bash
   ls -lh ~/.commanddesk/execos*.db
   ```

2. **Make test copy**
   ```bash
   cp ~/.commanddesk/execos.db ~/.commanddesk/execos_test.db
   ```

3. **Stop app**
   ```bash
   Ctrl+C
   ```

4. **Restore from backup**
   ```bash
   cp ~/.commanddesk/execos_test.db ~/.commanddesk/execos.db
   ```

5. **Start app**
   ```bash
   python3 start.py
   ```

6. **Verify data is intact**
   - Check a few projects
   - Verify task count
   - Check recent activities

---

## Common Tasks

### I can't find my database file

**Solution:**
1. Check Settings → General Settings
2. Look at "Database" → "path"
3. Copy the full path shown
4. Open in File Explorer/Finder

Or in terminal:
```bash
ls -lh ~/.commanddesk/execos.db
```

### I want to move my database to external drive

**Process:**
1. Note current location from Settings
2. Copy the .db file to new location
3. Edit .env with new DATABASE_URL
4. Restart application
5. Verify data is there

### My database is too large

**Solutions:**
1. **Archive old data** — Move completed tasks to archive
2. **Clean activity logs** — Delete old activity records
3. **Upgrade storage** — Use larger drive
4. **Switch to PostgreSQL** — Better for large datasets

### When will my backup happen?

**Check settings:**
- Settings → General Settings → Backup section
- Shows: "Schedule: Daily at 2:00 AM"

**To change backup time:**
- Edit backup script cron time
- See "Automated Backup" section above

### I accidentally deleted a project

**Quick Recovery:**
1. Restore from recent backup
2. Or recreate manually if data is small

**To prevent future accidents:**
- Confirm before delete
- Keep multiple backups
- Archive instead of delete when possible

---

## Troubleshooting

### Database Path Shows as "None"

**Cause:** Something went wrong parsing the database URL

**Solution:**
```bash
# Check your .env file
cat .env | grep DATABASE_URL

# Verify the path exists
ls -la ~/.commanddesk/

# If it doesn't exist, create it
mkdir -p ~/.commanddesk
```

### Cannot Edit Project

**Check:**
1. Is the project linked to an application?
2. Do you have write permissions?
3. Is another user editing it simultaneously?

**Solution:**
- Refresh page
- Restart server
- Check user permissions

### Cascade Delete Didn't Work

**Check:**
- Did projects actually have tasks?
- Were there other errors?
- Check application logs

**If data is stuck:**
```bash
# Manually clean up orphaned records
sqlite3 ~/.commanddesk/execos.db

# List orphaned projects (no application)
SELECT * FROM projects WHERE application_id IS NULL;

# Delete manually if needed
DELETE FROM projects WHERE application_id = 'non-existent-id';
```

---

## API Reference

### Projects

```
GET    /api/projects              # List all
POST   /api/projects              # Create
GET    /api/projects/{id}         # Get one
PATCH  /api/projects/{id}         # Update
DELETE /api/projects/{id}         # Delete (cascades tasks)
```

### Applications

```
GET    /api/applications          # List all
POST   /api/applications          # Create
GET    /api/applications/{id}     # Get one
PATCH  /api/applications/{id}     # Update
DELETE /api/applications/{id}     # Delete (cascades projects)
GET    /api/applications/{id}/projects
```

### Settings

```
GET    /api/settings/general      # System & backup info
GET    /api/settings/jira         # Jira config
POST   /api/settings/jira         # Update Jira
GET    /api/settings/gitlab       # GitLab config
POST   /api/settings/gitlab       # Update GitLab
```

---

## Best Practices

✅ **Do:**
- Keep regular backups (daily minimum)
- Archive old completed projects instead of deleting
- Use applications to group related projects
- Test restore procedure quarterly
- Store backups in cloud
- Check Settings → General regularly

❌ **Don't:**
- Delete applications without backup
- Modify database file directly
- Ignore backup warnings
- Keep backups only on same machine
- Delete tasks individually when you can delete the project

---

## Next Steps

- [Backup and Recovery](DEPLOYMENT_AND_OPERATIONS.md#backup-and-recovery)
- [Database Schema](DATABASE_SCHEMA.md)
- [API Documentation](API.md)
