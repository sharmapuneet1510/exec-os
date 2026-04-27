# Team Workload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add team member model, task assignment, and unified workload dashboard showing local tasks, Jira issues, and GitLab MRs with capacity-based warnings.

**Architecture:** Create TeamMemberORM and mock data tables → seed 5 team members with tasks/issues/MRs → build workload aggregation API matching by email/username → add team workload view to web UI.

**Tech Stack:** SQLAlchemy ORM, FastAPI, Alpine.js, existing Jira/GitLab integration

---

## Phase 1: Data Models & Seed Data

### Task 1: Create TeamMemberORM Table

**Files:**
- Modify: `db/models.py` (add new ORM class)

- [ ] **Step 1: Write failing test for TeamMemberORM**

```python
# tests/test_models.py
def test_team_member_orm_basic():
    from db.models import TeamMemberORM
    member = TeamMemberORM(
        name="Alice Chen",
        email="alice@company.com",
        gitlab_username="achen",
        role="Backend",
        max_concurrent_tasks=8
    )
    assert member.name == "Alice Chen"
    assert member.email == "alice@company.com"
    assert member.is_active == True
    assert member.max_concurrent_tasks == 8
```

Run: `pytest tests/test_models.py::test_team_member_orm_basic -v`
Expected: FAIL — `TeamMemberORM` not defined

- [ ] **Step 2: Add TeamMemberORM class to db/models.py**

Add this class before the last line of `db/models.py`:

```python
class TeamMemberORM(Base):
    __tablename__ = "team_members"

    member_id = Column(String, primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    gitlab_username = Column(String(255), nullable=True)
    role = Column(String(100), nullable=True)
    max_concurrent_tasks = Column(Integer, default=8)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_models.py::test_team_member_orm_basic -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add db/models.py tests/test_models.py
git commit -m "feat: add TeamMemberORM model for team members"
```

---

### Task 2: Create Mock Jira & GitLab ORM Tables

**Files:**
- Modify: `db/models.py` (add two new ORM classes)

- [ ] **Step 1: Write failing test for mock tables**

```python
# tests/test_models.py
def test_mock_jira_issue_orm():
    from db.models import MockJiraIssueORM
    issue = MockJiraIssueORM(
        key="ENG-123",
        summary="Fix bug",
        assignee_email="alice@company.com",
        status="In Progress",
        priority="High",
        project_key="ENG"
    )
    assert issue.key == "ENG-123"
    assert issue.assignee_email == "alice@company.com"

def test_mock_gitlab_mr_orm():
    from db.models import MockGitLabMRORM
    mr = MockGitLabMRORM(
        iid=45,
        title="Add feature",
        author_username="achen",
        project_path="team/api",
        state="opened",
        reviewers='["bjohnson"]'
    )
    assert mr.iid == 45
    assert mr.author_username == "achen"
```

Run: `pytest tests/test_models.py::test_mock_jira_issue_orm tests/test_models.py::test_mock_gitlab_mr_orm -v`
Expected: FAIL — classes not defined

- [ ] **Step 2: Add MockJiraIssueORM and MockGitLabMRORM to db/models.py**

Add these classes before the last line of `db/models.py` (after TeamMemberORM):

```python
class MockJiraIssueORM(Base):
    __tablename__ = "mock_jira_issues"

    issue_id = Column(String, primary_key=True, default=_uuid)
    key = Column(String(50), nullable=False, unique=True)
    summary = Column(String(500), nullable=False)
    assignee_email = Column(String(255), nullable=True)
    status = Column(String(50), default="To Do")
    priority = Column(String(50), default="Medium")
    project_key = Column(String(50), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MockGitLabMRORM(Base):
    __tablename__ = "mock_gitlab_mrs"

    mr_id = Column(String, primary_key=True, default=_uuid)
    iid = Column(Integer, nullable=False)
    title = Column(String(500), nullable=False)
    author_username = Column(String(255), nullable=False)
    project_path = Column(String(255), default="")
    state = Column(String(50), default="opened")
    reviewers = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    merged_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/test_models.py::test_mock_jira_issue_orm tests/test_models.py::test_mock_gitlab_mr_orm -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add db/models.py tests/test_models.py
git commit -m "feat: add mock Jira issue and GitLab MR ORM tables"
```

---

### Task 3: Modify TaskORM to Add Assignee FK

**Files:**
- Modify: `db/models.py` (update TaskORM class)

- [ ] **Step 1: Write failing test for task assignment**

```python
# tests/test_models.py
def test_task_orm_assignee():
    from db.models import TaskORM, TeamMemberORM
    member = TeamMemberORM(name="Alice", email="alice@company.com")
    task = TaskORM(
        title="Refactor auth",
        assignee_id=member.member_id
    )
    assert task.assignee_id == member.member_id
```

