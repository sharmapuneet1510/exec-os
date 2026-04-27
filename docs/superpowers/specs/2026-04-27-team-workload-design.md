---
name: Team Workload Feature Design
description: Add team member model, task assignment, and unified workload dashboard showing local tasks, Jira issues, and GitLab MRs
type: feature
date: 2026-04-27
---

# Team Workload Feature Design

## Overview

Add comprehensive team workload tracking to ExecOS. Team members can be created with capacity thresholds, tasks can be assigned to them, and a unified dashboard shows their workload across three sources: local tasks, Jira issues, and GitLab MRs.

**Scope:** 5 team members, capacity-based warnings (>8 tasks = overloaded), offline-ready with mock data fallback.

---

## 1. Data Model

### New Table: `TeamMemberORM`

```python
class TeamMemberORM(Base):
    __tablename__ = "team_members"
    
    member_id = Column(String, primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)           # display name
    email = Column(String(255), nullable=True)           # for Jira correlation
    gitlab_username = Column(String(255), nullable=True) # for GitLab correlation
    role = Column(String(100), nullable=True)            # e.g., "Backend", "Frontend", "QA"
    max_concurrent_tasks = Column(Integer, default=8)    # workload threshold
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Modified Table: `TaskORM`

Add one column to existing `TaskORM`:
```python
assignee_id = Column(String, ForeignKey("team_members.member_id", ondelete="SET NULL"), nullable=True)
```

- Allows tasks to be assigned to team members
- Nullable so unassigned tasks still work
- Cascade behavior: SET NULL if team member deleted

### New Mock Tables

**`MockJiraIssueORM`** — simulates Jira data offline
```python
class MockJiraIssueORM(Base):
    __tablename__ = "mock_jira_issues"
    
    issue_id = Column(String, primary_key=True, default=_uuid)
    key = Column(String(50), nullable=False, unique=True)          # e.g., "ENG-123"
    summary = Column(String(500), nullable=False)
    assignee_email = Column(String(255), nullable=True)
    status = Column(String(50), default="To Do")                  # "To Do", "In Progress", "In Review", "Done"
    priority = Column(String(50), default="Medium")               # "Highest", "High", "Medium", "Low"
    project_key = Column(String(50), default="")                 # e.g., "ENG"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**`MockGitLabMRORM`** — simulates GitLab MR data offline
```python
class MockGitLabMRORM(Base):
    __tablename__ = "mock_gitlab_mrs"
    
    mr_id = Column(String, primary_key=True, default=_uuid)
    iid = Column(Integer, nullable=False)                    # MR number within project
    title = Column(String(500), nullable=False)
    author_username = Column(String(255), nullable=False)
    project_path = Column(String(255), default="")          # e.g., "team/project"
    state = Column(String(50), default="opened")            # "opened", "merged", "closed"
    reviewers = Column(Text, default="[]")                  # JSON list of usernames
    created_at = Column(DateTime, default=datetime.utcnow)
    merged_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## 2. Workload Aggregation Logic

### Endpoint: `GET /api/workload/team?app_id=<application_id>`

Returns consolidated workload per team member.

**Data Sources (in priority order):**

1. **Local Tasks** — from `TaskORM` where `assignee_id = team_member.member_id`
2. **Jira Issues** — from real Jira API if configured, else from `MockJiraIssueORM`
3. **GitLab MRs** — from real GitLab API if configured, else from `MockGitLabMRORM`

**Matching Logic:**

- **Local:** Direct FK relationship via `assignee_id`
- **Jira:** Match by `team_member.email` against Jira issue `assignee.emailAddress`
- **GitLab:** Match by `team_member.gitlab_username` against MR `author.username` or in `reviewers` list

**Response Structure:**

```json
{
  "team": [
    {
      "member_id": "...",
      "name": "Alice Chen",
      "email": "alice.chen@company.com",
      "gitlab_username": "achen",
      "role": "Backend",
      "max_concurrent_tasks": 8,
      "workload": {
        "local_tasks": [
          {
            "task_id": "...",
            "title": "API refactor",
            "status": "in_progress",
            "priority": "high",
            "due_date": "2026-05-01"
          }
        ],
        "local_count": 2,
        "jira_issues": [
          {
            "key": "ENG-123",
            "summary": "Fix auth bug",
            "status": "In Progress",
            "priority": "High",
            "due_date": null
          }
        ],
        "jira_count": 3,
        "gitlab_mrs": [
          {
            "iid": 45,
            "title": "Add caching layer",
            "state": "opened",
            "created_at": "2026-04-20T10:00:00Z"
          }
        ],
        "mr_count": 1,
        "total_active": 6,
        "capacity_status": "moderate"
      }
    }
  ],
  "summary": {
    "total_members": 5,
    "overloaded_count": 1,
    "total_local_tasks": 12,
    "total_jira_issues": 8,
    "total_mrs": 5,
    "last_updated": "2026-04-27T14:30:00Z"
  }
}
```

**Capacity Status Calculation:**

- `total_active` = `local_count + jira_count + mr_count`
- Status: "light" (<4), "moderate" (4-7), "heavy" (≥8)
- Team member is "overloaded" if `total_active >= max_concurrent_tasks`

**Caching:**

- Local tasks: real-time (no cache)
- Jira + GitLab + mock data: 60s TTL in-memory cache
- Manual refresh available via `POST /api/workload/team/refresh`

---

## 3. Web UI: Team Workload Dashboard

### Location

New top-level nav item: "Team" (between "Projects" and "Admin" in sidebar)

### Layout

**Header:**
- Title: "Team Workload"
- Application selector dropdown (required, like Jira team view)
- Refresh button (shows loading state)
- Last updated timestamp

**Summary Cards:**
- Total Team Members
- Overloaded Count (members with workload ≥ threshold)
- Total Active Items (local + Jira + MRs)
- High Priority / Critical items

**Team Member Cards (Grid):**
- Responsive grid (1-5 columns depending on screen size)
- Each card shows:
  - Member avatar (initials if no avatar)
  - Name and role
  - Workload breakdown: "X tasks | Y issues | Z MRs"
  - Total active with color pill: 🟢 Light | 🟡 Moderate | 🔴 Heavy
  - Quick stats: high-priority count, overdue count
  - Expandable section showing all items grouped by source

**Search/Filter:**
- Filter by member name
- Filter by role (Backend, Frontend, etc.)
- Filter by capacity status

### Error Handling

- If Jira not configured: show "Jira data unavailable" but load mock data
- If GitLab not configured: show "GitLab data unavailable" but load mock data
- If both unavailable: show only local tasks (graceful degradation)
- Connection errors: show toast alert, retry button

---

## 4. Seed Data

### 5 Team Members

Created in `seed_data.py`:

```python
alice = TeamMemberORM(
    name="Alice Chen",
    email="alice.chen@company.com",
    gitlab_username="achen",
    role="Backend",
    max_concurrent_tasks=8
)

