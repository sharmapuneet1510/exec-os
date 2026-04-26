"""
Comprehensive seed data for ExecOS.
Covers: Projects · Tasks · Milestones · Commitments · Alerts · Estimations · Day Planner
Safe to re-run — clears and reloads everything.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, datetime, timedelta
import uuid

from db.base import SessionLocal
from db.init_db import create_all
from db.models import (
    ProjectORM, TaskORM, MilestoneORM, CommitmentORM,
    AlertORM, EstimationORM, DayPlanItemORM,
)

create_all()   # ensure new tables exist
db = SessionLocal()

# ── Wipe ──────────────────────────────────────────────────────────────────────
for model in [DayPlanItemORM, TaskORM, MilestoneORM, CommitmentORM,
              AlertORM, EstimationORM, ProjectORM]:
    db.query(model).delete()
db.commit()

today = date.today()
now   = datetime.utcnow()

def d(n):    return today + timedelta(days=n)
def dt(n):   return datetime.combine(today + timedelta(days=n), datetime.min.time())
def uid():   return str(uuid.uuid4())
def hm(h,m): return f"{h:02d}:{m:02d}"

# ── Projects ──────────────────────────────────────────────────────────────────
p1 = uid(); p2 = uid(); p3 = uid()
p4 = uid(); p5 = uid(); p6 = uid(); p7 = uid()

db.add_all([
    ProjectORM(project_id=p1, name="ExecOS Platform v2.0",
               description="FastAPI backend, SQLite, Alpine.js SPA — Gantt, estimator, integrations.",
               status="active", owner="Puneet Sharma",
               due_date=d(14), created_at=dt(-60)),

    ProjectORM(project_id=p2, name="Mobile Companion App",
               description="React Native app for ExecOS — push briefings, offline task updates.",
               status="active", owner="Priya Mehta",
               due_date=d(45), created_at=dt(-30)),

    ProjectORM(project_id=p3, name="API Gateway Migration",
               description="Replace legacy REST layer with Kong. Unified rate-limiting, auth, observability.",
               status="active", owner="Rahul Singh",
               due_date=d(30), created_at=dt(-20)),

    ProjectORM(project_id=p4, name="Q2 OKR Programme",
               description="Track, measure and report Q2 OKRs across all squads. Board presentation due soon.",
               status="active", owner="Puneet Sharma",
               due_date=d(5), created_at=dt(-90)),

    ProjectORM(project_id=p5, name="Infrastructure Hardening",
               description="Security audit, dependency upgrades, penetration testing, SOC 2 prep.",
               status="on_hold", owner="Rahul Singh",
               due_date=None, created_at=dt(-45)),

    ProjectORM(project_id=p6, name="Customer Portal Redesign",
               description="Full UX overhaul of the self-service portal. Shipped ahead of schedule.",
               status="completed", owner="Priya Mehta",
               due_date=d(-15), created_at=dt(-120)),

    ProjectORM(project_id=p7, name="Data Platform v3",
               description="Migrate analytics pipelines from Redshift to Databricks. Implement dbt models.",
               status="active", owner="Ananya Iyer",
               due_date=d(60), created_at=dt(-10)),
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
                  estimated_end_date=d(7), created_at=dt(-5)),

    EstimationORM(estimation_id=uid(), title="Kong Gateway Configuration",
                  project_id=p3, story_points=8, complexity="high",
                  testing_effort="moderate", has_release_paperwork=True,
                  velocity=2, start_date=d(0),
                  dev_days=5, testing_days=3, paperwork_days=1,
                  holiday_buffer_days=1, total_working_days=10,
                  estimated_end_date=d(12), created_at=dt(-3)),

    EstimationORM(estimation_id=uid(), title="Databricks Migration Scripts",
                  project_id=p7, story_points=13, complexity="very_high",
                  testing_effort="thorough", has_release_paperwork=True,
                  velocity=2, start_date=d(3),
                  dev_days=8, testing_days=4, paperwork_days=2,
                  holiday_buffer_days=1, total_working_days=15,
                  estimated_end_date=d(21), created_at=dt(-2)),
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

db.close()

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n✓ Seed complete:")
print("  7 projects")
print("  42 tasks  (6 due today · 8 overdue · 5 done today)")
print("  14 milestones  (3 overdue · 1 due today)")
print("  7 commitments  (1 due today · 2 overdue · 1 missed)")
print("  10 alerts  (2 critical · 4 warning · 4 info)")
print("  3 estimations")
print("  11 day planner items for today (3 meetings · 5 tasks · 2 focus/breaks)")
print("\nOpen http://localhost:8080 and refresh")
print("Tip: go to Alerts → ⚡ Scan Now to trigger the auto-alert engine")
print("Tip: go to Day Planner to see today's schedule")