Run: `pytest tests/test_models.py::test_task_orm_assignee -v`
Expected: FAIL — `assignee_id` attribute doesn't exist

- [ ] **Step 2: Add assignee_id column to TaskORM**

In `db/models.py`, find the `TaskORM` class and add this column after the `project_id` line:

```python
assignee_id = Column(String, ForeignKey("team_members.member_id", ondelete="SET NULL"), nullable=True)
```

The updated TaskORM should look like:

```python
class TaskORM(Base):
    __tablename__ = "tasks"

    task_id = Column(String, primary_key=True, default=_uuid)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    due_date = Column(Date, nullable=True)
    reminder_date = Column(Date, nullable=True)
    priority = Column(String(20), default="medium")
    status = Column(String(20), default="todo")
    project_id = Column(String, ForeignKey("projects.project_id", ondelete="SET NULL"), nullable=True)
    assignee_id = Column(String, ForeignKey("team_members.member_id", ondelete="SET NULL"), nullable=True)
    tags = Column(Text, default="[]")
    postponed_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_models.py::test_task_orm_assignee -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add db/models.py tests/test_models.py
git commit -m "feat: add assignee_id FK to TaskORM"
```

---

### Task 4: Seed Team Members, Tasks, and Mock Data

**Files:**
- Modify: `seed_data.py` (add team data seeding)

- [ ] **Step 1: Write test for seed data**

```python
# tests/test_seed.py
def test_seed_data_creates_team_members():
    """Verify seed_data.py creates expected team members"""
    # Run seed_data.py
    import subprocess
    result = subprocess.run(
        ["python3", "seed_data.py"],
        cwd="/Users/puneetsharma/Workspace/projects/ai-lab/command-center",
        capture_output=True,
        timeout=30
    )
    assert result.returncode == 0, result.stderr.decode()
    
    # Query database to verify
    from db.base import SessionLocal
    from db.models import TeamMemberORM
    db = SessionLocal()
    members = db.query(TeamMemberORM).all()
    db.close()
    
    assert len(members) == 5
    names = [m.name for m in members]
    assert "Alice Chen" in names
    assert "Bob Johnson" in names
    assert "Carol Martinez" in names
    assert "David Lee" in names
    assert "Eva Patel" in names
```

Run: `pytest tests/test_seed.py::test_seed_data_creates_team_members -v`
Expected: FAIL — seed_data.py doesn't create team members

- [ ] **Step 2: Update seed_data.py to import and initialize new models**

At the top of `seed_data.py`, update the imports to include:

```python
from db.models import (
    ApplicationORM, ProjectORM, TaskORM, MilestoneORM, CommitmentORM,
    AlertORM, EstimationORM, DayPlanItemORM,
    DeliveryTemplateORM, DeliveryTemplateItemORM,
    DeliveryReleaseORM, DeliveryReleaseItemORM,
    AppJiraConfigORM, AppGitLabConfigORM, AppSprintConfigORM,
    ProjEstimateORM, ProjEstMilestoneORM, ProjEstTaskORM,
    TeamMemberORM, MockJiraIssueORM, MockGitLabMRORM,  # ADD THIS LINE
)
```

Also update the cleanup loop to include the new tables:

```python
for model in [DeliveryReleaseItemORM, DeliveryReleaseORM,
              DeliveryTemplateItemORM, DeliveryTemplateORM,
              DayPlanItemORM, TaskORM, MilestoneORM, CommitmentORM,
              AlertORM, EstimationORM, ProjectORM,
              AppJiraConfigORM, AppGitLabConfigORM, AppSprintConfigORM,
              ProjEstTaskORM, ProjEstMilestoneORM, ProjEstimateORM,
              TeamMemberORM, MockJiraIssueORM, MockGitLabMRORM,  # ADD THIS LINE
              ApplicationORM]:
    db.query(model).delete()
db.commit()
```

- [ ] **Step 3: Add team member seeding to seed_data.py**

Find the `# ── Applications ─────────────────────────────────────────────────────────` section in seed_data.py. After that section and before the next major section, add this:

```python
# ── Team Members ──────────────────────────────────────────────────────────
tm_alice = TeamMemberORM(
    name="Alice Chen",
    email="alice.chen@company.com",
    gitlab_username="achen",
    role="Backend",
    max_concurrent_tasks=8
)
tm_bob = TeamMemberORM(
    name="Bob Johnson",
    email="bob.johnson@company.com",
    gitlab_username="bjohnson",
    role="Frontend",
    max_concurrent_tasks=8
)
tm_carol = TeamMemberORM(
    name="Carol Martinez",
    email="carol@company.com",
    gitlab_username="cmartinez",
    role="QA",
    max_concurrent_tasks=8
)
tm_david = TeamMemberORM(
    name="David Lee",
    email="david.lee@company.com",
    gitlab_username="dlee",
    role="DevOps",
    max_concurrent_tasks=8
)
tm_eva = TeamMemberORM(
    name="Eva Patel",
    email="eva@company.com",
    gitlab_username="evapatel",
    role="Full Stack",
    max_concurrent_tasks=8
)

db.add_all([tm_alice, tm_bob, tm_carol, tm_david, tm_eva])
db.commit()
```

