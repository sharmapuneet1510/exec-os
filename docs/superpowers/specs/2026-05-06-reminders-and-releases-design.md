# Reminders & Release Visibility Design

**Date:** 2026-05-06  
**Author:** Claude Code  
**Status:** Design Phase  

## Overview

This design adds two features to ExecOS:
1. **Reminders System** — Independent + task-linked reminders with snooze, recurring patterns, and email integration
2. **Release Visibility** — Releases appear in dashboards and link to both projects and applications

## Problem Statement

### Issue 1: Release Invisibility
- Releases are stored in `ReleaseORM` but not displayed in any dashboard
- Releases only link to projects; applications have no direct release association
- Portfolio-level release planning is impossible

### Issue 2: Missing Reminders
- No dedicated reminder system; tasks have `reminder_date` but no triggering logic
- No email notifications for reminders
- No SOD/EOD integration for reminders
- No snooze/recurring reminder support

## Solution

### Approach: Hybrid Reminder System + Dual-Linked Releases

**Reminder System (Approach 3):**
- New `ReminderORM` table with support for fixed-time and relative-interval scheduling
- Both task-linked and independent reminders
- Snooze capability with `snooze_until` field
- Recurring pattern support (daily, weekly, specific days)
- Background scheduler (APScheduler) runs every 5 minutes
- Reminders create `AlertORM` entries → integrated into email system
- Configurable SOD/EOD email inclusion per user

**Release Visibility:**
- Add `application_id` FK to `ReleaseORM` (keep `project_id` for dual association)
- Releases appear in both operational and executive dashboards
- Operational: upcoming releases card (7-30 day window)
- Executive: portfolio health aggregation by application + status

## Database Schema

### New Table: `reminders`

```sql
CREATE TABLE reminders (
    reminder_id VARCHAR PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT DEFAULT '',
    reminder_type VARCHAR(20) NOT NULL,  -- 'task' or 'independent'
    task_id VARCHAR FOREIGN KEY NULLABLE,  -- FK to tasks, only if reminder_type='task'
    trigger_type VARCHAR(20) NOT NULL,  -- 'fixed_time' or 'relative_interval'
    trigger_value VARCHAR(50) NOT NULL,  -- "HH:MM" or "1d" / "2h" / "-1day_before_due"
    trigger_date DATE NULLABLE,  -- for fixed_time reminders
    due_date DATE NULLABLE,  -- reference date for relative_interval
    recurrence_pattern TEXT DEFAULT '{}',  -- JSON: {"type": "daily"} or {"type": "weekly", "days": ["Mon", "Fri"]}
    is_active BOOLEAN DEFAULT TRUE,
    last_triggered DATETIME NULLABLE,
    snooze_until DATETIME NULLABLE,
    include_in_sod BOOLEAN DEFAULT TRUE,
    include_in_eod BOOLEAN DEFAULT TRUE,
    priority VARCHAR(20) DEFAULT 'medium',  -- 'low', 'medium', 'high'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Fields Explained:**
- `reminder_type`: 'task' = linked to a task; 'independent' = standalone
- `task_id`: Only populated if `reminder_type='task'`. If task is deleted, becomes null (reminder persists)
- `trigger_type`: Determines how trigger_value is interpreted
  - 'fixed_time': fires on `trigger_date` at time in `trigger_value` (HH:MM)
  - 'relative_interval': fires relative to `due_date` (e.g., "-1d" = 1 day before due_date)
- `trigger_value`: 
  - For fixed_time: "14:30" (2:30 PM)
  - For relative_interval: "-1d", "-2h", "+3d" (before/after reference)
- `recurrence_pattern`: JSON
  - `{"type": "once"}` — default
  - `{"type": "daily"}`
  - `{"type": "weekly", "days": ["Mon", "Wed", "Fri"]}`
  - `{"type": "custom", "interval": 7}` — every 7 days
- `last_triggered`: Tracks when reminder last fired (for recurrence calculations)
- `snooze_until`: If set, scheduler skips this reminder until datetime passes
- `include_in_sod` / `include_in_eod`: User controls whether reminder appears in SOD/EOD email

### Modified Table: `releases`

Add column to existing `ReleaseORM`:
```sql
ALTER TABLE releases ADD COLUMN application_id VARCHAR FOREIGN KEY NULLABLE;
```

**Rationale:** A release can now belong to an application AND/OR a project. This allows:
- Application-level release planning (multiple projects per app)
- Project-level release tracking (classic model)
- Cross-app release visibility on executive dashboard

### Modified Table: `email_config`

Add column to existing `EmailConfigORM`:
```sql
ALTER TABLE email_config ADD COLUMN reminder_priority_filter VARCHAR DEFAULT 'all';
-- Values: 'all' (show all reminders), 'high_only', 'high_medium'
```

## API Endpoints

### Reminders Router: `/api/reminders`

**POST /api/reminders**
```json
{
  "title": "Review Q2 roadmap",
  "description": "Quarterly planning session",
  "reminder_type": "independent",
  "task_id": null,
  "trigger_type": "fixed_time",
  "trigger_value": "14:30",
  "trigger_date": "2026-05-15",
  "recurrence_pattern": {"type": "once"},
  "include_in_sod": true,
  "include_in_eod": false,
  "priority": "high"
}
```
Returns: Created reminder object

**GET /api/reminders?active=true&type=task&priority=high**
Returns: Array of reminders, filterable

**GET /api/reminders/{id}**
Returns: Single reminder object

**PATCH /api/reminders/{id}**
Accepts: Any subset of reminder fields (title, priority, recurrence_pattern, etc.)
Returns: Updated reminder

**DELETE /api/reminders/{id}**
Returns: 204 No Content

**POST /api/reminders/{id}/snooze**
```json
{"snooze_minutes": 60}
```
Sets `snooze_until` to now + snooze_minutes, returns updated reminder

**POST /api/reminders/{id}/trigger** (testing endpoint)
Manually fires reminder, creates alert, returns result

## Background Scheduler

**Service:** `services/reminder_scheduler.py`

```python
class ReminderScheduler:
    def run(self):
        """Runs every 5 minutes"""
        reminders = db.query(ReminderORM).filter(ReminderORM.is_active == True).all()
        
        for reminder in reminders:
            # Skip if snoozed
            if reminder.snooze_until and reminder.snooze_until > datetime.utcnow():
                continue
            
            # Check if reminder should trigger
            if self._should_trigger(reminder):
                self._fire_reminder(reminder)
    
    def _should_trigger(self, reminder) -> bool:
        """Determine if reminder condition is met"""
        if reminder.trigger_type == 'fixed_time':
            # Fire on trigger_date at trigger_value time
            now = datetime.utcnow()
            return (now.date() == reminder.trigger_date and 
                    now.time() >= parse_time(reminder.trigger_value))
        
        elif reminder.trigger_type == 'relative_interval':
            # Fire relative to due_date
            reference = reminder.due_date or reminder.task.due_date
            target_datetime = self._calculate_target_datetime(reference, reminder.trigger_value)
            return datetime.utcnow() >= target_datetime
        
        return False
    
    def _fire_reminder(self, reminder):
        """Create alert, update last_triggered, handle recurrence"""
        # Create alert
        alert = AlertORM(
            title=f"Reminder: {reminder.title}",
            message=reminder.description,
            severity=self._priority_to_severity(reminder.priority),
            source="reminder"
        )
        db.add(alert)
        
        # Update last_triggered
        reminder.last_triggered = datetime.utcnow()
        
        # Handle recurrence
        if reminder.recurrence_pattern.get('type') != 'once':
            # Calculate next trigger, keep is_active=True
            reminder.next_trigger = self._calculate_next_trigger(reminder)
        else:
            # One-time reminder: deactivate
            reminder.is_active = False
        
        db.commit()
