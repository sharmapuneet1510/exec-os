# ExecOS Database Schema

Complete reference for the SQLite database schema, including all tables, fields, relationships, and constraints.

## Overview

ExecOS uses SQLite for persistent storage. The database file is located at:

```
~/.commanddesk/execos.db
```

All tables are created automatically on first startup via `db/init_db.py`.

---

## Core Tables

### `projects`

Stores project information and metadata.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `project_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `name` | TEXT | NOT NULL | Project name |
| `description` | TEXT | | Project description |
| `status` | TEXT | | Status: `active`, `on_hold`, `completed`, `archived` |
| `owner` | TEXT | | Project owner name |
| `start_date` | DATE | | Project start date |
| `due_date` | DATE | | Project due date |
| `tags` | TEXT | | JSON array of tag strings |
| `application_id` | TEXT | FK → applications | Associated application |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW, ON UPDATE NOW | Last update timestamp |

**Indexes:** `project_id` (primary key), `status`, `application_id`

**Example:**

```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Dashboard Redesign",
  "description": "Complete redesign of admin dashboard",
  "status": "active",
  "owner": "John Doe",
  "start_date": "2026-05-01",
  "due_date": "2026-06-30",
  "tags": "[\"frontend\", \"design\"]",
  "application_id": "app-uuid",
  "created_at": "2026-05-14T10:30:00",
  "updated_at": "2026-05-14T15:45:00"
}
```

---

### `tasks`

Stores individual work items.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `task_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `title` | TEXT | NOT NULL | Task title |
| `description` | TEXT | | Task description |
| `due_date` | DATE | | Task due date |
| `reminder_date` | DATE | | Date to send reminder |
| `priority` | TEXT | | `low`, `medium`, `high`, `critical` |
| `status` | TEXT | | `todo`, `in_progress`, `done`, `cancelled` |
| `project_id` | TEXT | FK → projects (CASCADE) | Parent project |
| `application_id` | TEXT | FK → applications | Associated application |
| `assignee_id` | TEXT | FK → team_members | Assigned team member |
| `tags` | TEXT | | JSON array of tag strings |
| `postponed_count` | INTEGER | DEFAULT 0 | Number of times postponed |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |
| `completed_at` | DATETIME | | When task was completed |

**Indexes:** `task_id`, `status`, `priority`, `project_id`, `assignee_id`

**Foreign Keys:**
- `project_id` → `projects.project_id` (ON DELETE SET NULL)
- `application_id` → `applications.application_id` (ON DELETE SET NULL)
- `assignee_id` → `team_members.member_id` (ON DELETE SET NULL)

**Example:**

```json
{
  "task_id": "650e8400-e29b-41d4-a716-446655440001",
  "title": "Design dashboard mockup",
  "description": "Create responsive dashboard mockups in Figma",
  "due_date": "2026-05-20",
  "reminder_date": "2026-05-19",
  "priority": "high",
  "status": "in_progress",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "assignee_id": "mem-uuid",
  "tags": "[\"design\", \"ui\"]",
  "postponed_count": 1,
  "created_at": "2026-05-14T10:30:00",
  "updated_at": "2026-05-14T14:20:00",
  "completed_at": null
}
```

---

### `releases`

Tracks version releases with milestones and dates.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `release_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `name` | TEXT | NOT NULL | Release name |
| `version` | TEXT | | Version number (e.g., `2.1.0`) |
| `project_id` | TEXT | FK → projects | Parent project |
| `application_id` | TEXT | FK → applications | Associated application |
| `due_date` | DATE | | Release due date |
| `start_date` | DATE | | Release start date |
| `uat_date` | DATE | | User acceptance testing date |
| `sign_off_date` | DATE | | Sign-off date |
| `jira_project_key` | TEXT | | Jira project key |
| `status` | TEXT | | `planned`, `in_progress`, `released`, `rollback` |
| `description` | TEXT | | Release description |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

**Foreign Keys:**
- `project_id` → `projects.project_id` (ON DELETE CASCADE)
- `application_id` → `applications.application_id` (ON DELETE SET NULL)

---

### `milestones`

Key checkpoints within projects and releases.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `milestone_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `title` | TEXT | NOT NULL | Milestone title |
| `description` | TEXT | | Milestone description |
| `project_id` | TEXT | FK → projects | Parent project |
| `release_id` | TEXT | FK → releases | Associated release |
| `due_date` | DATE | | Milestone due date |
| `status` | TEXT | | `pending`, `in_progress`, `completed` |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