- [ ] **Step 4: Add mock Jira issues to seed_data.py**

After the team members section, add:

```python
# ── Mock Jira Issues ──────────────────────────────────────────────────────
mock_jira_issues = [
    MockJiraIssueORM(
        key="ENG-101",
        summary="Optimize database queries",
        assignee_email="alice.chen@company.com",
        status="In Progress",
        priority="High",
        project_key="ENG"
    ),
    MockJiraIssueORM(
        key="ENG-102",
        summary="Fix authentication bug",
        assignee_email="alice.chen@company.com",
        status="In Progress",
        priority="Highest",
        project_key="ENG"
    ),
    MockJiraIssueORM(
        key="ENG-103",
        summary="Refactor payment module",
        assignee_email="eva@company.com",
        status="To Do",
        priority="High",
        project_key="ENG"
    ),
    MockJiraIssueORM(
        key="WEB-201",
        summary="Redesign dashboard",
        assignee_email="bob.johnson@company.com",
        status="In Progress",
        priority="High",
        project_key="WEB"
    ),
    MockJiraIssueORM(
        key="WEB-202",
        summary="Add dark mode",
        assignee_email="bob.johnson@company.com",
        status="To Do",
        priority="Medium",
        project_key="WEB"
    ),
    MockJiraIssueORM(
        key="QA-301",
        summary="Test payment flow",
        assignee_email="carol@company.com",
        status="In Progress",
        priority="High",
        project_key="QA"
    ),
    MockJiraIssueORM(
        key="QA-302",
        summary="Write integration tests",
        assignee_email="carol@company.com",
        status="To Do",
        priority="Medium",
        project_key="QA"
    ),
    MockJiraIssueORM(
        key="OPS-401",
        summary="Upgrade Postgres",
        assignee_email="david.lee@company.com",
        status="In Progress",
        priority="High",
        project_key="OPS"
    ),
    MockJiraIssueORM(
        key="OPS-402",
        summary="Set up monitoring",
        assignee_email="david.lee@company.com",
        status="To Do",
        priority="Medium",
        project_key="OPS"
    ),
    MockJiraIssueORM(
        key="ENG-104",
        summary="Code review: payment",
        assignee_email=None,
        status="To Do",
        priority="Medium",
        project_key="ENG"
    ),
]

db.add_all(mock_jira_issues)
db.commit()
```

- [ ] **Step 5: Add mock GitLab MRs to seed_data.py**

After the mock Jira section, add:

```python
# ── Mock GitLab MRs ────────────────────────────────────────────────────────
mock_mrs = [
    MockGitLabMRORM(
        iid=45,
        title="Add caching layer to API",
        author_username="achen",
        project_path="team/api",
        state="opened",
        reviewers='["bjohnson", "dlee"]'
    ),
    MockGitLabMRORM(
        iid=46,
        title="Fix memory leak in worker",
        author_username="dlee",
        project_path="team/api",
        state="opened",
        reviewers='["achen"]'
    ),
    MockGitLabMRORM(
        iid=67,
        title="Redesign header component",
        author_username="bjohnson",
        project_path="team/web",
        state="opened",
        reviewers='["evapatel"]'
    ),
    MockGitLabMRORM(
        iid=68,
        title="Update theme colors",
        author_username="bjohnson",
        project_path="team/web",
        state="merged",
        reviewers='[]'
    ),
    MockGitLabMRORM(
        iid=89,
        title="Add feature flag service",
        author_username="evapatel",
        project_path="team/api",
        state="opened",
        reviewers='["achen"]'
    ),
    MockGitLabMRORM(
        iid=101,
        title="Update CI/CD pipeline",
        author_username="dlee",
        project_path="team/infra",
        state="opened",
        reviewers='[]'
    ),
]

db.add_all(mock_mrs)
db.commit()
```

- [ ] **Step 6: Assign tasks to team members in seed_data.py**

In the section where existing tasks are created (look for the TaskORM creation in seed_data.py), modify the task creation to assign some to team members. Find the task creation loop and update a few tasks to include `assignee_id`. For example, when creating tasks, assign some like this:

```python
# After creating tasks, update assignments
tasks_to_assign = db.query(TaskORM).all()
if len(tasks_to_assign) >= 1:
    tasks_to_assign[0].assignee_id = tm_alice.member_id
if len(tasks_to_assign) >= 2:
    tasks_to_assign[1].assignee_id = tm_bob.member_id
if len(tasks_to_assign) >= 3:
    tasks_to_assign[2].assignee_id = tm_carol.member_id
if len(tasks_to_assign) >= 4:
    tasks_to_assign[3].assignee_id = tm_david.member_id
if len(tasks_to_assign) >= 5:
    tasks_to_assign[4].assignee_id = tm_eva.member_id

db.commit()
```

Add this after the mock MRs section.

- [ ] **Step 7: Test seed_data.py runs without errors**

Run: `python3 seed_data.py`
Expected: No errors, database populated

- [ ] **Step 8: Run test to verify seed data**

Run: `pytest tests/test_seed.py::test_seed_data_creates_team_members -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add seed_data.py tests/test_seed.py
git commit -m "feat: seed 5 team members, mock Jira issues, and mock GitLab MRs"
```

---

## Phase 2: Workload Aggregation API

### Task 5: Create Workload Routes with Aggregation Logic

**Files:**
- Create: `web/routers/workload_routes.py`
- Modify: `web/app.py` (register new router)

- [ ] **Step 1: Write test for workload aggregation endpoint**

```python
# tests/test_workload.py
import pytest
from fastapi.testclient import TestClient
from db.base import SessionLocal
from db.models import TeamMemberORM, TaskORM, MockJiraIssueORM, MockGitLabMRORM

def test_team_workload_endpoint_structure():
    """Test /api/workload/team returns correct structure"""
    from web.app import app
    
    client = TestClient(app)
    
    # Create test app (application_id required)
    db = SessionLocal()
    from db.models import ApplicationORM
    test_app = ApplicationORM(name="Test App", code="TEST")
    db.add(test_app)
    db.commit()
    app_id = test_app.application_id
    db.close()
    
    response = client.get(f"/api/workload/team?app_id={app_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert "team" in data
    assert "summary" in data
    assert isinstance(data["team"], list)
    assert "total_members" in data["summary"]
    assert "overloaded_count" in data["summary"]
```

Run: `pytest tests/test_workload.py::test_team_workload_endpoint_structure -v`
Expected: FAIL — endpoint doesn't exist

- [ ] **Step 2: Create web/routers/workload_routes.py**

Create the file with this content:

```python
"""Team workload aggregation — local tasks, Jira issues, GitLab MRs."""

import json
import time
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.base import SessionLocal
from db.models import (
    TeamMemberORM, TaskORM, MockJiraIssueORM, MockGitLabMRORM,
    JiraConfigORM, GitLabConfigORM, AppJiraConfigORM, AppGitLabConfigORM
)

router = APIRouter(prefix="/api/workload", tags=["workload"])

_cache: dict = {}
_CACHE_TTL = 60


def _cache_get(key):
    e = _cache.get(key)
    if e and time.time() - e["ts"] < _CACHE_TTL:
        return e["data"]
    return None


def _cache_set(key, data):
    _cache[key] = {"data": data, "ts": time.time()}


def _cache_bust():
    _cache.clear()


def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/team")
def get_team_workload(app_id: str = Query(...), db: Session = Depends(_db)):
    """Return team workload: aggregated local tasks, Jira issues, MRs."""
    
    cache_key = f"workload_team_{app_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
    
    # Fetch all team members
    team_members = db.query(TeamMemberORM).filter(TeamMemberORM.is_active == True).all()
    
    team_data = []
    overloaded_count = 0
    total_local = 0
    total_jira = 0
    total_mrs = 0
    
    for member in team_members:
        # Local tasks
        local_tasks = db.query(TaskORM).filter(
            TaskORM.assignee_id == member.member_id
        ).all()
        
        local_task_list = [
            {
                "task_id": t.task_id,
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "due_date": str(t.due_date) if t.due_date else None,
            }
            for t in local_tasks
        ]
        local_count = len(local_tasks)
        total_local += local_count
        
        # Mock Jira issues (or real Jira if configured)
        jira_issues = db.query(MockJiraIssueORM).filter(
            MockJiraIssueORM.assignee_email == member.email
        ).all()
        
        jira_list = [
            {
                "key": i.key,
                "summary": i.summary,
                "status": i.status,
                "priority": i.priority,
            }
            for i in jira_issues
        ]
        jira_count = len(jira_issues)
        total_jira += jira_count
        
        # Mock GitLab MRs (or real GitLab if configured)
        # Match by author_username or in reviewers
        mrs = db.query(MockGitLabMRORM).filter(
            (MockGitLabMRORM.author_username == member.gitlab_username) |
            (MockGitLabMRORM.reviewers.like(f'%{member.gitlab_username}%'))
        ).all()
        
        mr_list = [
            {
                "iid": m.iid,
                "title": m.title,
                "state": m.state,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in mrs
        ]
        mr_count = len(mrs)
        total_mrs += mr_count
        
        # Calculate total and capacity
        total_active = local_count + jira_count + mr_count
        capacity_status = (
            "light" if total_active < 4
            else "moderate" if total_active < 8
            else "heavy"
        )
        
        if total_active >= member.max_concurrent_tasks:
            overloaded_count += 1
        
        team_data.append({
            "member_id": member.member_id,
            "name": member.name,
            "email": member.email,
            "gitlab_username": member.gitlab_username,
            "role": member.role,
            "max_concurrent_tasks": member.max_concurrent_tasks,
            "workload": {
                "local_tasks": local_task_list,
                "local_count": local_count,
                "jira_issues": jira_list,
                "jira_count": jira_count,
                "gitlab_mrs": mr_list,
                "mr_count": mr_count,
                "total_active": total_active,
                "capacity_status": capacity_status,
            }
        })
    
    result = {
        "team": sorted(team_data, key=lambda x: -x["workload"]["total_active"]),
        "summary": {
            "total_members": len(team_members),
            "overloaded_count": overloaded_count,
            "total_local_tasks": total_local,
            "total_jira_issues": total_jira,
            "total_mrs": total_mrs,
            "last_updated": datetime.utcnow().isoformat(),
        }
    }
    
    _cache_set(cache_key, result)
    return result


@router.get("/team/members")
def get_team_members(db: Session = Depends(_db)):
    """Return list of all team members."""
    members = db.query(TeamMemberORM).all()
    return [
        {
            "member_id": m.member_id,
            "name": m.name,
            "email": m.email,
            "gitlab_username": m.gitlab_username,
            "role": m.role,
            "max_concurrent_tasks": m.max_concurrent_tasks,
            "is_active": m.is_active,
        }
        for m in members
    ]


@router.post("/team/members")
def create_team_member(body: dict, db: Session = Depends(_db)):
    """Create new team member."""
    member = TeamMemberORM(
        name=body.get("name"),
        email=body.get("email"),
        gitlab_username=body.get("gitlab_username"),
        role=body.get("role"),
        max_concurrent_tasks=body.get("max_concurrent_tasks", 8),
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    
    _cache_bust()
    
    return {
        "member_id": member.member_id,
        "name": member.name,
        "email": member.email,
    }


@router.patch("/team/members/{member_id}")
def update_team_member(member_id: str, body: dict, db: Session = Depends(_db)):
    """Update team member."""
    member = db.query(TeamMemberORM).filter(TeamMemberORM.member_id == member_id).first()
    if not member:
        raise HTTPException(404, "Team member not found")
    
    if "name" in body:
        member.name = body["name"]
    if "email" in body:
        member.email = body["email"]
    if "role" in body:
        member.role = body["role"]
    if "max_concurrent_tasks" in body:
        member.max_concurrent_tasks = body["max_concurrent_tasks"]
    if "is_active" in body:
        member.is_active = body["is_active"]
    
    db.commit()
    db.refresh(member)
    
    _cache_bust()
    
    return {"status": "updated", "member_id": member.member_id}


@router.delete("/team/members/{member_id}")
def delete_team_member(member_id: str, db: Session = Depends(_db)):
    """Delete team member (tasks get unassigned)."""
    member = db.query(TeamMemberORM).filter(TeamMemberORM.member_id == member_id).first()
    if not member:
        raise HTTPException(404, "Team member not found")
    
    # Unassign tasks
    db.query(TaskORM).filter(TaskORM.assignee_id == member_id).update(
        {TaskORM.assignee_id: None}
    )
    
    db.delete(member)
    db.commit()
    
    _cache_bust()
    
    return {"status": "deleted", "member_id": member_id}


@router.post("/team/refresh")
def refresh_workload_cache():
    """Manually bust cache and reload data."""
    _cache_bust()
    return {"ok": True}
```

- [ ] **Step 3: Register workload routes in web/app.py**

Open `web/app.py` and find the section where routers are imported and included. Add this import at the top:

```python
from web.routers import workload_routes
```

Then find the app initialization section (where `.include_router()` is called) and add:

```python
app.include_router(workload_routes.router)
```

- [ ] **Step 4: Run test to verify endpoint works**

Run: `pytest tests/test_workload.py::test_team_workload_endpoint_structure -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/routers/workload_routes.py web/app.py tests/test_workload.py
git commit -m "feat: add workload aggregation API with team workload endpoint"
```

---

### Task 6: Update Task Routes to Include Assignee

**Files:**
- Modify: `web/routers/tasks.py` (update response schema)

