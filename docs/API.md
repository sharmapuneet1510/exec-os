# ExecOS API Documentation

Complete API reference for ExecOS backend endpoints.

**Base URL:** `http://localhost:8080`  
**API Prefix:** `/api`  
**Documentation:** http://localhost:8080/docs (Swagger UI)

---

## Table of Contents

1. [Health & Status](#health--status)
2. [Tasks](#tasks)
3. [Projects](#projects)
4. [Milestones](#milestones)
5. [Releases](#releases)
6. [Commitments](#commitments)
7. [Alerts](#alerts)
8. [Dashboard](#dashboard)
9. [Team Management](#team-management)
10. [Applications](#applications)
11. [Jira Integration](#jira-integration)
12. [GitLab Integration](#gitlab-integration)
13. [Admin Settings](#admin-settings)
14. [Estimations](#estimations)
15. [Activity Logs](#activity-logs)

---

## Health & Status

### Check API Health
```
GET /health
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "timestamp": "2026-05-14T10:30:00Z"
}
```

---

## Tasks

### List Tasks
```
GET /api/tasks
```

**Query Parameters:**
- `status` (optional): Comma-separated values: `todo`, `in_progress`, `done`, `cancelled`
- `priority` (optional): Comma-separated values: `low`, `medium`, `high`, `critical`
- `project_id` (optional): Filter by project UUID
- `assignee_id` (optional): Filter by team member UUID
- `search` (optional): Full-text search in title and description
- `sort_by` (optional): `due_date`, `priority`, `created_at` (default: `due_date`)
- `order` (optional): `asc` or `desc` (default: `asc`)
- `limit` (optional): Number of results (default: 100, max: 1000)
- `offset` (optional): Pagination offset (default: 0)

**Response (200 OK):**
```json
{
  "tasks": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Implement user authentication",
      "description": "Add JWT-based auth",
      "due_date": "2026-05-20",
      "priority": "high",
      "status": "in_progress",
      "project_id": "550e8400-e29b-41d4-a716-446655440001",
      "assignee_id": "550e8400-e29b-41d4-a716-446655440002",
      "tags": ["backend", "security"],
      "created_at": "2026-05-01T08:00:00Z",
      "updated_at": "2026-05-14T10:30:00Z",
      "completed_at": null
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

### Create Task
```
POST /api/tasks
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "Implement user authentication",
  "description": "Add JWT-based auth to API",
  "due_date": "2026-05-20",
  "priority": "high",
  "status": "todo",
  "project_id": "550e8400-e29b-41d4-a716-446655440001",
  "assignee_id": "550e8400-e29b-41d4-a716-446655440002",
  "tags": ["backend", "security"]
}
```

**Response (201 Created):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Implement user authentication",
  "description": "Add JWT-based auth to API",
  "due_date": "2026-05-20",
  "priority": "high",
  "status": "todo",
  "project_id": "550e8400-e29b-41d4-a716-446655440001",
  "assignee_id": "550e8400-e29b-41d4-a716-446655440002",
  "tags": ["backend", "security"],
  "created_at": "2026-05-14T10:30:00Z",
  "updated_at": "2026-05-14T10:30:00Z",
  "completed_at": null
}
```

**Validation Rules:**
- `title`: Required, max 500 characters
- `due_date`: Optional, ISO 8601 format (YYYY-MM-DD)
- `priority`: One of `low`, `medium`, `high`, `critical`
- `status`: One of `todo`, `in_progress`, `done`, `cancelled`
- `project_id`: Optional, must reference existing project
- `assignee_id`: Optional, must reference existing team member
- `tags`: Optional array of strings

### Get Task
```
GET /api/tasks/{task_id}
```

**Response (200 OK):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Implement user authentication",
  "description": "Add JWT-based auth to API",
  "due_date": "2026-05-20",
  "priority": "high",
  "status": "in_progress",
  "project_id": "550e8400-e29b-41d4-a716-446655440001",
  "assignee_id": "550e8400-e29b-41d4-a716-446655440002",
  "tags": ["backend", "security"],
  "created_at": "2026-05-01T08:00:00Z",
  "updated_at": "2026-05-14T10:30:00Z",
  "completed_at": null
}
```

### Update Task
```
PATCH /api/tasks/{task_id}
Content-Type: application/json
```

**Request Body (all fields optional):**
```json
{
  "title": "Implement user authentication",
  "description": "Add JWT-based auth with refresh tokens",
  "due_date": "2026-05-21",
  "priority": "critical",
  "status": "in_progress",
  "assignee_id": "550e8400-e29b-41d4-a716-446655440003",
  "tags": ["backend", "security", "api"]
}
```

**Response (200 OK):** Updated task object

### Delete Task
```
DELETE /api/tasks/{task_id}
```

**Response (204 No Content)**

---

## Projects

### List Projects
```
GET /api/projects
```

**Query Parameters:**
- `status` (optional): `active`, `on_hold`, `completed`, `archived`
- `owner` (optional): Filter by owner name
- `search` (optional): Full-text search
- `include_health` (optional): Boolean to include health score calculation
- `limit` (optional): Pagination limit (default: 100)
- `offset` (optional): Pagination offset

**Response (200 OK):**
```json
{
  "projects": [
    {
      "project_id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "Mobile App Redesign",
      "description": "Complete redesign of mobile application",
      "status": "active",
      "owner": "John Doe",
      "start_date": "2026-05-01",
      "due_date": "2026-08-31",
      "tags": ["mobile", "ui/ux"],
      "created_at": "2026-05-01T08:00:00Z",
      "updated_at": "2026-05-14T10:30:00Z",
      "health": {
        "total_tasks": 24,
        "completed_tasks": 8,
        "health_pct": 33.33,
        "overdue_tasks": 2
      }
    }
  ],
  "total": 15,
  "page": 1
}
```

### Create Project
```
POST /api/projects
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "Mobile App Redesign",
  "description": "Complete redesign of mobile application",
  "status": "active",
  "owner": "John Doe",
  "start_date": "2026-05-01",
  "due_date": "2026-08-31",
  "tags": ["mobile", "ui/ux"]
}
```

**Response (201 Created):** Project object

### Get Project
```
GET /api/projects/{project_id}
```

**Response (200 OK):** Project object with optional health metrics

### Update Project
```
PATCH /api/projects/{project_id}
Content-Type: application/json
```

**Response (200 OK):** Updated project object

### Delete Project
```
DELETE /api/projects/{project_id}
```

**Response (204 No Content)**

### Get Project Health
```
GET /api/projects/{project_id}/health
```

**Response (200 OK):**
```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "Mobile App Redesign",
  "total_tasks": 24,
  "completed_tasks": 8,
  "in_progress_tasks": 6,
  "overdue_tasks": 2,
  "health_pct": 33.33,
  "at_risk": false,
  "risk_reason": null
}
```

---

## Milestones

### List Milestones
```
GET /api/milestones
```

**Query Parameters:**
- `project_id` (optional): Filter by project
- `release_id` (optional): Filter by release
- `status` (optional): `pending`, `in_progress`, `completed`, `at_risk`

**Response (200 OK):**
```json
{
  "milestones": [
    {
      "milestone_id": "550e8400-e29b-41d4-a716-446655440010",
      "title": "API Implementation Complete",
      "description": "All API endpoints implemented and tested",
      "project_id": "550e8400-e29b-41d4-a716-446655440001",
      "release_id": "550e8400-e29b-41d4-a716-446655440020",
      "due_date": "2026-06-15",
      "status": "in_progress",
      "days_remaining": 32,
      "is_overdue": false,
      "created_at": "2026-05-01T08:00:00Z",
      "updated_at": "2026-05-14T10:30:00Z"
    }
  ],
  "total": 8
}
```

### Create Milestone
```
POST /api/milestones
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "API Implementation Complete",
  "description": "All API endpoints implemented and tested",
  "project_id": "550e8400-e29b-41d4-a716-446655440001",
  "release_id": "550e8400-e29b-41d4-a716-446655440020",
  "due_date": "2026-06-15",
  "status": "pending"
}
```

**Response (201 Created):** Milestone object

### Update Milestone
```
PATCH /api/milestones/{milestone_id}
Content-Type: application/json
```

**Request Body (optional fields):**
```json
{
  "status": "in_progress",
  "due_date": "2026-06-20"
}
```

**Response (200 OK):** Updated milestone

### Delete Milestone
```
DELETE /api/milestones/{milestone_id}
```

**Response (204 No Content)**

---

## Releases

### List Releases
```
GET /api/releases
```

**Query Parameters:**
- `project_id` (optional): Filter by project
- `application_id` (optional): Filter by application
- `status` (optional): `planned`, `in_progress`, `released`, `rollback`

**Response (200 OK):**
```json
{
  "releases": [
    {
      "release_id": "550e8400-e29b-41d4-a716-446655440020",
      "name": "Q2 2026 Release",
      "version": "2.1.0",
      "project_id": "550e8400-e29b-41d4-a716-446655440001",
      "application_id": "550e8400-e29b-41d4-a716-446655440005",
      "due_date": "2026-06-30",
      "start_date": "2026-05-01",
      "uat_date": "2026-06-20",
      "sign_off_date": "2026-06-25",
      "status": "in_progress",
      "milestone_count": 5,
      "created_at": "2026-05-01T08:00:00Z",
      "updated_at": "2026-05-14T10:30:00Z"
    }
  ],
  "total": 12
}
```

### Create Release
```
POST /api/releases
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "Q2 2026 Release",
  "version": "2.1.0",
  "project_id": "550e8400-e29b-41d4-a716-446655440001",
  "application_id": "550e8400-e29b-41d4-a716-446655440005",
  "due_date": "2026-06-30",
  "start_date": "2026-05-01",
  "uat_date": "2026-06-20",
  "sign_off_date": "2026-06-25",
  "status": "planned"
}
```

**Response (201 Created):** Release object

### Update Release
```
PATCH /api/releases/{release_id}
Content-Type: application/json
```

**Response (200 OK):** Updated release

### Delete Release
```
DELETE /api/releases/{release_id}
```

**Response (204 No Content)**

---

## Commitments

### List Commitments
```
GET /api/commitments
```

**Query Parameters:**
- `status` (optional): `pending`, `fulfilled`, `missed`
- `project_id` (optional): Filter by project

**Response (200 OK):**
```json
{
  "commitments": [
    {
      "commitment_id": "550e8400-e29b-41d4-a716-446655440030",
      "title": "Deliver Phase 1 by end of May",
      "description": "Complete all Phase 1 requirements",
      "due_date": "2026-05-31",
      "status": "pending",
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "project_id": "550e8400-e29b-41d4-a716-446655440001",
      "days_remaining": 17,
      "created_at": "2026-05-01T08:00:00Z"
    }
  ],
  "total": 8
}
```

### Create Commitment
```
POST /api/commitments
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "Deliver Phase 1 by end of May",
  "description": "Complete all Phase 1 requirements",
  "due_date": "2026-05-31",
  "status": "pending",
  "project_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

**Response (201 Created):** Commitment object

### Update Commitment
```
PATCH /api/commitments/{commitment_id}
Content-Type: application/json
```

**Request Body:**
```json
{
  "status": "fulfilled"
}
```

**Response (200 OK):** Updated commitment

### Delete Commitment
```
DELETE /api/commitments/{commitment_id}
```

**Response (204 No Content)**

---

## Alerts

### List Alerts
```
GET /api/alerts
```

**Query Parameters:**
- `unread_only` (optional): Boolean (default: false)
- `severity` (optional): `info`, `warning`, `critical`
- `source` (optional): `system`, `user`, `integration`
- `limit` (optional): Pagination limit

**Response (200 OK):**
```json
{
  "alerts": [
    {
      "alert_id": "550e8400-e29b-41d4-a716-446655440040",
      "title": "Task overdue: API Implementation",
      "message": "Task 'Implement user auth' is 2 days overdue",
      "severity": "warning",
      "source": "system",
      "is_read": false,
      "is_snoozed": false,
      "created_at": "2026-05-14T10:30:00Z"
    }
  ],
  "total": 5
}
```

### Create Alert
```
POST /api/alerts
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "Critical: Database backup failed",
  "message": "Daily backup job failed at 03:00 UTC",
  "severity": "critical",
  "source": "system"
}
```

**Response (201 Created):** Alert object

### Mark Alert as Read
```
PATCH /api/alerts/{alert_id}/read
Content-Type: application/json
```

**Request Body:**
```json
{
  "is_read": true
}
```

**Response (200 OK):** Updated alert

### Snooze Alert
```
POST /api/alerts/{alert_id}/snooze
Content-Type: application/json
```

**Request Body:**
```json
{
  "snooze_until": "2026-05-15T10:30:00Z"
}
```

**Response (200 OK):** Updated alert with snooze time

### Delete Alert
```
DELETE /api/alerts/{alert_id}
```

**Response (204 No Content)**

---

## Dashboard

### Operational Dashboard
```
GET /api/dashboard/operational
```

**Query Parameters:**
- `use_cache` (optional): Boolean (default: true, uses 60-second cache)

**Response (200 OK):**
```json
{
  "timestamp": "2026-05-14T10:30:00Z",
  "metrics": {
    "total_tasks": 84,
    "completed_today": 6,
    "in_progress": 18,
    "overdue": 4,
    "due_this_week": 12,
    "overdue_by_priority": {
      "critical": 2,
      "high": 2,
      "medium": 0,
      "low": 0
    }
  },
  "overdue_tasks": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Fix authentication bug",
      "project": "Security",
      "due_date": "2026-05-10",
      "days_overdue": 4,
      "priority": "critical"
    }
  ],
  "in_progress_tasks": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440001",
      "title": "Implement API v2",
      "project": "Backend",
      "due_date": "2026-05-20",
      "days_remaining": 6,
      "priority": "high"
    }
  ],
  "due_this_week": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440002",
      "title": "Code review",
      "project": "QA",
      "due_date": "2026-05-16",
      "days_remaining": 2,
      "priority": "medium"
    }
  ]
}
```

### Executive Dashboard
```
GET /api/dashboard/executive
```

**Response (200 OK):**
```json
{
  "timestamp": "2026-05-14T10:30:00Z",
  "portfolio_health": {
    "total_projects": 15,
    "completed_projects": 3,
    "active_projects": 10,
    "on_hold_projects": 2,
    "portfolio_health_pct": 20.0
  },
  "commitment_risk": {
    "total_commitments": 25,
    "fulfilled_commitments": 18,
    "pending_commitments": 5,
    "missed_commitments": 2,
    "fulfillment_rate": 72.0,
    "missed_rate": 8.0
  },
  "at_risk_projects": [
    {
      "project_id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "Mobile App Redesign",
      "overdue_count": 5,
      "total_tasks": 24,
      "overdue_pct": 20.8
    }
  ],
  "top_blockers": [
    {
      "title": "Waiting for legal approval",
      "project": "Compliance Update",
      "blocked_task_count": 3
    }
  ]
}
```

### Start of Day (SOD) Summary
```
GET /api/dashboard/sod
```

**Response (200 OK):**
```json
{
  "date": "2026-05-14",
  "overdue_tasks": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Fix critical bug",
      "priority": "critical",
      "days_overdue": 4
    }
  ],
  "due_today_tasks": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440001",
      "title": "Code review",
      "priority": "high"
    }
  ],
  "carry_forward_tasks": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440002",
      "title": "API implementation",
      "priority": "high",
      "days_in_progress": 5
    }
  ]
}
```

### End of Day (EOD) Summary
```
GET /api/dashboard/eod
```

**Response (200 OK):**
```json
{
  "date": "2026-05-14",
  "completed_tasks": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Code review",
      "priority": "medium",
      "completed_at": "2026-05-14T17:30:00Z"
    }
  ],
  "pending_tasks": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440001",
      "title": "API implementation",
      "priority": "high",
      "status": "in_progress"
    }
  ]
}
```

---

## Team Management

### List Team Members
```
GET /api/team-members
```

**Query Parameters:**
- `include_stats` (optional): Boolean to include task statistics
- `active_only` (optional): Boolean (default: false)

**Response (200 OK):**
```json
{
  "team_members": [
    {
      "member_id": "550e8400-e29b-41d4-a716-446655440002",
      "name": "Alice Johnson",
      "email": "alice@company.com",
      "role": "Senior Developer",
      "is_active": true,
      "max_concurrent_tasks": 8,
      "current_task_count": 6,
      "capacity_pct": 75.0,
      "created_at": "2026-01-01T08:00:00Z"
    }
  ],
  "total": 12
}
```

### Create Team Member
```
POST /api/team-members
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "Alice Johnson",
  "email": "alice@company.com",
  "role": "Senior Developer",
  "is_active": true,
  "max_concurrent_tasks": 8
}
```

**Response (201 Created):** Team member object

### Update Team Member
```
PATCH /api/team-members/{member_id}
Content-Type: application/json
```

**Response (200 OK):** Updated team member

### Delete Team Member
```
DELETE /api/team-members/{member_id}
```

**Response (204 No Content)**

### Get Team Workload
```
GET /api/team-members/workload
```

**Response (200 OK):**
```json
{
  "workload": [
    {
      "member_id": "550e8400-e29b-41d4-a716-446655440002",
      "name": "Alice Johnson",
      "max_concurrent_tasks": 8,
      "current_tasks": 6,
      "capacity_pct": 75.0,
      "avg_priority": "high",
      "risk_level": "normal"
    }
  ]
}
```

---

## Applications

### List Applications
```
GET /api/applications
```

**Query Parameters:**
- `status` (optional): `active`, `on_hold`, `archived`

**Response (200 OK):**
```json
{
  "applications": [
    {
      "application_id": "550e8400-e29b-41d4-a716-446655440005",
      "name": "Mobile App",
      "code": "MOBILE",
      "description": "Primary mobile application",
      "owner": "John Doe",
      "status": "active",
      "jira_enabled": true,
      "gitlab_enabled": true,
      "created_at": "2026-01-01T08:00:00Z"
    }
  ],
  "total": 8
}
```

### Create Application
```
POST /api/applications
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "Mobile App",
  "code": "MOBILE",
  "description": "Primary mobile application",
  "owner": "John Doe",
  "status": "active"
}
```

**Response (201 Created):** Application object

### Update Application
```
PATCH /api/applications/{application_id}
Content-Type: application/json
```

**Response (200 OK):** Updated application

---

## Jira Integration

### Configure Jira
```
PATCH /api/admin/config/jira
Content-Type: application/json
```

**Request Body:**
```json
{
  "base_url": "https://company.atlassian.net",
  "pat": "ATATT...",
  "project_keys": ["PROJ1", "PROJ2"],
  "enabled": true
}
```

**Response (200 OK):** Configuration saved

### Sync Jira
```
POST /api/admin/sync-jira
```

**Response (200 OK):**
```json
{
  "status": "success",
  "synced_at": "2026-05-14T10:30:00Z",
  "issues_synced": 42
}
```

### List Sprint Board Issues
```
GET /api/jira/sprints/{sprint_id}/issues
```

**Response (200 OK):**
```json
{
  "sprint_id": "1",
  "issues": [
    {
      "key": "PROJ-123",
      "summary": "Implement authentication",
      "status": "In Progress",
      "assignee": "alice@company.com",
      "priority": "High"
    }
  ]
}
```

### Update Issue Status
```
PATCH /api/jira/issues/{issue_key}/status
Content-Type: application/json
```

**Request Body:**
```json
{
  "status": "Done"
}
```

**Response (200 OK):** Issue updated

---

## GitLab Integration

### Configure GitLab
```
PATCH /api/admin/config/gitlab
Content-Type: application/json
```

**Request Body:**
```json
{
  "base_url": "https://gitlab.com",
  "access_token": "glpat-...",
  "project_ids": ["123", "456"],
  "enabled": true
}
```

**Response (200 OK):** Configuration saved

### Sync GitLab
```
POST /api/admin/sync-gitlab
```

**Response (200 OK):**
```json
{
  "status": "success",
  "synced_at": "2026-05-14T10:30:00Z",
  "mrs_synced": 18
}
```

### List Merge Requests
```
GET /api/gitlab/merge-requests
```

**Response (200 OK):**
```json
{
  "merge_requests": [
    {
      "iid": 42,
      "title": "Add user authentication",
      "state": "opened",
      "author": "alice",
      "project_path": "company/mobile-app",
      "reviewers": ["bob", "charlie"]
    }
  ]
}
```

---

## Admin Settings

### Get Email Configuration
```
GET /api/admin/config/email
```

**Response (200 OK):**
```json
{
  "recipient_email": "team@company.com",
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_mode": "starttls",
  "sod_enabled": true,
  "sod_time": "08:00",
  "eod_enabled": true,
  "eod_time": "18:00",
  "reminder_priority_filter": "all"
}
```

### Update Email Configuration
```
PATCH /api/admin/config/email
Content-Type: application/json
```

**Request Body:**
```json
{
  "recipient_email": "team@company.com",
  "sod_time": "08:00",
  "eod_time": "18:00",
  "sod_enabled": true,
  "eod_enabled": true
}
```

**Response (200 OK):** Updated configuration

### Send Test Email
```
POST /api/admin/send-test-email
```

**Response (200 OK):**
```json
{
  "status": "sent",
  "recipient": "team@company.com"
}
```

---

## Estimations

### List Estimations
```
GET /api/estimations
```

**Query Parameters:**
- `project_id` (optional): Filter by project

**Response (200 OK):**
```json
{
  "estimations": [
    {
      "estimation_id": "550e8400-e29b-41d4-a716-446655440050",
      "title": "API Module Development",
      "story_points": 13,
      "complexity": "high",
      "testing_effort": "moderate",
      "velocity": 2,
      "dev_days": 7,
      "testing_days": 3,
      "paperwork_days": 1,
      "total_working_days": 11,
      "estimated_end_date": "2026-05-30"
    }
  ],
  "total": 5
}
```

### Create Estimation
```
POST /api/estimations
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "API Module Development",
  "project_id": "550e8400-e29b-41d4-a716-446655440001",
  "story_points": 13,
  "complexity": "high",
  "testing_effort": "moderate",
  "has_release_paperwork": true,
  "velocity": 2,
  "start_date": "2026-05-19"
}
```

**Response (201 Created):** Estimation with calculated fields

---

## Activity Logs

### List Activity Logs
```
GET /api/activity-logs
```

**Query Parameters:**
- `entity_type` (optional): `task`, `project`, `release`, etc.
- `action` (optional): `created`, `updated`, `deleted`
- `date_from` (optional): ISO 8601 date
- `date_to` (optional): ISO 8601 date
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 50)

**Response (200 OK):**
```json
{
  "logs": [
    {
      "activity_id": "550e8400-e29b-41d4-a716-446655440060",
      "entity_type": "task",
      "entity_id": "550e8400-e29b-41d4-a716-446655440000",
      "action": "updated",
      "description": "Status changed from 'todo' to 'in_progress'",
      "details": {
        "status": "in_progress",
        "previous_status": "todo"
      },
      "created_at": "2026-05-14T10:30:00Z"
    }
  ],
  "total": 284,
  "page": 1,
  "page_size": 50
}
```

### Export Activity Logs
```
GET /api/activity-logs/export
```

**Query Parameters:**
- `format` (optional): `csv` (default) or `json`
- `date_from`, `date_to`, `entity_type`, `action`: Same as listing

**Response (200 OK):** CSV or JSON file download

---

## Error Handling

All endpoints follow standard HTTP status codes:

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **204 No Content**: Request successful, no response body
- **400 Bad Request**: Invalid request parameters
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Access denied
- **404 Not Found**: Resource not found
- **409 Conflict**: Conflict (e.g., duplicate key)
- **500 Internal Server Error**: Server error

### Error Response Format
```json
{
  "error": "Bad Request",
  "message": "Invalid priority value. Must be one of: low, medium, high, critical",
  "status_code": 400
}
```

---

## Pagination

List endpoints support pagination:

**Query Parameters:**
- `limit`: Number of items per page (default: 20, max: 100)
- `offset`: Number of items to skip (default: 0)

**Response includes:**
```json
{
  "items": [...],
  "total": 284,
  "page": 1,
  "page_size": 20,
  "total_pages": 15
}
```

---

## Caching

Dashboard endpoints use in-memory caching with 60-second TTL:

- `GET /api/dashboard/operational` - Cached
- `GET /api/dashboard/executive` - Cached
- `GET /api/dashboard/sod` - Not cached (live)
- `GET /api/dashboard/eod` - Not cached (live)

To bypass cache, use query parameter: `?use_cache=false`

---

## Rate Limiting

No rate limiting currently implemented. For production, implement:

- 100 requests per minute per IP
- 500 requests per minute per authenticated user
- Response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

---

## Authentication (Future)

Currently, the API has no authentication. For production deployment, implement:

- Bearer token authentication
- JWT tokens with expiration
- Scope-based access control
- API key management

---

## Interactive Documentation

Full interactive API documentation available at: `http://localhost:8080/docs`

Uses OpenAPI 3.0 / Swagger UI for exploring endpoints and testing requests.