**Foreign Keys:**
- `project_id` → `projects.project_id` (ON DELETE CASCADE)
- `release_id` → `releases.release_id` (ON DELETE SET NULL)

---

### `commitments`

Promises or deliverables tracked as fulfilled or missed.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `commitment_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `title` | TEXT | NOT NULL | Commitment title |
| `description` | TEXT | | Commitment description |
| `due_date` | DATE | | Commitment due date |
| `status` | TEXT | | `pending`, `fulfilled`, `missed` |
| `task_id` | TEXT | | Associated task ID (optional) |
| `project_id` | TEXT | FK → projects | Associated project |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

**Foreign Keys:**
- `project_id` → `projects.project_id` (ON DELETE SET NULL)

---

### `alerts`

System and user-generated alerts with severity levels.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `alert_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `title` | TEXT | NOT NULL | Alert title |
| `message` | TEXT | | Alert message |
| `severity` | TEXT | | `info`, `warning`, `critical` |
| `source` | TEXT | | Source system (e.g., `system`, `jira`, `user`) |
| `is_read` | BOOLEAN | DEFAULT FALSE | Whether alert has been read |
| `is_snoozed` | BOOLEAN | DEFAULT FALSE | Whether alert is snoozed |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `snoozed_until` | DATETIME | | When snooze expires |

**Indexes:** `alert_id`, `is_read`, `severity`

---

### `reminders`

Reminders that can be triggered at fixed times or relative intervals.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `reminder_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `title` | TEXT | NOT NULL | Reminder title |
| `description` | TEXT | | Reminder description |
| `reminder_type` | TEXT | | `independent`, `task` |
| `task_id` | TEXT | FK → tasks | Associated task |
| `trigger_type` | TEXT | NOT NULL | `fixed_time` or `relative_interval` |
| `trigger_value` | TEXT | NOT NULL | `HH:MM` or `-1d`, `2h`, etc. |
| `trigger_date` | DATE | | For fixed_time reminders |
| `due_date` | DATE | | Reference date for relative intervals |
| `recurrence_pattern` | TEXT | | JSON: `{"type": "daily"}`, etc. |
| `is_active` | BOOLEAN | DEFAULT TRUE | Whether reminder is active |
| `last_triggered` | DATETIME | | When reminder was last triggered |
| `snooze_until` | DATETIME | | When snooze expires |
| `include_in_sod` | BOOLEAN | DEFAULT TRUE | Include in SOD summary |
| `include_in_eod` | BOOLEAN | DEFAULT TRUE | Include in EOD summary |
| `priority` | TEXT | | `low`, `medium`, `high` |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

**Foreign Keys:**
- `task_id` → `tasks.task_id` (ON DELETE SET NULL)

---

## Integration Tables

### `email_config`

Email configuration for SOD/EOD notifications.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `id` | INTEGER | PRIMARY KEY | Singleton (always 1) |
| `recipient_email` | TEXT | | Email recipient |
| `smtp_host` | TEXT | DEFAULT `smtp.gmail.com` | SMTP server |
| `smtp_port` | INTEGER | DEFAULT 587 | SMTP port |
| `smtp_user` | TEXT | | SMTP user/email |
| `smtp_password` | TEXT | | SMTP password (plaintext) |
| `smtp_mode` | TEXT | DEFAULT `starttls` | `starttls`, `ssl`, `plain` |
| `sod_time` | TEXT | DEFAULT `08:00` | SOD email time (HH:MM) |
| `eod_time` | TEXT | DEFAULT `18:00` | EOD email time (HH:MM) |
| `sod_enabled` | BOOLEAN | DEFAULT TRUE | Enable SOD email |
| `eod_enabled` | BOOLEAN | DEFAULT TRUE | Enable EOD email |
| `reminder_priority_filter` | TEXT | DEFAULT `all` | Filter reminders by priority |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

**Note:** Only one row with `id = 1` should exist.

---

### `jira_config`

Jira integration configuration.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `id` | INTEGER | PRIMARY KEY | Singleton (always 1) |
| `base_url` | TEXT | | Jira base URL |
| `pat` | TEXT | | Personal Access Token |
| `project_keys` | TEXT | | JSON array of project keys |
| `enabled` | BOOLEAN | DEFAULT FALSE | Integration enabled |
| `last_synced` | DATETIME | | Last sync timestamp |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

---

### `gitlab_config`

GitLab integration configuration.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `id` | INTEGER | PRIMARY KEY | Singleton (always 1) |
| `base_url` | TEXT | DEFAULT `https://gitlab.com` | GitLab base URL |
| `access_token` | TEXT | | Access token |
| `project_ids` | TEXT | | JSON array of project IDs |
| `enabled` | BOOLEAN | DEFAULT FALSE | Integration enabled |
| `last_synced` | DATETIME | | Last sync timestamp |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