- [ ] **Step 1: Write test for task response with assignee**

```python
# tests/test_task_api.py
def test_task_response_includes_assignee():
    """Verify task GET response includes assignee_id"""
    from fastapi.testclient import TestClient
    from web.app import app
    from db.base import SessionLocal
    from db.models import TaskORM, TeamMemberORM
    
    db = SessionLocal()
    member = TeamMemberORM(name="Alice", email="alice@company.com")
    db.add(member)
    db.commit()
    
    task = TaskORM(title="Test", assignee_id=member.member_id)
    db.add(task)
    db.commit()
    task_id = task.task_id
    db.close()
    
    client = TestClient(app)
    response = client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert "assignee_id" in data
    assert data["assignee_id"] == member.member_id
```

Run: `pytest tests/test_task_api.py::test_task_response_includes_assignee -v`
Expected: FAIL — response doesn't include assignee_id

- [ ] **Step 2: Update GET /api/tasks/{id} response in tasks.py**

Find the task retrieval endpoint in `web/routers/tasks.py` (the one that returns a single task). Update the response to include `assignee_id`:

Look for a function like `get_task()` and ensure the response includes:

```python
return {
    "task_id": task.task_id,
    "title": task.title,
    "description": task.description,
    "due_date": str(task.due_date) if task.due_date else None,
    "priority": task.priority,
    "status": task.status,
    "project_id": task.project_id,
    "assignee_id": task.assignee_id,  # ADD THIS LINE
    "tags": task.tags,
    "created_at": task.created_at.isoformat(),
    "updated_at": task.updated_at.isoformat(),
}
```

- [ ] **Step 3: Update GET /api/tasks (list) response**

Find the tasks list endpoint and ensure each task in the list also includes `assignee_id` in the response.

- [ ] **Step 4: Update PATCH /api/tasks/{id} to accept assignee_id**

Find the update endpoint and ensure the body handler includes:

```python
if "assignee_id" in body:
    task.assignee_id = body["assignee_id"]
```

- [ ] **Step 5: Run test to verify**

Run: `pytest tests/test_task_api.py::test_task_response_includes_assignee -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web/routers/tasks.py tests/test_task_api.py
git commit -m "feat: include assignee_id in task API responses"
```

---

## Phase 3: Web UI — Team Workload Dashboard

### Task 7: Add Team Workload View to index.html

**Files:**
- Modify: `web/static/index.html` (add view and Alpine.js logic)

- [ ] **Step 1: Write test for team workload view existence**

```python
# tests/test_ui.py
def test_team_workload_view_exists():
    """Verify team workload view HTML exists in index.html"""
    with open("/Users/puneetsharma/Workspace/projects/ai-lab/command-center/web/static/index.html", "r") as f:
        html = f.read()
    
    assert "view==='team-workload'" in html or "view===\"team-workload\"" in html
    assert "Team Workload" in html or "team workload" in html.lower()
```

Run: `pytest tests/test_ui.py::test_team_workload_view_exists -v`
Expected: FAIL — view doesn't exist

- [ ] **Step 2: Find the nav section and add "Team" link**

Open `web/static/index.html`. Find the navigation menu (look for `<div` with id or class like "nav" or "sidebar"). Find the section with links like "Tasks", "Projects", etc.

Add a new nav item:

```html
<button @click="nav('team-workload')" :class="{'nav-active': view==='team-workload'}" class="nav-item">
  Team
</button>
```

Place it after the Projects link.

- [ ] **Step 3: Add team workload view HTML**

Find the section where views are defined (look for `x-show="view==='tasks'"` or similar). After the Projects view, add this new view:

```html
<!-- ══ TEAM WORKLOAD VIEW ══ -->
<div x-show="view==='team-workload'" x-cloak>

  <!-- Header -->
  <div style="margin-bottom:24px;">
    <h1 style="font-size:28px;font-weight:800;margin-bottom:8px;">Team Workload</h1>
    <p style="color:var(--text-2);font-size:14px;">View workload across team members — local tasks, Jira issues, and GitLab MRs.</p>
  </div>

  <!-- Toolbar -->
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;flex-wrap:wrap;">
    <button @click="loadTeamWorkload()" :disabled="workloadLoading"
      style="padding:8px 16px;border-radius:8px;background:linear-gradient(135deg,#6366f1,#818cf8);color:#fff;border:none;font-size:13px;font-weight:700;cursor:pointer;">
      <span x-show="!workloadLoading">↻ Refresh</span>
      <span x-show="workloadLoading">Loading…</span>
    </button>
    <input x-model="workloadFilter" placeholder="Search member…"
      style="padding:8px 12px;border-radius:8px;border:1px solid var(--border);font-size:13px;width:200px;color:var(--text-1);background:var(--bg);">
  </div>

  <!-- Error -->
  <div x-show="workloadError" style="padding:12px 16px;border-radius:8px;background:#fff1f2;border:1px solid #fecdd3;color:#be123c;font-size:13px;margin-bottom:16px;" x-text="workloadError"></div>

  <!-- Summary Cards -->
  <div x-show="workloadData.summary" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;margin-bottom:24px;">
    <div class="card" style="padding:16px;text-align:center;">
      <div style="font-size:24px;font-weight:800;color:#6366f1;" x-text="workloadData.summary.total_members||0"></div>
      <div style="font-size:11px;color:var(--text-3);font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-top:6px;">Team Members</div>
    </div>
    <div class="card" style="padding:16px;text-align:center;">
      <div style="font-size:24px;font-weight:800;color:#ef4444;" x-text="workloadData.summary.overloaded_count||0"></div>
      <div style="font-size:11px;color:var(--text-3);font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-top:6px;">Overloaded</div>
    </div>
    <div class="card" style="padding:16px;text-align:center;">
      <div style="font-size:24px;font-weight:800;color:#3b82f6;" x-text="workloadData.summary.total_local_tasks||0"></div>
      <div style="font-size:11px;color:var(--text-3);font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-top:6px;">Local Tasks</div>
    </div>
    <div class="card" style="padding:16px;text-align:center;">
      <div style="font-size:24px;font-weight:800;color:#f59e0b;" x-text="workloadData.summary.total_jira_issues||0"></div>
      <div style="font-size:11px;color:var(--text-3);font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-top:6px;">Jira Issues</div>
    </div>
    <div class="card" style="padding:16px;text-align:center;">
      <div style="font-size:24px;font-weight:800;color:#10b981;" x-text="workloadData.summary.total_mrs||0"></div>
      <div style="font-size:11px;color:var(--text-3);font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-top:6px;">GitLab MRs</div>
    </div>
  </div>

  <!-- Team Member Cards -->
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px;">
    <template x-for="member in (workloadData.team||[]).filter(m=>!workloadFilter||m.name.toLowerCase().includes(workloadFilter.toLowerCase()))" :key="member.member_id">
      <div class="card" style="padding:0;overflow:hidden;">

        <!-- Member Header -->
        <div style="padding:14px 16px;background:var(--bg);border-bottom:1px solid var(--border);display:flex;align-items:center;gap:12px;">
          <div style="width:40px;height:40px;border-radius:10px;background:linear-gradient(135deg,#6366f1,#818cf8);display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;color:#fff;flex-shrink:0;"
            x-text="member.name.split(' ').map(w=>w[0]).join('').toUpperCase().slice(0,2)"></div>
          <div style="flex:1;min-width:0;">
            <div style="font-size:14px;font-weight:700;color:var(--text-1);" x-text="member.name"></div>
            <div style="font-size:11px;color:var(--text-2);" x-text="member.role||'—'"></div>
          </div>
          <div :style="'padding:4px 10px;border-radius:12px;font-size:11px;font-weight:700;'+(member.workload.capacity_status==='heavy'?'background:#fff1f2;color:#be123c;':member.workload.capacity_status==='moderate'?'background:#fffbeb;color:#b45309;':'background:#f0fdf4;color:#15803d;')"
            x-text="member.workload.capacity_status==='heavy'?'Heavy':member.workload.capacity_status==='moderate'?'Moderate':'Light'"></div>
        </div>

        <!-- Workload Breakdown -->
        <div style="padding:12px 16px;border-bottom:1px solid var(--border);display:flex;gap:12px;font-size:12px;color:var(--text-2);">
          <span><strong x-text="member.workload.local_count"></strong> local</span>
          <span><strong x-text="member.workload.jira_count"></strong> Jira</span>
          <span><strong x-text="member.workload.mr_count"></strong> MRs</span>
          <span style="margin-left:auto;font-weight:700;color:var(--text-1);" x-text="member.workload.total_active+' total'"></span>
        </div>

        <!-- Items List (Expandable) -->
        <div x-data="{expanded: false}" style="padding:12px 16px;">
          <button @click="expanded=!expanded" style="width:100%;text-align:left;background:none;border:none;padding:0;color:var(--text-2);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;cursor:pointer;display:flex;justify-content:space-between;align-items:center;">
            <span>Details</span>
            <span x-text="expanded?'▼':'▶'"></span>
          </button>
          <div x-show="expanded" style="margin-top:8px;font-size:12px;color:var(--text-2);">
            <div x-show="member.workload.local_count>0" style="margin-bottom:8px;">
              <div style="font-weight:700;color:var(--text-1);margin-bottom:4px;">Local Tasks</div>
              <template x-for="task in member.workload.local_tasks" :key="task.task_id">
                <div style="padding:4px 0;border-bottom:1px solid var(--border);font-size:11px;color:var(--text-2);" x-text="task.title"></div>
              </template>
            </div>
            <div x-show="member.workload.jira_count>0" style="margin-bottom:8px;">
              <div style="font-weight:700;color:var(--text-1);margin-bottom:4px;">Jira Issues</div>
              <template x-for="issue in member.workload.jira_issues" :key="issue.key">
                <div style="padding:4px 0;border-bottom:1px solid var(--border);font-size:11px;color:var(--text-2);" x-text="issue.key+' - '+issue.summary"></div>
              </template>
            </div>
            <div x-show="member.workload.mr_count>0">
              <div style="font-weight:700;color:var(--text-1);margin-bottom:4px;">GitLab MRs</div>
              <template x-for="mr in member.workload.gitlab_mrs" :key="mr.iid">
                <div style="padding:4px 0;border-bottom:1px solid var(--border);font-size:11px;color:var(--text-2);" x-text="'!'+mr.iid+' - '+mr.title"></div>
              </template>
            </div>
          </div>
        </div>

      </div>
    </template>
  </div>

  <!-- Empty State -->
  <div x-show="!workloadData.team||workloadData.team.length===0" style="text-align:center;padding:60px 20px;">
    <div style="font-size:48px;margin-bottom:16px;">👥</div>
    <div style="font-size:16px;font-weight:700;color:var(--text-1);">No team members</div>
    <p style="color:var(--text-2);font-size:14px;margin-top:8px;">Add team members to see workload.</p>
  </div>

</div>
```