```

**Integration with Email System:**
- SOD email job queries: `AlertORM` where `source="reminder"` and `include_in_sod=True`
- EOD email job queries: Same, but `include_in_eod=True`
- User's `reminder_priority_filter` from `EmailConfigORM` filters which reminders appear
- Reminders grouped by priority in email body

## Dashboard Updates

### Operational Dashboard: `/api/dashboard/operational`

Add new section:
```json
{
  "upcoming_releases": [
    {
      "release_id": "...",
      "name": "v2.5",
      "version": "2.5.0",
      "application_name": "MyApp",
      "project_name": "Backend Services",
      "due_date": "2026-05-20",
      "status": "planned",
      "days_until": 14
    }
  ]
}
```

**Logic:** Releases where `due_date` is 7-30 days away and `status` in ['planned', 'in_progress'], ordered by due_date

### Executive Dashboard: `/api/dashboard/executive`

Add new section:
```json
{
  "releases_by_status": {
    "planned": 5,
    "in_progress": 2,
    "released": 12,
    "rollback": 0
  },
  "release_health": [
    {
      "application_id": "...",
      "application_name": "MyApp",
      "total_releases": 7,
      "on_time": 6,
      "overdue": 1,
      "health_pct": 86,
      "health": "green"
    }
  ]
}
```

**Logic:** 
- Aggregates releases by application
- Health % = (on_time / total) * 100
- Health color: green (>80%), yellow (50-80%), red (<50%)

## SOD/EOD Email Updates

### SOD Summary: `/api/dashboard/sod`

Add reminders section:
```json
{
  "date": "2026-05-06",
  "reminders": [
    {
      "reminder_id": "...",
      "title": "Review Q2 roadmap",
      "priority": "high",
      "trigger_time": "14:30"
    }
  ]
}
```

Email format:
```
REMINDERS (2)
🔴 High: Review Q2 roadmap — due at 2:00 PM
🟡 Medium: 1-on-1 with Alex — tomorrow 10:00 AM
```

### EOD Summary: `/api/dashboard/eod`

Same structure as SOD, but filtered by `include_in_eod`.

## Frontend UI

### Reminders Management Page

**Views:**
1. **List view** — Filterable table with columns: Title, Type (task/independent), Next Due, Priority, Status (active/snoozed)
2. **Create/Edit modal** — Form fields:
   - Title, Description
   - Type picker: Task (auto-populates task_id) or Independent
   - Trigger type: Fixed Time or Relative Interval
   - For Fixed Time: Date picker + time input
   - For Relative: Due date + offset selector (-1d, -2h, etc.)
   - Recurrence: Pattern picker (once/daily/weekly/custom)
   - Include in SOD/EOD checkboxes
   - Priority selector
3. **Quick actions:**
   - Snooze button (1h, 2h, 1d, custom)
   - Edit, Delete buttons
   - Manual trigger (testing only, hidden by default)

### Release Visibility in Dashboards

**Operational Dashboard:**
- New card: "Upcoming Releases"
- List of 5-10 releases, sortable by due_date
- Each row shows: Release name, version, app/project names, due date, status badge
- Click to view release details (currently read-only; future: edit endpoint)

**Executive Dashboard:**
- New card: "Release Portfolio"
- Status counts (planned, in_progress, released, rollback)
- Per-app health table: Application, Total Releases, On-Time %, Health indicator

### Alerts Integration

When a reminder fires and creates an alert:
- Alert appears in the Alerts list with source="reminder"
- User can:
  - Mark as read (dismiss)
  - Snooze directly (shows snooze options)
  - Click to edit the original reminder
- Snoozed alerts show "snoozed until X" time

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Background job fails | Logged to activity_logs; scheduler continues next cycle |
| Malformed recurrence_pattern JSON | Treat as "once", log warning |
| Task-linked reminder, task deleted | task_id becomes null, reminder persists as independent |
| Relative reminder with no due_date | Skipped, logged warning |
| Email send fails | Alert still created; marked for retry on next SOD/EOD run |
| Snooze past midnight | Honored precisely; no date-boundary issues |
| Recurring reminder on Feb 29 | Handled by date arithmetic library; no recurrence that year if pattern is yearly |

## Testing Strategy

**Unit Tests:**
- ReminderScheduler._should_trigger() with fixed_time, relative_interval, recurrence patterns
- Recurrence pattern calculation (next occurrence)
- Priority-to-severity mapping
- Snooze logic (skip when snoozed, fire after snooze expires)

**Integration Tests:**
- Create reminder → background job triggers → alert created → SOD/EOD includes it
- Task-linked reminder with task deletion → reminder_type changes, task_id nulled
- Relative interval reminder referencing task due_date
- Recurring reminder fires multiple times (weekly Mon/Wed/Fri)
- Email config filter: 'high_only' excludes low/medium reminders

**Manual Testing:**
- Create independent + task-linked reminders
- Test snooze (verify skipped, then fires after snooze expires)
- SOD/EOD emails include correct reminders per filter
- Operational dashboard shows upcoming releases
- Executive dashboard shows release health by app

## Scope & Limits

**In Scope:**
- Reminders CRUD API
- Background scheduler (every 5 min)
- Snooze + one-time/recurring patterns
- Email integration (SOD/EOD)
- Release dashboard visibility
- Release-to-application dual linking

**Out of Scope (Phase 2+):**
- Desktop/push notifications (handled by email for now)
- Reminder edit UI in web app (CRUD API exists; UI TBD)
- Bulk import reminders from external sources
- Reminder templates
- AI-powered reminder suggestions
- Holiday calendar integration for snooze

## Success Criteria

1. ✅ Reminders created and persisted
2. ✅ Background job triggers reminders on schedule
3. ✅ Snooze prevents firing for duration, then fires again
4. ✅ Recurring reminders calculate next occurrence correctly
5. ✅ Reminders appear in SOD/EOD emails (respecting filter config)
6. ✅ Releases visible in both dashboards
7. ✅ Releases link to both projects and applications
8. ✅ Dashboard release aggregations correct (by app, by status, health %)
9. ✅ All endpoints have tests (unit + integration)
10. ✅ No background job crashes; failures logged and retried

## Implementation Order

1. Database schema changes (reminders table + releases.application_id)
2. ReminderORM + migrations
3. Reminders router (CRUD endpoints)
4. ReminderScheduler service + APScheduler integration
5. AlertORM integration (fire reminder → create alert)
6. Email system updates (query reminders, include in SOD/EOD)
7. Dashboard updates (operational + executive releases)
8. Web UI: Reminders list + create/edit modals
9. Web UI: Releases on dashboards
10. Testing (unit + integration + manual)