---

### `outlook_config`

Outlook calendar integration configuration.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `id` | INTEGER | PRIMARY KEY | Singleton (always 1) |
| `ics_url` | TEXT | | Outlook ICS feed URL |
| `enabled` | BOOLEAN | DEFAULT FALSE | Integration enabled |
| `working_start` | TEXT | DEFAULT `09:00` | Working hours start (HH:MM) |
| `working_end` | TEXT | DEFAULT `18:00` | Working hours end (HH:MM) |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

---

## Entity Tables

### `applications`

Applications/products within the organization.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `application_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `name` | TEXT | NOT NULL | Application name |
| `code` | TEXT | | Application code |
| `description` | TEXT | | Application description |
| `owner` | TEXT | | Application owner |
| `status` | TEXT | DEFAULT `active` | `active`, `on_hold`, `archived` |
| `jira_project_key` | TEXT | | Primary Jira project key |
| `jira_projects` | TEXT | | JSON array of Jira keys |
| `gitlab_projects` | TEXT | | JSON array of GitLab paths |
| `sprints` | TEXT | | JSON array of sprint objects |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

---

### `team_members`

Team members and their capacity.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `member_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `name` | TEXT | NOT NULL | Member name |
| `email` | TEXT | | Member email |
| `gitlab_username` | TEXT | | GitLab username |
| `role` | TEXT | | Job role/title |
| `is_active` | BOOLEAN | DEFAULT TRUE | Whether member is active |
| `is_team_member` | BOOLEAN | DEFAULT FALSE | Whether in team |
| `max_concurrent_tasks` | INTEGER | DEFAULT 8 | Max concurrent tasks |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

---

### `resource_allocations`

Team member allocation to projects over time periods.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `allocation_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `member_id` | TEXT | NOT NULL, FK → team_members | Team member |
| `project_id` | TEXT | NOT NULL, FK → projects | Project |
| `start_date` | DATE | NOT NULL | Allocation start |
| `end_date` | DATE | NOT NULL | Allocation end |
| `allocation_pct` | INTEGER | DEFAULT 100 | % allocated |
| `role` | TEXT | | Role on project |
| `notes` | TEXT | | Allocation notes |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

**Foreign Keys:**
- `member_id` → `team_members.member_id` (ON DELETE CASCADE)
- `project_id` → `projects.project_id` (ON DELETE CASCADE)

---

## Estimation Tables

### `estimations`

Work effort estimations with complexity and testing factors.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `estimation_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `title` | TEXT | NOT NULL | Estimation title |
| `task_id` | TEXT | | Associated task |
| `project_id` | TEXT | FK → projects | Associated project |
| `story_points` | INTEGER | DEFAULT 1 | Story points |
| `complexity` | TEXT | | `low`, `medium`, `high`, `very_high` |
| `testing_effort` | TEXT | | `none`, `light`, `moderate`, `thorough` |
| `has_release_paperwork` | BOOLEAN | DEFAULT FALSE | Requires release paperwork |
| `velocity` | INTEGER | DEFAULT 2 | Story points per working day |
| `start_date` | DATE | | Estimation start date |
| `holidays` | TEXT | | JSON array of holiday dates |
| `dev_days` | INTEGER | | Calculated development days |
| `testing_days` | INTEGER | | Calculated testing days |
| `paperwork_days` | INTEGER | | Calculated paperwork days |
| `holiday_buffer_days` | INTEGER | | Holiday buffer days |
| `total_working_days` | INTEGER | | Total calculated days |
| `estimated_end_date` | DATE | | Estimated completion date |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |

---

### `proj_estimates`

Project-level estimation with hierarchical tasks.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `est_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `name` | TEXT | NOT NULL | Estimate name |
| `description` | TEXT | | Estimate description |
| `start_date` | DATE | | Project start date |
| `end_date_constraint` | DATE | | Hard deadline |
| `jira_project_key` | TEXT | | Associated Jira project |
| `application_id` | TEXT | | Associated application |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

---

### `proj_est_milestones`

Milestones within a project estimation.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `ms_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `est_id` | TEXT | NOT NULL, FK → proj_estimates | Parent estimate |
| `name` | TEXT | NOT NULL | Milestone name |
| `description` | TEXT | | Milestone description |
| `order` | INTEGER | | Display order |
| `execution_type` | TEXT | | `sequential`, `parallel` |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |

**Foreign Keys:**
- `est_id` → `proj_estimates.est_id` (ON DELETE CASCADE)

---

### `proj_est_tasks`

Tasks within estimation milestones.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `task_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `ms_id` | TEXT | NOT NULL, FK → proj_est_milestones | Parent milestone |
| `name` | TEXT | NOT NULL | Task name |
| `description` | TEXT | | Task description |
| `duration_days` | INTEGER | DEFAULT 1 | Estimated days |
| `execution_type` | TEXT | | `sequential`, `parallel` |
| `order` | INTEGER | | Display order |
| `assignee` | TEXT | | Assigned person |
| `jira_key` | TEXT | | Associated Jira key |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |

**Foreign Keys:**
- `ms_id` → `proj_est_milestones.ms_id` (ON DELETE CASCADE)

---

## Delivery Tables

### `delivery_templates`

Templates for release deliverables and checklists.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `template_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `name` | TEXT | NOT NULL | Template name |
| `description` | TEXT | | Template description |
| `is_default` | BOOLEAN | DEFAULT FALSE | Default template |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

---

### `delivery_template_items`

Checklist items within a delivery template.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `item_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `template_id` | TEXT | NOT NULL, FK → delivery_templates | Parent template |
| `order` | INTEGER | | Display order |
| `title` | TEXT | NOT NULL | Item title |
| `description` | TEXT | | Item description |
| `category` | TEXT | | `pre_release`, `release`, `post_release` |
| `responsible_role` | TEXT | | Role responsible |
| `is_required` | BOOLEAN | DEFAULT TRUE | Required item |

**Foreign Keys:**
- `template_id` → `delivery_templates.template_id` (ON DELETE CASCADE)

---

### `delivery_releases`

Release records with delivery template tracking.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `release_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `name` | TEXT | NOT NULL | Release name |
| `version` | TEXT | | Version number |
| `application_id` | TEXT | | Associated application |
| `project_id` | TEXT | | Associated project |
| `template_id` | TEXT | | Delivery template used |
| `release_manager` | TEXT | | Release manager name |
| `target_date` | DATE | | Target release date |
| `start_date` | DATE | | Release start date |
| `release_date` | DATE | | Actual release date |
| `uat_date` | DATE | | UAT date |
| `sign_off_date` | DATE | | Sign-off date |
| `jira_project_key` | TEXT | | Jira project key |
| `status` | TEXT | | `planned`, `in_progress`, `released`, `rollback` |
| `description` | TEXT | | Release description |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

---

### `delivery_release_items`

Checklist items for a specific delivery release.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `item_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `release_id` | TEXT | NOT NULL, FK → delivery_releases | Parent release |
| `order` | INTEGER | | Display order |
| `title` | TEXT | NOT NULL | Item title |
| `description` | TEXT | | Item description |
| `category` | TEXT | | `pre_release`, `release`, `post_release` |
| `responsible_role` | TEXT | | Role responsible |
| `status` | TEXT | | `pending`, `in_progress`, `done`, `skipped`, `blocked` |
| `assignee` | TEXT | | Assigned person |
| `notes` | TEXT | | Item notes |
| `is_required` | BOOLEAN | DEFAULT TRUE | Required item |
| `completed_at` | DATETIME | | Completion timestamp |

**Foreign Keys:**
- `release_id` → `delivery_releases.release_id` (ON DELETE CASCADE)

---

## Activity & Audit Tables

### `audit_logs`

Audit trail for entity changes.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `log_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `entity_type` | TEXT | NOT NULL | `task`, `project`, `release`, etc. |
| `entity_id` | TEXT | NOT NULL | ID of entity |
| `action` | TEXT | NOT NULL | `created`, `updated`, `deleted` |
| `detail` | TEXT | | Change details (JSON) |
| `created_at` | DATETIME | DEFAULT NOW | Timestamp |