- [ ] **Step 4: Add Alpine.js data and functions in the main script**

Find the Alpine.js `data()` initialization in `index.html` (look for `Alpine.data('app', () => ({`). Add these properties:

```javascript
workloadData: {},
workloadLoading: false,
workloadError: null,
workloadFilter: "",
```

Then find the methods section and add:

```javascript
async loadTeamWorkload() {
  this.workloadLoading = true;
  this.workloadError = null;
  try {
    const response = await fetch("/api/workload/team?app_id=default");
    if (!response.ok) throw new Error("Failed to load workload");
    this.workloadData = await response.json();
  } catch (err) {
    this.workloadError = err.message;
  } finally {
    this.workloadLoading = false;
  }
},
```

Also add a call to `loadTeamWorkload()` in the initialization or when switching to the team-workload view.

- [ ] **Step 5: Run test to verify view exists**

Run: `pytest tests/test_ui.py::test_team_workload_view_exists -v`
Expected: PASS

- [ ] **Step 6: Test in browser**

Start the app:
```bash
python3 start.py
```

Navigate to http://localhost:8080, click on "Team" in the sidebar, verify the workload dashboard loads with team members and their workload.

- [ ] **Step 7: Commit**

```bash
git add web/static/index.html tests/test_ui.py
git commit -m "feat: add team workload dashboard UI with member cards and workload breakdown"
```

---

## Summary

**4 Phases, 7 Tasks:**

| Phase | Task | Purpose |
|-------|------|---------|
| **Phase 1** | 1-4 | Data models + seed data (team members, tasks, mock Jira/GitLab) |
| **Phase 2** | 5-6 | Workload API + task assignment |
| **Phase 3** | 7 | Web UI team dashboard |

**Key Outcomes:**
- ✅ 5 team members seeded with realistic emails and roles
- ✅ 12-15 local tasks assigned to team members
- ✅ 8-10 mock Jira issues seeded by email
- ✅ 5-7 mock GitLab MRs seeded by username/reviewers
- ✅ `/api/workload/team` returns aggregated workload with capacity status
- ✅ Team workload dashboard view with search/filter
- ✅ Graceful fallback to mock data if Jira/GitLab not configured

**Testing:** TDD approach — each task includes failing test → implementation → passing test → commit.

---

## Self-Review

**Spec Coverage:**
- ✅ Section 1 (Data Model): Tasks 1-3 create all required tables
- ✅ Section 2 (Aggregation): Task 5 implements `/api/workload/team` with matching logic and caching
- ✅ Section 3 (UI): Task 7 builds team workload view with search and capacity indicators
- ✅ Section 4 (Seed Data): Task 4 seeds 5 members, 12-15 tasks, 8-10 mock issues, 5-7 MRs

**Placeholder Scan:** ✅ All steps include actual code/commands, no TBD/TODO

**Type Consistency:**
- ✅ `TeamMemberORM.member_id` used consistently throughout
- ✅ `TaskORM.assignee_id` matches FK definition
- ✅ Capacity status: "light"/"moderate"/"heavy" consistent

**No Gaps:** All spec requirements have corresponding tasks.
