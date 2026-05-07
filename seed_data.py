"""
Comprehensive seed data for ExecOS.
Covers: Applications · Projects · Tasks · Milestones · Commitments · Alerts ·
        Estimations · Day Planner · Delivery Templates · Delivery Releases
Safe to re-run — clears and reloads everything.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, datetime, timedelta
import uuid

from db.base import SessionLocal
from db.init_db import create_all
from db.models import (
    ApplicationORM, ProjectORM, TaskORM, MilestoneORM, CommitmentORM,
    AlertORM, EstimationORM, DayPlanItemORM,
    DeliveryTemplateORM, DeliveryTemplateItemORM,
    DeliveryReleaseORM, DeliveryReleaseItemORM,
    AppJiraConfigORM, AppGitLabConfigORM, AppSprintConfigORM,
    ProjEstimateORM, ProjEstMilestoneORM, ProjEstTaskORM,
    TeamMemberORM, MockJiraIssueORM, MockGitLabMRORM,
)

create_all()   # ensure new tables exist (runs migrations too)
db = SessionLocal()

# ── Wipe ──────────────────────────────────────────────────────────────────────
for model in [DeliveryReleaseItemORM, DeliveryReleaseORM,
              DeliveryTemplateItemORM, DeliveryTemplateORM,
              DayPlanItemORM, TaskORM, MilestoneORM, CommitmentORM,
              AlertORM, EstimationORM, ProjectORM,
              AppJiraConfigORM, AppGitLabConfigORM, AppSprintConfigORM,
              ProjEstTaskORM, ProjEstMilestoneORM, ProjEstimateORM,
              TeamMemberORM, MockJiraIssueORM, MockGitLabMRORM,
              ApplicationORM]:
    db.query(model).delete()
db.commit()

today = date.today()
now   = datetime.utcnow()

def d(n):    return today + timedelta(days=n)
def dt(n):   return datetime.combine(today + timedelta(days=n), datetime.min.time())
def uid():   return str(uuid.uuid4())
def hm(h,m): return f"{h:02d}:{m:02d}"

# ── Applications ─────────────────────────────────────────────────────────────
a1 = uid(); a2 = uid(); a3 = uid(); a4 = uid()

db.add_all([
    ApplicationORM(application_id=a1, name="ExecOS Platform",
                   code="EXEC",
                   description="Internal execution & command-centre platform for leadership. FastAPI + SQLite + Alpine.js.",
                   created_at=dt(-120)),

    ApplicationORM(application_id=a2, name="Mobile Suite",
                   code="MOBILE",
                   description="Cross-platform mobile apps — React Native. Serves push briefings and offline task management.",
                   created_at=dt(-90)),

    ApplicationORM(application_id=a3, name="Customer Portal",
                   code="PORTAL",
                   description="Self-service customer portal for account management, billing, and support.",
                   created_at=dt(-180)),

    ApplicationORM(application_id=a4, name="Data & Analytics Platform",
                   code="DATA",
                   description="Centralized data warehouse, dbt models, Databricks pipelines, and analytics dashboards.",
                   created_at=dt(-60)),
])
db.commit()

# ── Team Members ──────────────────────────────────────────────────────────────
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

# ── Projects ──────────────────────────────────────────────────────────────────
p1 = uid(); p2 = uid(); p3 = uid()
p4 = uid(); p5 = uid(); p6 = uid(); p7 = uid()

db.add_all([
    ProjectORM(project_id=p1, name="ExecOS Platform v2.0",
               description="FastAPI backend, SQLite, Alpine.js SPA — Gantt, estimator, integrations.",
               status="active", owner="Puneet Sharma",
               due_date=d(14), created_at=dt(-60), application_id=a1),

    ProjectORM(project_id=p2, name="Mobile Companion App",
               description="React Native app for ExecOS — push briefings, offline task updates.",
               status="active", owner="Priya Mehta",
               due_date=d(45), created_at=dt(-30), application_id=a2),

    ProjectORM(project_id=p3, name="API Gateway Migration",
               description="Replace legacy REST layer with Kong. Unified rate-limiting, auth, observability.",
               status="active", owner="Rahul Singh",
               due_date=d(30), created_at=dt(-20), application_id=a1),

    ProjectORM(project_id=p4, name="Q2 OKR Programme",
               description="Track, measure and report Q2 OKRs across all squads. Board presentation due soon.",
               status="active", owner="Puneet Sharma",
               due_date=d(5), created_at=dt(-90)),

    ProjectORM(project_id=p5, name="Infrastructure Hardening",
               description="Security audit, dependency upgrades, penetration testing, SOC 2 prep.",
               status="on_hold", owner="Rahul Singh",
               due_date=None, created_at=dt(-45), application_id=a3),

    ProjectORM(project_id=p6, name="Customer Portal Redesign",
               description="Full UX overhaul of the self-service portal. Shipped ahead of schedule.",
               status="completed", owner="Priya Mehta",
               due_date=d(-15), created_at=dt(-120), application_id=a3),

    ProjectORM(project_id=p7, name="Data Platform v3",
               description="Migrate analytics pipelines from Redshift to Databricks. Implement dbt models.",
               status="active", owner="Ananya Iyer",
               due_date=d(60), created_at=dt(-10), application_id=a4),
])
db.commit()

# ── Tasks ─────────────────────────────────────────────────────────────────────
# Today/overdue tasks are seeded intentionally to trigger the alert engine
db.add_all([

    # ── ExecOS Platform v2.0 ──────────────────────────────────────────────────
    TaskORM(task_id=uid(), title="Define API contracts and OpenAPI spec",
            project_id=p1, priority="high", status="done",
            due_date=d(-40), completed_at=dt(-42), created_at=dt(-60)),
    TaskORM(task_id=uid(), title="SQLite schema + ORM models",
            project_id=p1, priority="high", status="done",
            due_date=d(-30), completed_at=dt(-31), created_at=dt(-55)),
    TaskORM(task_id=uid(), title="FastAPI CRUD endpoints",
            project_id=p1, priority="high", status="done",
            due_date=d(-25), completed_at=dt(-24), created_at=dt(-50)),
    TaskORM(task_id=uid(), title="Alpine.js SPA — dashboard and task views",
            project_id=p1, priority="high", status="in_progress",
            due_date=d(0),   created_at=dt(-20)),  # DUE TODAY
    TaskORM(task_id=uid(), title="SOD/EOD email automation",
            project_id=p1, priority="medium", status="in_progress",
            due_date=d(0),   created_at=dt(-10)),  # DUE TODAY
    TaskORM(task_id=uid(), title="Jira and GitLab integration testing",
            project_id=p1, priority="high", status="in_progress",
            due_date=d(-2),  created_at=dt(-5)),   # OVERDUE
    TaskORM(task_id=uid(), title="Write unit tests for alert engine",
            project_id=p1, priority="medium", status="todo",
            due_date=d(-1),  created_at=dt(-4)),   # OVERDUE
    TaskORM(task_id=uid(), title="QA regression testing",
            project_id=p1, priority="high", status="todo",
            due_date=d(7),   created_at=dt(-3)),
    TaskORM(task_id=uid(), title="Production deployment and rollout plan",
            project_id=p1, priority="critical", status="todo",
            due_date=d(14),  created_at=dt(-3)),

    # ── Mobile Companion App ──────────────────────────────────────────────────
    TaskORM(task_id=uid(), title="UX wireframes and design system",
            project_id=p2, priority="high", status="done",
            due_date=d(-20), completed_at=dt(-21), created_at=dt(-30)),
    TaskORM(task_id=uid(), title="React Native project setup and CI/CD",
            project_id=p2, priority="medium", status="done",
            due_date=d(-15), completed_at=dt(-14), created_at=dt(-28)),
    TaskORM(task_id=uid(), title="Authentication and session management",
            project_id=p2, priority="high", status="in_progress",
            due_date=d(-3),  created_at=dt(-12)),  # OVERDUE
    TaskORM(task_id=uid(), title="Dashboard and task list screens",
            project_id=p2, priority="medium", status="todo",
            due_date=d(0),   created_at=dt(-5)),   # DUE TODAY
    TaskORM(task_id=uid(), title="Push notification integration",
            project_id=p2, priority="medium", status="todo",
            due_date=d(20),  created_at=dt(-3)),
    TaskORM(task_id=uid(), title="Beta testing with 10 users",
            project_id=p2, priority="high", status="todo",
            due_date=d(40),  created_at=dt(-2)),

    # ── API Gateway Migration ─────────────────────────────────────────────────
    TaskORM(task_id=uid(), title="Current state API audit and documentation",
            project_id=p3, priority="medium", status="done",
            due_date=d(-10), completed_at=dt(-11), created_at=dt(-20)),
    TaskORM(task_id=uid(), title="Kong gateway config and routing policies",
            project_id=p3, priority="high", status="in_progress",
            due_date=d(0),   created_at=dt(-15)),  # DUE TODAY
    TaskORM(task_id=uid(), title="Rate limiting and auth plugin setup",
            project_id=p3, priority="high", status="todo",
            due_date=d(-4),  created_at=dt(-10)),  # OVERDUE
    TaskORM(task_id=uid(), title="Service mesh and observability setup",
            project_id=p3, priority="medium", status="todo",
            due_date=d(15),  created_at=dt(-5)),
    TaskORM(task_id=uid(), title="Load and performance testing",
            project_id=p3, priority="high", status="todo",
            due_date=d(22),  created_at=dt(-3)),
    TaskORM(task_id=uid(), title="Cutover plan and rollback procedure",
            project_id=p3, priority="critical", status="todo",
            due_date=d(28),  created_at=dt(-2)),

    # ── Q2 OKR Programme ─────────────────────────────────────────────────────
    TaskORM(task_id=uid(), title="Define Q2 OKRs with engineering leads",
            project_id=p4, priority="critical", status="done",
            due_date=d(-85), completed_at=dt(-86), created_at=dt(-90)),
    TaskORM(task_id=uid(), title="Mid-quarter OKR health check",
            project_id=p4, priority="high", status="done",
            due_date=d(-45), completed_at=dt(-44), created_at=dt(-60)),
    TaskORM(task_id=uid(), title="Q2 OKR progress dashboard update",
            project_id=p4, priority="medium", status="done",
            due_date=d(-10), completed_at=dt(-10), created_at=dt(-20)),
    TaskORM(task_id=uid(), title="Final Q2 results deck preparation",
            project_id=p4, priority="critical", status="in_progress",
            due_date=d(0),   created_at=dt(-5)),   # DUE TODAY - CRITICAL
    TaskORM(task_id=uid(), title="All-hands Q2 retrospective session prep",
            project_id=p4, priority="high", status="todo",
            due_date=d(5),   created_at=dt(-3)),
    TaskORM(task_id=uid(), title="Q3 OKR planning kickoff",
            project_id=p4, priority="medium", status="todo",
            due_date=d(12),  created_at=dt(-2)),

    # ── Infrastructure Hardening (overdue — on hold) ──────────────────────────
    TaskORM(task_id=uid(), title="Third-party security audit — schedule vendor",
            project_id=p5, priority="critical", status="todo",
            due_date=d(-7),  created_at=dt(-45)),  # OVERDUE CRITICAL
    TaskORM(task_id=uid(), title="Dependency vulnerability remediation",
            project_id=p5, priority="high", status="todo",
            due_date=d(-5),  created_at=dt(-30)),  # OVERDUE
    TaskORM(task_id=uid(), title="Penetration testing engagement",
            project_id=p5, priority="high", status="todo",
            due_date=d(20),  created_at=dt(-15)),
    TaskORM(task_id=uid(), title="SOC 2 compliance documentation",
            project_id=p5, priority="medium", status="todo",
            due_date=None,   created_at=dt(-10)),

    # ── Customer Portal (all done) ────────────────────────────────────────────
    TaskORM(task_id=uid(), title="Stakeholder interviews and requirements",
            project_id=p6, priority="high", status="done",
            due_date=d(-100), completed_at=dt(-102), created_at=dt(-120)),
    TaskORM(task_id=uid(), title="Design system and component library",
            project_id=p6, priority="high", status="done",
            due_date=d(-75),  completed_at=dt(-73), created_at=dt(-110)),
    TaskORM(task_id=uid(), title="Frontend implementation",
            project_id=p6, priority="high", status="done",
            due_date=d(-40),  completed_at=dt(-38), created_at=dt(-90)),
    TaskORM(task_id=uid(), title="UAT and bug fixes",
            project_id=p6, priority="medium", status="done",
            due_date=d(-20),  completed_at=dt(-19), created_at=dt(-50)),
    TaskORM(task_id=uid(), title="Production launch",
            project_id=p6, priority="critical", status="done",
            due_date=d(-15),  completed_at=dt(-15), created_at=dt(-30)),

    # ── Data Platform v3 ─────────────────────────────────────────────────────
    TaskORM(task_id=uid(), title="Databricks workspace provisioning",
            project_id=p7, priority="high", status="in_progress",
            due_date=d(0),   created_at=dt(-8)),   # DUE TODAY
    TaskORM(task_id=uid(), title="dbt project structure and base models",
            project_id=p7, priority="medium", status="todo",
            due_date=d(10),  created_at=dt(-6)),
    TaskORM(task_id=uid(), title="Redshift to Databricks migration scripts",
            project_id=p7, priority="high", status="todo",
            due_date=d(-2),  created_at=dt(-5)),   # OVERDUE
    TaskORM(task_id=uid(), title="Data quality validation suite",
            project_id=p7, priority="medium", status="todo",
            due_date=d(25),  created_at=dt(-3)),
    TaskORM(task_id=uid(), title="Analytics dashboard handoff",
            project_id=p7, priority="low", status="todo",
            due_date=d(55),  created_at=dt(-2)),
])
db.commit()

# ── Mock Jira Issues ──────────────────────────────────────────────────────────
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

# ── Mock GitLab MRs ────────────────────────────────────────────────────────────
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

# ── Milestones ────────────────────────────────────────────────────────────────
db.add_all([
    MilestoneORM(milestone_id=uid(), title="Alpha Release Ready",
                 project_id=p1, due_date=d(7),   status="pending",   created_at=dt(-60)),
    MilestoneORM(milestone_id=uid(), title="Integration Test Sign-off",
                 project_id=p1, due_date=d(-1),  status="pending",   created_at=dt(-30)),  # OVERDUE
    MilestoneORM(milestone_id=uid(), title="Production Deploy",
                 project_id=p1, due_date=d(14),  status="pending",   created_at=dt(-60)),

    MilestoneORM(milestone_id=uid(), title="Design Handoff Complete",
                 project_id=p2, due_date=d(-10), status="completed", created_at=dt(-30)),
    MilestoneORM(milestone_id=uid(), title="Auth Module Done",
                 project_id=p2, due_date=d(-2),  status="pending",   created_at=dt(-25)),  # OVERDUE
    MilestoneORM(milestone_id=uid(), title="App Store Submission",
                 project_id=p2, due_date=d(42),  status="pending",   created_at=dt(-30)),

    MilestoneORM(milestone_id=uid(), title="Kong Config Complete",
                 project_id=p3, due_date=d(0),   status="pending",   created_at=dt(-20)),  # DUE TODAY
    MilestoneORM(milestone_id=uid(), title="API Gateway Live",
                 project_id=p3, due_date=d(30),  status="pending",   created_at=dt(-20)),

    MilestoneORM(milestone_id=uid(), title="Q2 Results Presentation",
                 project_id=p4, due_date=d(5),   status="pending",   created_at=dt(-90)),
    MilestoneORM(milestone_id=uid(), title="Q2 Mid-Quarter Review",
                 project_id=p4, due_date=d(-30), status="completed", created_at=dt(-90)),

    MilestoneORM(milestone_id=uid(), title="Security Certification",
                 project_id=p5, due_date=d(30),  status="pending",   created_at=dt(-45)),
    MilestoneORM(milestone_id=uid(), title="Pen Test Complete",
                 project_id=p5, due_date=d(-10), status="pending",   created_at=dt(-40)),  # OVERDUE

    MilestoneORM(milestone_id=uid(), title="Portal Go-Live",
                 project_id=p6, due_date=d(-15), status="completed", created_at=dt(-120)),

    MilestoneORM(milestone_id=uid(), title="Databricks POC Done",
                 project_id=p7, due_date=d(-3),  status="pending",   created_at=dt(-10)),  # OVERDUE
])
db.commit()

# ── Assign Tasks to Team Members ──────────────────────────────────────────────
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
if len(tasks_to_assign) >= 6:
    tasks_to_assign[5].assignee_id = tm_alice.member_id
if len(tasks_to_assign) >= 7:
    tasks_to_assign[6].assignee_id = tm_bob.member_id
if len(tasks_to_assign) >= 8:
    tasks_to_assign[7].assignee_id = tm_carol.member_id
if len(tasks_to_assign) >= 9:
    tasks_to_assign[8].assignee_id = tm_david.member_id
if len(tasks_to_assign) >= 10:
    tasks_to_assign[9].assignee_id = tm_eva.member_id

db.commit()

# ── Commitments ───────────────────────────────────────────────────────────────
db.add_all([
    CommitmentORM(commitment_id=uid(),
                  title="Deliver ExecOS v2.0 live demo to leadership",
                  description="Full walk-through of Gantt, email briefings, Jira/GitLab integrations.",
                  due_date=d(0),  status="pending", project_id=p1, created_at=dt(-10)),  # DUE TODAY

    CommitmentORM(commitment_id=uid(),
                  title="Present Q2 OKR final results at all-hands",
                  due_date=d(5),  status="pending", project_id=p4, created_at=dt(-14)),

    CommitmentORM(commitment_id=uid(),
                  title="Resolve all P1 security audit findings",
                  due_date=d(-3), status="pending", project_id=p5, created_at=dt(-7)),   # OVERDUE MISSED

    CommitmentORM(commitment_id=uid(),
                  title="Mobile app wireframes reviewed by design team",
                  due_date=d(-5), status="missed",  project_id=p2, created_at=dt(-20)),

    CommitmentORM(commitment_id=uid(),
                  title="Customer portal redesign stakeholder sign-off",
                  due_date=d(-16),status="fulfilled",project_id=p6, created_at=dt(-30)),

    CommitmentORM(commitment_id=uid(),
                  title="API gateway load test results shared with CTO",
                  due_date=d(-1), status="pending", project_id=p3, created_at=dt(-8)),   # OVERDUE

    CommitmentORM(commitment_id=uid(),
                  title="Data Platform migration plan approved",
                  due_date=d(3),  status="pending", project_id=p7, created_at=dt(-5)),
])
db.commit()

# ── Alerts (mix of severities, sources, read/unread) ──────────────────────────
db.add_all([
    AlertORM(alert_id=uid(),
             title="🚨 Security audit 7 days overdue — SOC 2 at risk",
             message="Infrastructure Hardening: third-party audit was due " + d(-7).isoformat() + ". Project is on hold but this blocks SOC 2 certification.",
             severity="critical", source="risk-engine", is_read=False, created_at=dt(-1)),

    AlertORM(alert_id=uid(),
             title="🚨 Missed commitment: P1 security findings unresolved",
             message="'Resolve all P1 security audit findings' was due " + d(-3).isoformat() + " and is still pending.",
             severity="critical", source="commitment-tracker", is_read=False, created_at=dt(-1)),

    AlertORM(alert_id=uid(),
             title="⚠️ Q2 OKR presentation due in 5 days",
             message="Final deck is in-progress. All-hands retro and Q3 kickoff not started. Risk of missing leadership deadline.",
             severity="warning", source="deadline-monitor", is_read=False, created_at=dt(-1)),

    AlertORM(alert_id=uid(),
             title="⚠️ API Gateway load test commitment overdue",
             message="CTO is waiting for load test results shared by " + d(-1).isoformat() + ". Escalate immediately.",
             severity="warning", source="commitment-tracker", is_read=False, created_at=dt(0)),

    AlertORM(alert_id=uid(),
             title="⚠️ 6 tasks due today across 5 projects",
             message="Tasks due today: Alpine.js SPA, SOD/EOD automation, Dashboard screens, Kong config, Q2 deck, Databricks provisioning.",
             severity="warning", source="daily-digest", is_read=False, created_at=dt(0)),

    AlertORM(alert_id=uid(),
             title="⚠️ Mobile Auth module — 3 days overdue",
             message="Auth module for Mobile Companion App was due " + d(-3).isoformat() + ". Blocking dashboard and push notification work.",
             severity="warning", source="risk-engine", is_read=False, created_at=dt(-1)),

    AlertORM(alert_id=uid(),
             title="ℹ️ ExecOS v2.0 demo scheduled for today",
             message="Leadership demo commitment is due today. Ensure Jira/GitLab integrations, Gantt, and Day Planner are working.",
             severity="info", source="system", is_read=False, created_at=dt(0)),

    AlertORM(alert_id=uid(),
             title="ℹ️ Customer Portal Redesign shipped ahead of schedule",
             message="All 5 tasks completed. Project closed 15 days before deadline. Outstanding execution by Priya's team.",
             severity="info", source="system", is_read=True, created_at=dt(-15)),

    AlertORM(alert_id=uid(),
             title="ℹ️ Weekly summary — 10 tasks completed",
             message="10 tasks completed across 4 projects this week. 2 milestones hit. 4 new tasks created.",
             severity="info", source="weekly-summary", is_read=True, created_at=dt(-7)),

    AlertORM(alert_id=uid(),
             title="ℹ️ Data Platform v3 kickoff complete",
             message="Project scoped and team assembled. Databricks workspace provisioning started.",
             severity="info", source="system", is_read=True, created_at=dt(-10)),
])
db.commit()

# ── Estimations ───────────────────────────────────────────────────────────────
db.add_all([
    EstimationORM(estimation_id=uid(), title="Mobile Auth Module",
                  project_id=p2, story_points=5, complexity="medium",
                  testing_effort="thorough", has_release_paperwork=False,
                  velocity=2, start_date=d(0),
                  dev_days=3, testing_days=2, paperwork_days=0,
                  holiday_buffer_days=0, total_working_days=5,
                  estimated_end_date=d(7)),

    EstimationORM(estimation_id=uid(), title="Kong Gateway Configuration",
                  project_id=p3, story_points=8, complexity="high",
                  testing_effort="moderate", has_release_paperwork=True,
                  velocity=2, start_date=d(0),
                  dev_days=5, testing_days=3, paperwork_days=1,
                  holiday_buffer_days=1, total_working_days=10,
                  estimated_end_date=d(12)),

    EstimationORM(estimation_id=uid(), title="Databricks Migration Scripts",
                  project_id=p7, story_points=13, complexity="very_high",
                  testing_effort="thorough", has_release_paperwork=True,
                  velocity=2, start_date=d(3),
                  dev_days=8, testing_days=4, paperwork_days=2,
                  holiday_buffer_days=1, total_working_days=15,
                  estimated_end_date=d(21)),
])
db.commit()

# ── Day Planner — today's schedule ────────────────────────────────────────────
# Realistic mix: calendar meetings + auto-scheduled tasks + manual items
db.add_all([
    DayPlanItemORM(item_id=uid(), plan_date=today,
                   time_start="09:00", time_end="09:30",
                   title="Daily standup — Engineering team",
                   item_type="meeting", source="calendar",
                   notes="Room: Zoom · Link in calendar", priority="medium", completed=True),

    DayPlanItemORM(item_id=uid(), plan_date=today,
                   time_start="09:30", time_end="11:00",
                   title="Final Q2 results deck preparation",
                   item_type="task", source="auto",
                   notes="Critical — due today. Block time to finish slides and data.", priority="critical"),

    DayPlanItemORM(item_id=uid(), plan_date=today,
                   time_start="11:00", time_end="12:00",
                   title="Leadership sync — ExecOS demo prep",
                   item_type="meeting", source="calendar",
                   notes="Puneet to demo Day Planner, Jira integration, and Gantt.", priority="medium"),

    DayPlanItemORM(item_id=uid(), plan_date=today,
                   time_start="12:00", time_end="12:30",
                   title="Lunch break",
                   item_type="break", source="manual",
                   notes="", priority="low"),

    DayPlanItemORM(item_id=uid(), plan_date=today,
                   time_start="12:30", time_end="14:00",
                   title="Alpine.js SPA — dashboard and task views",
                   item_type="task", source="auto",
                   notes="Due today. Finish overdue task row styling and Gantt scroll.", priority="high"),

    DayPlanItemORM(item_id=uid(), plan_date=today,
                   time_start="14:00", time_end="14:30",
                   title="1:1 with Rahul Singh — API Gateway status",
                   item_type="meeting", source="calendar",
                   notes="Review Kong config blockers and timeline risk.", priority="medium"),

    DayPlanItemORM(item_id=uid(), plan_date=today,
                   time_start="14:30", time_end="15:30",
                   title="Kong gateway config and routing policies",
                   item_type="task", source="auto",
                   notes="Due today. Finish plugin setup and validate routing rules.", priority="high"),

    DayPlanItemORM(item_id=uid(), plan_date=today,
                   time_start="15:30", time_end="16:00",
                   title="SOD/EOD email automation",
                   item_type="task", source="auto",
                   notes="Due today. Test email delivery with real SMTP config.", priority="medium"),

    DayPlanItemORM(item_id=uid(), plan_date=today,
                   time_start="16:00", time_end="16:30",
                   title="Weekly team retrospective",
                   item_type="meeting", source="calendar",
                   notes="30-min retro — what worked, what didn't, blockers.", priority="medium"),

    DayPlanItemORM(item_id=uid(), plan_date=today,
                   time_start="16:30", time_end="17:30",
                   title="Review open Jira tickets and unreviewed MRs",
                   item_type="focus", source="manual",
                   notes="Book of work review: check Jira backlog, unreviewed MRs, pending emails.", priority="high"),

    DayPlanItemORM(item_id=uid(), plan_date=today,
                   time_start="17:30", time_end="18:00",
                   title="EOD wrap-up — update task statuses",
                   item_type="task", source="manual",
                   notes="Mark completed tasks done, update project notes, check tomorrow's calendar.", priority="medium"),
])
db.commit()

# ── Delivery Templates ────────────────────────────────────────────────────────
t1 = uid(); t2 = uid()

db.add_all([
    DeliveryTemplateORM(template_id=t1, name="Standard Software Release",
                        description="Default checklist for any production software release.",
                        is_default=True, created_at=dt(-30)),
    DeliveryTemplateORM(template_id=t2, name="Hotfix / Patch Release",
                        description="Lightweight checklist for urgent hotfixes and patches.",
                        is_default=False, created_at=dt(-20)),
])
db.commit()

# Template 1 items
db.add_all([
    # Pre-release
    DeliveryTemplateItemORM(item_id=uid(), template_id=t1, order=1, title="Code freeze & feature branch merge",
                             category="pre_release", responsible_role="Tech Lead", is_required=True),
    DeliveryTemplateItemORM(item_id=uid(), template_id=t1, order=2, title="Unit & integration tests passing",
                             category="pre_release", responsible_role="QA Engineer", is_required=True),
    DeliveryTemplateItemORM(item_id=uid(), template_id=t1, order=3, title="Security scan (SAST/dependency audit)",
                             category="pre_release", responsible_role="Security", is_required=True),
    DeliveryTemplateItemORM(item_id=uid(), template_id=t1, order=4, title="Staging deployment & smoke test",
                             category="pre_release", responsible_role="DevOps", is_required=True),
    DeliveryTemplateItemORM(item_id=uid(), template_id=t1, order=5, title="Release notes & changelog drafted",
                             category="pre_release", responsible_role="PM", is_required=True),
    DeliveryTemplateItemORM(item_id=uid(), template_id=t1, order=6, title="Stakeholder sign-off",
                             category="pre_release", responsible_role="PM", is_required=False),
    # Release
    DeliveryTemplateItemORM(item_id=uid(), template_id=t1, order=7, title="Production deployment",
                             category="release", responsible_role="DevOps", is_required=True),
    DeliveryTemplateItemORM(item_id=uid(), template_id=t1, order=8, title="Database migrations run",
                             category="release", responsible_role="Backend Lead", is_required=True),
    DeliveryTemplateItemORM(item_id=uid(), template_id=t1, order=9, title="Feature flags enabled",
                             category="release", responsible_role="Tech Lead", is_required=False),
    DeliveryTemplateItemORM(item_id=uid(), template_id=t1, order=10, title="Canary / blue-green rollout verified",
                             category="release", responsible_role="DevOps", is_required=True),
    # Post-release
    DeliveryTemplateItemORM(item_id=uid(), template_id=t1, order=11, title="Production smoke test",
                             category="post_release", responsible_role="QA Engineer", is_required=True),
    DeliveryTemplateItemORM(item_id=uid(), template_id=t1, order=12, title="Monitoring & alerts baseline reviewed",
                             category="post_release", responsible_role="SRE", is_required=True),
    DeliveryTemplateItemORM(item_id=uid(), template_id=t1, order=13, title="Rollback plan tested & documented",
                             category="post_release", responsible_role="DevOps", is_required=True),
    DeliveryTemplateItemORM(item_id=uid(), template_id=t1, order=14, title="Release comms sent to stakeholders",
                             category="post_release", responsible_role="PM", is_required=False),
])
# Template 2 items
db.add_all([
    DeliveryTemplateItemORM(item_id=uid(), template_id=t2, order=1, title="Hotfix branch created from tag",
                             category="pre_release", responsible_role="Tech Lead", is_required=True),
    DeliveryTemplateItemORM(item_id=uid(), template_id=t2, order=2, title="Fix validated in staging",
                             category="pre_release", responsible_role="QA Engineer", is_required=True),
    DeliveryTemplateItemORM(item_id=uid(), template_id=t2, order=3, title="Emergency deployment to production",
                             category="release", responsible_role="DevOps", is_required=True),
    DeliveryTemplateItemORM(item_id=uid(), template_id=t2, order=4, title="Issue resolved — verify in prod",
                             category="post_release", responsible_role="QA Engineer", is_required=True),
    DeliveryTemplateItemORM(item_id=uid(), template_id=t2, order=5, title="Incident report filed",
                             category="post_release", responsible_role="PM", is_required=False),
])
db.commit()

# ── Delivery Releases ─────────────────────────────────────────────────────────
r1 = uid(); r2 = uid(); r3 = uid(); r4 = uid()

db.add_all([
    DeliveryReleaseORM(release_id=r1, name="ExecOS v2.0 — GA Release",
                       version="v2.0.0", project_id=p1, template_id=t1,
                       release_manager="Puneet Sharma",
                       target_date=d(14), status="in_progress",
                       description="General availability release of ExecOS v2.0 — full web UI, integrations, Day Planner.",
                       created_at=dt(-7)),

    DeliveryReleaseORM(release_id=r2, name="Mobile App Beta",
                       version="v0.9.0-beta", project_id=p2, template_id=t1,
                       release_manager="Priya Mehta",
                       target_date=d(40), status="planned",
                       description="Beta release of the Mobile Companion App for internal testers.",
                       created_at=dt(-5)),

    DeliveryReleaseORM(release_id=r3, name="API Gateway Cutover",
                       version="v1.0.0", project_id=p3, template_id=t1,
                       release_manager="Rahul Singh",
                       target_date=d(30), status="planned",
                       description="Production cutover from legacy REST layer to Kong API Gateway.",
                       created_at=dt(-3)),

    DeliveryReleaseORM(release_id=r4, name="Customer Portal v3.2 Hotfix",
                       version="v3.2.1", project_id=p6, template_id=t2,
                       release_manager="Priya Mehta",
                       target_date=d(-14), status="released",
                       description="Emergency hotfix for login redirect bug reported post-launch.",
                       created_at=dt(-16)),
])
db.commit()

# Populate release checklist items from templates
for rel_id, tmpl_id, done_count in [
    (r1, t1, 6),   # in-progress: first 6 items done
    (r2, t1, 0),   # planned: nothing done yet
    (r3, t1, 0),
    (r4, t2, 5),   # released: all done
]:
    tmpl_items = db.query(DeliveryTemplateItemORM).filter(
        DeliveryTemplateItemORM.template_id == tmpl_id
    ).order_by(DeliveryTemplateItemORM.order).all()
    for idx, ti in enumerate(tmpl_items):
        status = "done" if idx < done_count else "pending"
        completed_at = datetime.utcnow() if status == "done" else None
        db.add(DeliveryReleaseItemORM(
            item_id=uid(), release_id=rel_id, order=ti.order,
            title=ti.title, description=ti.description or "",
            category=ti.category, responsible_role=ti.responsible_role or "",
            is_required=ti.is_required, status=status, completed_at=completed_at,
        ))
db.commit()

# ── Per-App Integration Configs ───────────────────────────────────────────────
import json as _json

# EXEC app: Jira + GitLab + Sprint
db.add_all([
    AppJiraConfigORM(
        application_id=a1,
        base_url="https://execos.atlassian.net",
        pat="ATATT3xFfGF0_demo_token_exec_12345",
        project_keys=_json.dumps(["EXEC", "INFRA"]),
        enabled=True,
    ),
    AppGitLabConfigORM(
        application_id=a1,
        base_url="https://gitlab.com",
        access_token="glpat-demo_token_exec_67890",
        project_ids=_json.dumps(["execos/command-center", "execos/api-gateway"]),
        enabled=True,
    ),
    AppSprintConfigORM(
        application_id=a1,
        board_id="101",
        sprint_id="2401",
        sprint_name="Sprint 24 — May Platform",
        my_jira_email="puneet@execos.io",
        my_gitlab_username="puneet-sharma",
    ),
])

# MOBILE app: Jira + GitLab + Sprint
db.add_all([
    AppJiraConfigORM(
        application_id=a2,
        base_url="https://execos.atlassian.net",
        pat="ATATT3xFfGF0_demo_token_mobile_54321",
        project_keys=_json.dumps(["MOBILE", "PUSHNOTIF"]),
        enabled=True,
    ),
    AppGitLabConfigORM(
        application_id=a2,
        base_url="https://gitlab.com",
        access_token="glpat-demo_token_mobile_11111",
        project_ids=_json.dumps(["execos/mobile-app", "execos/push-service"]),
        enabled=True,
    ),
    AppSprintConfigORM(
        application_id=a2,
        board_id="202",
        sprint_id="2402",
        sprint_name="Sprint 24 — May Mobile",
        my_jira_email="priya@execos.io",
        my_gitlab_username="priya-mehta",
    ),
])

# PORTAL app: Jira + GitLab
db.add_all([
    AppJiraConfigORM(
        application_id=a3,
        base_url="https://execos.atlassian.net",
        pat="ATATT3xFfGF0_demo_token_portal_99999",
        project_keys=_json.dumps(["PORTAL"]),
        enabled=False,
    ),
    AppGitLabConfigORM(
        application_id=a3,
        base_url="https://gitlab.com",
        access_token="glpat-demo_token_portal_22222",
        project_ids=_json.dumps(["execos/customer-portal"]),
        enabled=False,
    ),
])

# DATA app: Jira
db.add_all([
    AppJiraConfigORM(
        application_id=a4,
        base_url="https://execos.atlassian.net",
        pat="ATATT3xFfGF0_demo_token_data_33333",
        project_keys=_json.dumps(["DATA", "DBTMODELS"]),
        enabled=True,
    ),
    AppSprintConfigORM(
        application_id=a4,
        board_id="303",
        sprint_id="2403",
        sprint_name="Sprint 24 — May Data",
        my_jira_email="ananya@execos.io",
        my_gitlab_username="ananya-iyer",
    ),
])
db.commit()

# ── Project Estimates (proj-planner) ─────────────────────────────────────────
e1 = uid(); e2 = uid(); e3 = uid()

db.add_all([
    ProjEstimateORM(est_id=e1,
                    name="ExecOS v2.1 Feature Pack",
                    description="Email digest v2, GitLab MR auto-assign, mobile push, risk dashboard.",
                    start_date=d(1), end_date_constraint=d(45),
                    jira_project_key="EXEC", application_id=a1),

    ProjEstimateORM(est_id=e2,
                    name="Mobile App v1.0 Launch",
                    description="Auth, offline sync, push notifications, App Store submission.",
                    start_date=d(5), end_date_constraint=d(50),
                    jira_project_key="MOBILE", application_id=a2),

    ProjEstimateORM(est_id=e3,
                    name="Data Platform Migration",
                    description="Redshift → Databricks migration, dbt base models, analytics hand-off.",
                    start_date=d(3), end_date_constraint=d(65),
                    jira_project_key="DATA", application_id=a4),
])
db.commit()

# Milestones & tasks for e1 — ExecOS v2.1
ms1a = uid(); ms1b = uid(); ms1c = uid()
db.add_all([
    ProjEstMilestoneORM(ms_id=ms1a, est_id=e1, name="Email & Alerts v2",         order=1, execution_type="sequential"),
    ProjEstMilestoneORM(ms_id=ms1b, est_id=e1, name="GitLab Auto-Assign",         order=2, execution_type="sequential"),
    ProjEstMilestoneORM(ms_id=ms1c, est_id=e1, name="Risk Dashboard",             order=3, execution_type="parallel"),
])
db.commit()
db.add_all([
    ProjEstTaskORM(ms_id=ms1a, name="Email digest engine v2",      duration_days=3, execution_type="sequential", order=1, assignee="Puneet Sharma",  jira_key="EXEC-101"),
    ProjEstTaskORM(ms_id=ms1a, name="HTML email template redesign", duration_days=2, execution_type="sequential", order=2, assignee="Priya Mehta",   jira_key="EXEC-102"),
    ProjEstTaskORM(ms_id=ms1a, name="Scheduler & retry logic",      duration_days=2, execution_type="sequential", order=3, assignee="Rahul Singh",   jira_key="EXEC-103"),
    ProjEstTaskORM(ms_id=ms1b, name="GitLab webhook listener",      duration_days=3, execution_type="sequential", order=1, assignee="Rahul Singh",   jira_key="EXEC-110"),
    ProjEstTaskORM(ms_id=ms1b, name="Auto-assign rules engine",     duration_days=3, execution_type="sequential", order=2, assignee="Puneet Sharma",  jira_key="EXEC-111"),
    ProjEstTaskORM(ms_id=ms1b, name="UI for assignment rules",      duration_days=2, execution_type="sequential", order=3, assignee="Priya Mehta",   jira_key="EXEC-112"),
    ProjEstTaskORM(ms_id=ms1c, name="Risk score calculation",       duration_days=4, execution_type="parallel",   order=1, assignee="Puneet Sharma",  jira_key="EXEC-120"),
    ProjEstTaskORM(ms_id=ms1c, name="Risk dashboard UI",            duration_days=3, execution_type="parallel",   order=2, assignee="Priya Mehta",   jira_key="EXEC-121"),
])
db.commit()

# Milestones & tasks for e2 — Mobile App
ms2a = uid(); ms2b = uid(); ms2c = uid()
db.add_all([
    ProjEstMilestoneORM(ms_id=ms2a, est_id=e2, name="Auth & Onboarding",     order=1, execution_type="sequential"),
    ProjEstMilestoneORM(ms_id=ms2b, est_id=e2, name="Core Features",          order=2, execution_type="sequential"),
    ProjEstMilestoneORM(ms_id=ms2c, est_id=e2, name="App Store Submission",   order=3, execution_type="sequential"),
])
db.commit()
db.add_all([
    ProjEstTaskORM(ms_id=ms2a, name="JWT auth flow",             duration_days=4, execution_type="sequential", order=1, assignee="Priya Mehta",   jira_key="MOBILE-11"),
    ProjEstTaskORM(ms_id=ms2a, name="Biometric login (Face/Touch)", duration_days=2, execution_type="sequential", order=2, assignee="Priya Mehta", jira_key="MOBILE-12"),
    ProjEstTaskORM(ms_id=ms2a, name="Onboarding screens",        duration_days=3, execution_type="sequential", order=3, assignee="Ananya Iyer",  jira_key="MOBILE-13"),
    ProjEstTaskORM(ms_id=ms2b, name="Task list & filters",       duration_days=3, execution_type="parallel",   order=1, assignee="Priya Mehta",  jira_key="MOBILE-20"),
    ProjEstTaskORM(ms_id=ms2b, name="Dashboard cards",           duration_days=3, execution_type="parallel",   order=2, assignee="Ananya Iyer",  jira_key="MOBILE-21"),
    ProjEstTaskORM(ms_id=ms2b, name="Push notification service", duration_days=4, execution_type="sequential", order=3, assignee="Rahul Singh",  jira_key="MOBILE-22"),
    ProjEstTaskORM(ms_id=ms2b, name="Offline sync & conflict resolution", duration_days=5, execution_type="sequential", order=4, assignee="Rahul Singh", jira_key="MOBILE-23"),
    ProjEstTaskORM(ms_id=ms2c, name="TestFlight beta distribution", duration_days=1, execution_type="sequential", order=1, assignee="Priya Mehta", jira_key="MOBILE-30"),
    ProjEstTaskORM(ms_id=ms2c, name="App Store assets & screenshots", duration_days=2, execution_type="sequential", order=2, assignee="Ananya Iyer", jira_key="MOBILE-31"),
    ProjEstTaskORM(ms_id=ms2c, name="App Store review & approval", duration_days=5, execution_type="sequential", order=3, assignee="Priya Mehta", jira_key="MOBILE-32"),
])
db.commit()

# Milestones & tasks for e3 — Data Platform
ms3a = uid(); ms3b = uid()
db.add_all([
    ProjEstMilestoneORM(ms_id=ms3a, est_id=e3, name="Databricks Setup & Migration",  order=1, execution_type="sequential"),
    ProjEstMilestoneORM(ms_id=ms3b, est_id=e3, name="dbt Models & Validation",        order=2, execution_type="sequential"),
])
db.commit()
db.add_all([
    ProjEstTaskORM(ms_id=ms3a, name="Databricks workspace provisioning", duration_days=2, execution_type="sequential", order=1, assignee="Ananya Iyer",  jira_key="DATA-01"),
    ProjEstTaskORM(ms_id=ms3a, name="ETL migration scripts (Python)",    duration_days=8, execution_type="sequential", order=2, assignee="Ananya Iyer",  jira_key="DATA-02"),
    ProjEstTaskORM(ms_id=ms3a, name="Historical data backfill",          duration_days=3, execution_type="parallel",   order=3, assignee="Rahul Singh",  jira_key="DATA-03"),
    ProjEstTaskORM(ms_id=ms3a, name="Parallel validation run",           duration_days=3, execution_type="parallel",   order=4, assignee="Ananya Iyer",  jira_key="DATA-04"),
    ProjEstTaskORM(ms_id=ms3b, name="dbt project scaffold",              duration_days=2, execution_type="sequential", order=1, assignee="Ananya Iyer",  jira_key="DATA-10"),
    ProjEstTaskORM(ms_id=ms3b, name="Staging + intermediate models",     duration_days=4, execution_type="sequential", order=2, assignee="Ananya Iyer",  jira_key="DATA-11"),
    ProjEstTaskORM(ms_id=ms3b, name="Analytics mart models",             duration_days=4, execution_type="sequential", order=3, assignee="Rahul Singh",  jira_key="DATA-12"),
    ProjEstTaskORM(ms_id=ms3b, name="Data quality tests & CI setup",     duration_days=3, execution_type="sequential", order=4, assignee="Ananya Iyer",  jira_key="DATA-13"),
])
db.commit()

# ── Day Planner — tomorrow & day-after ───────────────────────────────────────
tomorrow = today + timedelta(days=1)
day_after = today + timedelta(days=2)

db.add_all([
    # ── Tomorrow ──────────────────────────────────────────────────────────────
    DayPlanItemORM(item_id=uid(), plan_date=tomorrow,
                   time_start="09:00", time_end="09:30",
                   title="Daily standup — Engineering team",
                   item_type="meeting", source="calendar",
                   notes="Zoom standup. Focus: API Gateway cutover blockers.", priority="medium"),

    DayPlanItemORM(item_id=uid(), plan_date=tomorrow,
                   time_start="09:30", time_end="11:30",
                   title="QA regression testing — ExecOS v2.0",
                   item_type="task", source="auto",
                   notes="Run full regression suite before release. Fix any P1 bugs.", priority="high"),

    DayPlanItemORM(item_id=uid(), plan_date=tomorrow,
                   time_start="11:30", time_end="12:00",
                   title="Sprint retrospective — Sprint 23",
                   item_type="meeting", source="calendar",
                   notes="What went well, what didn't. Action items for Sprint 24.", priority="medium"),

    DayPlanItemORM(item_id=uid(), plan_date=tomorrow,
                   time_start="12:00", time_end="12:30",
                   title="Lunch", item_type="break", source="manual",
                   notes="", priority="low"),

    DayPlanItemORM(item_id=uid(), plan_date=tomorrow,
                   time_start="12:30", time_end="14:30",
                   title="Rate limiting and auth plugin setup — API Gateway",
                   item_type="task", source="auto",
                   notes="Overdue by 4 days. Block time to complete Kong plugin config.", priority="high"),

    DayPlanItemORM(item_id=uid(), plan_date=tomorrow,
                   time_start="14:30", time_end="15:00",
                   title="1:1 with Ananya Iyer — Data Platform v3 status",
                   item_type="meeting", source="calendar",
                   notes="Check Databricks POC timeline and blocker on migration scripts.", priority="medium"),

    DayPlanItemORM(item_id=uid(), plan_date=tomorrow,
                   time_start="15:00", time_end="16:30",
                   title="Penetration testing engagement — vendor coordination",
                   item_type="task", source="auto",
                   notes="Infra Hardening. Email vendor for schedule. Critical task.", priority="critical"),

    DayPlanItemORM(item_id=uid(), plan_date=tomorrow,
                   time_start="16:30", time_end="17:00",
                   title="Dashboard screens — Mobile Companion App",
                   item_type="task", source="auto",
                   notes="Due today. Finish task list and dashboard card components.", priority="medium"),

    DayPlanItemORM(item_id=uid(), plan_date=tomorrow,
                   time_start="17:00", time_end="18:00",
                   title="EOD review — update statuses, plan Thursday",
                   item_type="task", source="manual",
                   notes="Mark done tasks, check tomorrow's calendar, log blockers.", priority="low"),

    # ── Day after ─────────────────────────────────────────────────────────────
    DayPlanItemORM(item_id=uid(), plan_date=day_after,
                   time_start="09:00", time_end="09:30",
                   title="Daily standup — Engineering team",
                   item_type="meeting", source="calendar",
                   notes="Zoom standup.", priority="medium"),

    DayPlanItemORM(item_id=uid(), plan_date=day_after,
                   time_start="09:30", time_end="11:00",
                   title="Production deployment planning — ExecOS v2.0",
                   item_type="task", source="auto",
                   notes="Create deployment runbook, define rollback plan, schedule maintenance window.",
                   priority="critical"),

    DayPlanItemORM(item_id=uid(), plan_date=day_after,
                   time_start="11:00", time_end="12:00",
                   title="Q3 OKR planning kickoff",
                   item_type="meeting", source="calendar",
                   notes="Set Q3 OKRs with engineering leads. Deadline alignment.", priority="high"),

    DayPlanItemORM(item_id=uid(), plan_date=day_after,
                   time_start="12:00", time_end="12:30",
                   title="Lunch", item_type="break", source="manual",
                   notes="", priority="low"),

    DayPlanItemORM(item_id=uid(), plan_date=day_after,
                   time_start="12:30", time_end="14:30",
                   title="Service mesh and observability setup",
                   item_type="task", source="auto",
                   notes="API Gateway milestone. Set up Prometheus + Grafana dashboards.", priority="medium"),

    DayPlanItemORM(item_id=uid(), plan_date=day_after,
                   time_start="14:30", time_end="16:00",
                   title="dbt project structure and base models",
                   item_type="task", source="auto",
                   notes="Data Platform v3. Create staging schema and base model layer.", priority="medium"),

    DayPlanItemORM(item_id=uid(), plan_date=day_after,
                   time_start="16:00", time_end="16:45",
                   title="Security audit findings review",
                   item_type="focus", source="manual",
                   notes="Review P1/P2 vulnerability list. Assign remediation owners.", priority="high"),

    DayPlanItemORM(item_id=uid(), plan_date=day_after,
                   time_start="16:45", time_end="17:30",
                   title="Mobile beta testing — recruit 10 users",
                   item_type="task", source="auto",
                   notes="Email invite to beta group. Set up TestFlight access.", priority="medium"),
])
db.commit()

db.close()

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n✓ Seed complete:")
print("  4 applications  (EXEC · MOBILE · PORTAL · DATA)")
print("  Per-app configs: 4× Jira · 4× GitLab · 3× Sprint")
print("  7 projects  (linked to applications)")
print("  42 tasks  (6 due today · 8 overdue · 5 done today)")
print("  14 milestones  (3 overdue · 1 due today)")
print("  7 commitments  (1 due today · 2 overdue · 1 missed)")
print("  10 alerts  (2 critical · 4 warning · 4 info)")
print("  3 estimations  (story-point estimator)")
print("  3 project plans  (proj-planner: ExecOS v2.1, Mobile v1.0, Data Platform)")
print("  29 day planner items  (today + tomorrow + day-after)")
print("  2 delivery templates  (Standard · Hotfix)")
print("  4 releases  (1 in-progress · 2 planned · 1 released)")
print("\nOpen http://localhost:8080 and refresh")
print("Tip: Applications → select an app → Jira/GitLab/Sprint tabs for per-app config")
print("Tip: Click '⚡ Activate Globally' to push a config to Sprint Board / Team Workload")
print("Tip: Project Planner shows 3 seeded plans with milestones and tasks")
print("Tip: Day Planner has items for today, tomorrow, and the day after")