---

### `activity_logs`

HTTP request/response activity log.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `log_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `method` | TEXT | NOT NULL | HTTP method |
| `endpoint` | TEXT | NOT NULL | API endpoint |
| `status_code` | INTEGER | | HTTP status code |
| `request_headers` | TEXT | | Request headers (JSON) |
| `request_body` | TEXT | | Request body |
| `response_headers` | TEXT | | Response headers (JSON) |
| `response_body` | TEXT | | Response body |
| `duration_ms` | INTEGER | | Request duration (ms) |
| `error` | TEXT | | Error message if failed |
| `created_at` | DATETIME | DEFAULT NOW | Timestamp |

---

### `entity_activity_logs`

High-level entity activity tracking.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `activity_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `entity_type` | TEXT | NOT NULL | Entity type |
| `entity_id` | TEXT | NOT NULL | Entity ID |
| `action` | TEXT | NOT NULL | `created`, `updated`, `deleted` |
| `description` | TEXT | | Human-readable description |
| `details` | TEXT | | Change details (JSON) |
| `created_at` | DATETIME | DEFAULT NOW | Timestamp |

---

## Sprint & Configuration Tables

### `sprint_config`

Sprint configuration for Jira/GitLab sync.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `id` | INTEGER | PRIMARY KEY | Singleton |
| `board_id` | TEXT | | Jira board ID |
| `sprint_id` | TEXT | | Active sprint ID |
| `sprint_name` | TEXT | | Sprint name |
| `my_jira_email` | TEXT | | User's Jira email |
| `my_gitlab_username` | TEXT | | User's GitLab username |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

---

### `app_jira_configs`

Per-application Jira configuration.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `application_id` | TEXT | NOT NULL, UNIQUE | Application ID |
| `base_url` | TEXT | | Jira base URL |
| `pat` | TEXT | | Personal Access Token |
| `project_keys` | TEXT | | JSON array of project keys |
| `enabled` | BOOLEAN | DEFAULT FALSE | Integration enabled |
| `last_synced` | DATETIME | | Last sync timestamp |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

---

### `app_gitlab_configs`

Per-application GitLab configuration.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `application_id` | TEXT | NOT NULL, UNIQUE | Application ID |
| `base_url` | TEXT | DEFAULT `https://gitlab.com` | GitLab base URL |
| `access_token` | TEXT | | Access token |
| `project_ids` | TEXT | | JSON array of project IDs |
| `enabled` | BOOLEAN | DEFAULT FALSE | Integration enabled |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

---

### `app_sprint_configs`

Per-application sprint configuration.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `application_id` | TEXT | NOT NULL, UNIQUE | Application ID |
| `board_id` | TEXT | | Jira board ID |
| `sprint_id` | TEXT | | Sprint ID |
| `sprint_name` | TEXT | | Sprint name |
| `my_jira_email` | TEXT | | User's Jira email |
| `my_gitlab_username` | TEXT | | User's GitLab username |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

---

## Mock Tables (for Testing)

### `mock_jira_issues`

Mock Jira issues for development/testing.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `issue_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `key` | TEXT | NOT NULL, UNIQUE | Jira issue key |
| `summary` | TEXT | NOT NULL | Issue summary |
| `assignee_email` | TEXT | | Assignee email |
| `status` | TEXT | DEFAULT `To Do` | Issue status |
| `priority` | TEXT | DEFAULT `Medium` | Issue priority |
| `project_key` | TEXT | | Jira project key |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

---

### `mock_gitlab_mrs`

Mock GitLab merge requests for development/testing.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `mr_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `iid` | INTEGER | NOT NULL | Merge request IID |
| `title` | TEXT | NOT NULL | MR title |
| `author_username` | TEXT | NOT NULL | Author's GitLab username |
| `project_path` | TEXT | | GitLab project path |
| `state` | TEXT | DEFAULT `opened` | `opened`, `merged`, `closed` |
| `reviewers` | TEXT | | JSON array of reviewer usernames |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `merged_at` | DATETIME | | Merge timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