bob = TeamMemberORM(
    name="Bob Johnson",
    email="bob.johnson@company.com",
    gitlab_username="bjohnson",
    role="Frontend",
    max_concurrent_tasks=8
)

carol = TeamMemberORM(
    name="Carol Martinez",
    email="carol@company.com",
    gitlab_username="cmartinez",
    role="QA",
    max_concurrent_tasks=8
)

david = TeamMemberORM(
    name="David Lee",
    email="david.lee@company.com",
    gitlab_username="dlee",
    role="DevOps",
    max_concurrent_tasks=8
)

eva = TeamMemberORM(
    name="Eva Patel",
    email="eva@company.com",
    gitlab_username="evapatel",
    role="Full Stack",
    max_concurrent_tasks=8
)
```

### Local Task Assignments

- 12-15 total tasks distributed across team
- Each member gets 2-4 tasks
- Mix of statuses: todo, in_progress, done
- Various priorities: low, medium, high, critical
- Due dates spread over next 2 weeks

### Mock Jira Issues

- 8-10 issues total
- 2-3 per team member (assigned by email)
- Project keys: ENG, QA, OPS
- Statuses: To Do, In Progress, In Review, Done
- Priorities: Highest, High, Medium, Low

Example:
```python
MockJiraIssueORM(
    key="ENG-101",
    summary="Optimize database queries",
    assignee_email="alice.chen@company.com",
    status="In Progress",
    priority="High",
    project_key="ENG"
)
```

### Mock GitLab MRs

- 5-7 MRs total
- 1-2 per team member (as author or reviewer)
- Project paths: team/api, team/web, team/infra
- States: opened, merged (some recent, some older)

Example:
```python
MockGitLabMRORM(
    iid=45,
    title="Add caching layer",
    author_username="achen",
    project_path="team/api",
    state="opened",
    reviewers='["bjohnson", "dlee"]'
)
```

---

## 5. API & Routing

### New Routes (in `workload_routes.py`)

```python
@router.get("/api/workload/team")
def get_team_workload(app_id: str = Query(...), db: Session = Depends(_db)):
    """Return team workload: aggregated local tasks, Jira issues, MRs"""
    # Returns structure from Section 2

@router.get("/api/workload/team/members")
def get_team_members(db: Session = Depends(_db)):
    """Return list of all team members"""

@router.post("/api/workload/team/members")
def create_team_member(body: dict, db: Session = Depends(_db)):
    """Create new team member"""

@router.patch("/api/workload/team/members/{member_id}")
def update_team_member(member_id: str, body: dict, db: Session = Depends(_db)):
    """Update team member (name, role, max_concurrent_tasks)"""

@router.delete("/api/workload/team/members/{member_id}")
def delete_team_member(member_id: str, db: Session = Depends(_db)):
    """Delete team member (tasks get unassigned)"""

@router.post("/api/workload/team/refresh")
def refresh_workload_cache():
    """Manually bust cache and reload Jira/GitLab data"""
```

---

## 6. Implementation Phases

**Phase 1: Data Model & Seed**
- Create TeamMemberORM table
- Create mock data tables
- Add assignee_id to TaskORM
- Seed 5 team members + local tasks + mock Jira + mock GitLab

**Phase 2: Workload Aggregation API**
- Implement `/api/workload/team` endpoint
- Matching logic (email for Jira, username for GitLab)
- Capacity calculation
- Caching

**Phase 3: Team Member CRUD API**
- Team member management endpoints
- Update task UI to show assignee field

**Phase 4: Web UI**
- Team workload dashboard view
- Search/filter
- Responsive layout

---

## 7. Success Criteria

- ✅ 5 team members created with realistic emails and roles
- ✅ 12-15 local tasks assigned to team members
- ✅ 8-10 mock Jira issues seeded by email
- ✅ 5-7 mock GitLab MRs seeded by username
- ✅ `/api/workload/team` returns aggregated data correctly
- ✅ Capacity status calculated (light/moderate/heavy)
- ✅ Team workload view loads and displays data
- ✅ Graceful fallback when Jira/GitLab not configured
- ✅ Filter and search work correctly

---

## 8. Testing Strategy

- Unit tests: workload aggregation logic, matching by email/username
- Integration tests: endpoint returns correct structure
- Manual: browse team workload view, verify data matches expectations
- Offline test: disable Jira/GitLab, verify mock data loads

---

## Notes

- No changes to existing tasks/projects/applications — fully additive
- Mock data enables offline demos and testing
- Seed script remains idempotent (can re-run safely)
- Capacity threshold is configurable per team member
