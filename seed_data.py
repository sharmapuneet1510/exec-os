"""Seed realistic demo data into ExecOS. Safe to re-run — clears and reloads."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, datetime, timedelta
import uuid

from db.base import SessionLocal
from db.models import (ProjectORM, TaskORM, MilestoneORM, CommitmentORM,
                       AlertORM, EstimationORM)

db = SessionLocal()

# ── Wipe existing data ────────────────────────────────────────────────────────
for model in [TaskORM, MilestoneORM, CommitmentORM, AlertORM, EstimationORM, ProjectORM]:
    db.query(model).delete()
db.commit()

today = date.today()

def d(n):  return today + timedelta(days=n)
def dt(n): return datetime.combine(today + timedelta(days=n), datetime.min.time())
def uid(): return str(uuid.uuid4())

# ── Projects ──────────────────────────────────────────────────────────────────
p1 = uid(); p2 = uid(); p3 = uid(); p4 = uid(); p5 = uid(); p6 = uid()

db.add_all([
    ProjectORM(project_id=p1, name="ExecOS Platform v2.0",
               description="Full rewrite: FastAPI backend, SQLite, Alpine.js SPA, Gantt tracker and automated email briefings.",
               status="active", owner="Puneet Sharma",
               due_date=d(21), created_at=dt(-60)),
    ProjectORM(project_id=p2, name="Mobile Companion App",
               description="React Native companion for ExecOS — push briefings, quick task updates, offline-first.",
               status="active", owner="Priya Mehta",
               due_date=d(45), created_at=dt(-30)),
    ProjectORM(project_id=p3, name="API Gateway Migration",
               description="Replace legacy REST layer with Kong gateway. Unified rate limiting, auth and observability.",
               status="active", owner="Rahul Singh",
               due_date=d(56), created_at=dt(-20)),
    ProjectORM(project_id=p4, name="Q2 OKR Programme",
               description="Track, measure and report Q2 OKRs across all engineering squads. Deadline this week.",
               status="active", owner="Puneet Sharma",
               due_date=d(7), created_at=dt(-90)),
    ProjectORM(project_id=p5, name="Infrastructure Hardening",
               description="Security audit, dependency upgrades, penetration testing and SOC 2 certification prep.",
               status="on_hold", owner="Rahul Singh",
               due_date=None, created_at=dt(-45)),
    ProjectORM(project_id=p6, name="Customer Portal Redesign",
               description="Full UX overhaul of the customer self-service portal. Shipped ahead of schedule.",
               status="completed", owner="Priya Mehta",
               due_date=d(-15), created_at=dt(-120)),
])
db.commit()

# ── Tasks ─────────────────────────────────────────────────────────────────────
db.add_all([
    # ── ExecOS Platform v2.0 ──
    TaskORM(task_id=uid(), title="Define API contracts and OpenAPI spec",
            project_id=p1, priority="high", status="done",
            due_date=d(-40), completed_at=dt(-42), created_at=dt(-60)),
    TaskORM(task_id=uid(), title="SQLite schema design and ORM models",
            project_id=p1, priority="high", status="done",
            due_date=d(-30), completed_at=dt(-31), created_at=dt(-55)),
    TaskORM(task_id=uid(), title="FastAPI backend — CRUD endpoints",
            project_id=p1, priority="high", status="done",
            due_date=d(-25), completed_at=dt(-24), created_at=dt(-50)),
    TaskORM(task_id=uid(), title="Alpine.js SPA — dashboard and task views",
            project_id=p1, priority="high", status="in_progress",
            due_date=d(7), created_at=dt(-20)),
    TaskORM(task_id=uid(), title="SOD/EOD email automation",
            project_id=p1, priority="medium", status="in_progress",
            due_date=d(5), created_at=dt(-10)),
    TaskORM(task_id=uid(), title="Project Tracker Gantt chart view",
            project_id=p1, priority="medium", status="in_progress",
            due_date=d(10), created_at=dt(-5)),
    TaskORM(task_id=uid(), title="QA testing and regression fixes",
            project_id=p1, priority="high", status="todo",
            due_date=d(16), created_at=dt(-3)),
    TaskORM(task_id=uid(), title="Production deployment and rollout",
            project_id=p1, priority="critical", status="todo",
            due_date=d(21), created_at=dt(-3)),

    # ── Mobile Companion App ──
    TaskORM(task_id=uid(), title="UX wireframes and design system",
            project_id=p2, priority="high", status="done",
            due_date=d(-20), completed_at=dt(-21), created_at=dt(-30)),
    TaskORM(task_id=uid(), title="React Native project setup and CI/CD",
            project_id=p2, priority="medium", status="done",
            due_date=d(-15), completed_at=dt(-14), created_at=dt(-28)),
    TaskORM(task_id=uid(), title="Authentication and session management",
            project_id=p2, priority="high", status="in_progress",
            due_date=d(14), created_at=dt(-12)),
    TaskORM(task_id=uid(), title="Dashboard and task list screens",
            project_id=p2, priority="medium", status="todo",
            due_date=d(28), created_at=dt(-5)),
    TaskORM(task_id=uid(), title="Push notification integration",
            project_id=p2, priority="medium", status="todo",
            due_date=d(35), created_at=dt(-3)),
    TaskORM(task_id=uid(), title="Beta testing with 10 users",
            project_id=p2, priority="high", status="todo",
            due_date=d(42), created_at=dt(-2)),

    # ── API Gateway Migration ──
    TaskORM(task_id=uid(), title="Current state API audit and documentation",
            project_id=p3, priority="medium", status="done",
            due_date=d(-10), completed_at=dt(-11), created_at=dt(-20)),
    TaskORM(task_id=uid(), title="Kong gateway configuration and policies",
            project_id=p3, priority="high", status="in_progress",
            due_date=d(10), created_at=dt(-15)),
    TaskORM(task_id=uid(), title="Service mesh and observability setup",
            project_id=p3, priority="medium", status="todo",
            due_date=d(25), created_at=dt(-5)),
    TaskORM(task_id=uid(), title="Load and performance testing",
            project_id=p3, priority="high", status="todo",
            due_date=d(40), created_at=dt(-3)),
    TaskORM(task_id=uid(), title="Cutover plan and rollback procedure",
            project_id=p3, priority="critical", status="todo",
            due_date=d(50), created_at=dt(-2)),

    # ── Q2 OKR Programme ──
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
            due_date=d(3), created_at=dt(-5)),
    TaskORM(task_id=uid(), title="All-hands Q2 retrospective session",
            project_id=p4, priority="high", status="todo",
            due_date=d(7), created_at=dt(-3)),
    TaskORM(task_id=uid(), title="Q3 OKR planning kickoff",
            project_id=p4, priority="medium", status="todo",
            due_date=d(14), created_at=dt(-2)),

    # ── Infrastructure Hardening (some overdue — project on hold) ──
    TaskORM(task_id=uid(), title="Third-party security audit",
            project_id=p5, priority="critical", status="todo",
            due_date=d(-5), created_at=dt(-45)),
    TaskORM(task_id=uid(), title="Dependency vulnerability remediation",
            project_id=p5, priority="high", status="todo",
            due_date=d(-3), created_at=dt(-30)),
    TaskORM(task_id=uid(), title="Penetration testing engagement",
            project_id=p5, priority="high", status="todo",
            due_date=d(20), created_at=dt(-15)),
    TaskORM(task_id=uid(), title="SOC 2 compliance documentation",
            project_id=p5, priority="medium", status="todo",
            due_date=None, created_at=dt(-10)),

    # ── Customer Portal Redesign (all done) ──
    TaskORM(task_id=uid(), title="Stakeholder interviews and requirements",
            project_id=p6, priority="high", status="done",
            due_date=d(-100), completed_at=dt(-102), created_at=dt(-120)),
    TaskORM(task_id=uid(), title="Design system and component library",
            project_id=p6, priority="high", status="done",
            due_date=d(-75), completed_at=dt(-73), created_at=dt(-110)),
    TaskORM(task_id=uid(), title="Frontend implementation",
            project_id=p6, priority="high", status="done",
            due_date=d(-40), completed_at=dt(-38), created_at=dt(-90)),
    TaskORM(task_id=uid(), title="UAT and bug fixes",
            project_id=p6, priority="medium", status="done",
            due_date=d(-20), completed_at=dt(-19), created_at=dt(-50)),
    TaskORM(task_id=uid(), title="Production launch",
            project_id=p6, priority="critical", status="done",
            due_date=d(-15), completed_at=dt(-15), created_at=dt(-30)),
])
db.commit()

# ── Milestones ────────────────────────────────────────────────────────────────
db.add_all([
    MilestoneORM(milestone_id=uid(), title="Alpha Release Ready",
                 project_id=p1, due_date=d(7),  status="pending",   created_at=dt(-60)),
    MilestoneORM(milestone_id=uid(), title="Production Deploy",
                 project_id=p1, due_date=d(21), status="pending",   created_at=dt(-60)),
    MilestoneORM(milestone_id=uid(), title="Design Handoff",
                 project_id=p2, due_date=d(-10),status="completed", created_at=dt(-30)),
    MilestoneORM(milestone_id=uid(), title="App Store Submission",
                 project_id=p2, due_date=d(42), status="pending",   created_at=dt(-30)),
    MilestoneORM(milestone_id=uid(), title="API Gateway Live",
                 project_id=p3, due_date=d(56), status="pending",   created_at=dt(-20)),
    MilestoneORM(milestone_id=uid(), title="Q2 Results Presentation",
                 project_id=p4, due_date=d(3),  status="pending",   created_at=dt(-90)),
    MilestoneORM(milestone_id=uid(), title="Q2 Mid-Quarter Review",
                 project_id=p4, due_date=d(-3), status="completed", created_at=dt(-90)),
    MilestoneORM(milestone_id=uid(), title="Security Certification",
                 project_id=p5, due_date=d(30), status="pending",   created_at=dt(-45)),
    MilestoneORM(milestone_id=uid(), title="Portal Go-Live",
                 project_id=p6, due_date=d(-15),status="completed", created_at=dt(-120)),
])
db.commit()

# ── Commitments ───────────────────────────────────────────────────────────────
db.add_all([
    CommitmentORM(commitment_id=uid(),
                  title="Deliver ExecOS v2.0 live demo to leadership",
                  description="Full walk-through of Gantt tracker, email briefings, and story estimator.",
                  due_date=d(14), status="pending",
                  project_id=p1, created_at=dt(-10)),
    CommitmentORM(commitment_id=uid(),
                  title="Present Q2 OKR final results at all-hands",
                  due_date=d(3),  status="pending",
                  project_id=p4, created_at=dt(-14)),
    CommitmentORM(commitment_id=uid(),
                  title="Resolve all P1 security audit findings",
                  due_date=d(7),  status="pending",
                  project_id=p5, created_at=dt(-7)),
    CommitmentORM(commitment_id=uid(),
                  title="Mobile app wireframes reviewed by design team",
                  due_date=d(-5), status="missed",
                  project_id=p2, created_at=dt(-20)),
    CommitmentORM(commitment_id=uid(),
                  title="Customer portal redesign stakeholder sign-off",
                  due_date=d(-16),status="fulfilled",
                  project_id=p6, created_at=dt(-30)),
])
db.commit()

# ── Alerts ────────────────────────────────────────────────────────────────────
db.add_all([
    AlertORM(alert_id=uid(),
             title="Infrastructure Hardening — 2 tasks critically overdue",
             message="Security audit (5d overdue) and dependency remediation (3d overdue) are blocking the SOC 2 path. Project is on hold but deadlines have passed.",
             severity="critical", source="risk-engine", is_read=False, created_at=dt(-1)),
    AlertORM(alert_id=uid(),
             title="Q2 OKR deadline in 7 days — action required",
             message="Final Q2 results deck is in progress but All-hands retro and Q3 kickoff haven't started. Risk of slipping the leadership presentation.",
             severity="warning", source="deadline-monitor", is_read=False, created_at=dt(-1)),
    AlertORM(alert_id=uid(),
             title="Mobile App — commitment missed",
             message="'Mobile app wireframes reviewed by design team' was due 5 days ago. Design review needs to be rescheduled immediately.",
             severity="warning", source="commitment-tracker", is_read=False, created_at=dt(-2)),
    AlertORM(alert_id=uid(),
             title="Customer Portal Redesign completed ahead of schedule",
             message="All 5 tasks completed. Project marked done 15 days before original deadline. Outstanding execution.",
             severity="info", source="system", is_read=True, created_at=dt(-15)),
    AlertORM(alert_id=uid(),
             title="Weekly summary — 8 tasks completed this week",
             message="8 tasks completed across 3 projects. 1 milestone hit (Q2 Mid-Quarter Review). 2 new tasks created.",
             severity="info", source="weekly-summary", is_read=True, created_at=dt(-7)),
])
db.commit()

# ── Estimations ───────────────────────────────────────────────────────────────
db.add_all([
    EstimationORM(estimation_id=uid(), title="Mobile Auth Module",
                  project_id=p2, story_points=5, complexity="medium",
                  testing_effort="thorough", has_release_paperwork=False,
                  velocity=2, start_date=d(14),
                  dev_days=3, testing_days=2, paperwork_days=0,
                  holiday_buffer_days=0, total_working_days=5,
                  estimated_end_date=d(21), created_at=dt(-5)),
    EstimationORM(estimation_id=uid(), title="API Gateway Configuration",
                  project_id=p3, story_points=8, complexity="high",
                  testing_effort="moderate", has_release_paperwork=True,
                  velocity=2, start_date=d(0),
                  dev_days=5, testing_days=3, paperwork_days=1,
                  holiday_buffer_days=0, total_working_days=9,
                  estimated_end_date=d(13), created_at=dt(-3)),
])
db.commit()
db.close()

print("✓ Seed complete:")
print(f"  6 projects · 34 tasks · 9 milestones · 5 commitments · 5 alerts · 2 estimations")
print(f"  Open http://localhost:8080 and refresh")