---

## Daily Planning Tables

### `day_plan_items`

Time-blocked daily plan items.

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `item_id` | TEXT | PRIMARY KEY | UUID, auto-generated |
| `plan_date` | DATE | NOT NULL | Date of plan |
| `time_start` | TEXT | NOT NULL | Start time (HH:MM) |
| `time_end` | TEXT | NOT NULL | End time (HH:MM) |
| `title` | TEXT | NOT NULL | Item title |
| `item_type` | TEXT | DEFAULT `task` | `meeting`, `task`, `break`, `focus` |
| `task_id` | TEXT | FK → tasks | Associated task |
| `notes` | TEXT | | Item notes |
| `completed` | BOOLEAN | DEFAULT FALSE | Completion status |
| `source` | TEXT | DEFAULT `manual` | `manual`, `auto`, `calendar` |
| `priority` | TEXT | DEFAULT `medium` | Item priority |
| `calendar_uid` | TEXT | | Calendar event UID |
| `created_at` | DATETIME | DEFAULT NOW | Creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW | Last update timestamp |

**Foreign Keys:**
- `task_id` → `tasks.task_id` (ON DELETE SET NULL)

---

## Data Types Reference

| SQLAlchemy Type | SQL Type | Python Type | Example |
|-----------------|----------|------------|---------|
| `String(255)` | TEXT | str | `"Project Name"` |
| `Text` | TEXT | str | Long descriptions |
| `Integer` | INTEGER | int | `42` |
| `Date` | DATE | date | `2026-05-14` |
| `DateTime` | DATETIME | datetime | `2026-05-14T10:30:00` |
| `Boolean` | BOOLEAN | bool | `True`/`False` |

---

## Common Queries

### Get all overdue tasks

```sql
SELECT * FROM tasks 
WHERE due_date < date('now') 
AND status != 'done';
```

### Get tasks by project with completion rate

```sql
SELECT p.name, COUNT(t.task_id) as total, 
  SUM(CASE WHEN t.status = 'done' THEN 1 ELSE 0 END) as completed,
  ROUND(100.0 * SUM(CASE WHEN t.status = 'done' THEN 1 ELSE 0 END) / COUNT(t.task_id), 2) as completion_rate
FROM projects p
LEFT JOIN tasks t ON p.project_id = t.project_id
GROUP BY p.project_id;
```

### Get team member workload

```sql
SELECT tm.name, COUNT(t.task_id) as assigned_tasks,
  SUM(CASE WHEN t.status = 'in_progress' THEN 1 ELSE 0 END) as in_progress
FROM team_members tm
LEFT JOIN tasks t ON tm.member_id = t.assignee_id
GROUP BY tm.member_id;
```

### Get resource allocation by project and date

```sql
SELECT p.name, tm.name, ra.allocation_pct, ra.start_date, ra.end_date
FROM resource_allocations ra
JOIN projects p ON ra.project_id = p.project_id
JOIN team_members tm ON ra.member_id = tm.member_id
WHERE ra.start_date <= date('now') 
AND ra.end_date >= date('now')
ORDER BY p.name, tm.name;
```

---

## Maintenance & Performance

### Index Strategy

Indexes are automatically created on:
- Primary keys (all tables)
- Foreign keys (relationships)
- Frequently queried fields (status, priority, project_id, etc.)

### Recommended Indexes (optional)

```sql
-- For activity log queries
CREATE INDEX idx_activity_logs_endpoint ON activity_logs(endpoint);
CREATE INDEX idx_activity_logs_created ON activity_logs(created_at);

-- For task queries
CREATE INDEX idx_tasks_due_date ON tasks(due_date);
CREATE INDEX idx_tasks_status_priority ON tasks(status, priority);

-- For project queries
CREATE INDEX idx_projects_status ON projects(status);
```

### Database Size Management

- **SQLite file location:** `~/.commanddesk/execos.db`
- **Expected size:** < 100 MB for typical usage (millions of records)
- **Backup strategy:** Copy `.db` file to backup location
- **Vacuum:** Run `VACUUM` periodically to reclaim space from deleted records

