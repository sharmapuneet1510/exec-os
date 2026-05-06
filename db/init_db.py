from .base import engine, SessionLocal
from . import models  # noqa: F401 — ensures all ORM classes are registered
from datetime import datetime, timedelta
import json


def create_all(populate_data=False):
    models.Base.metadata.create_all(bind=engine)
    _migrate()
    print("Database tables created.")
    if populate_data:
        _populate_dummy_data()


def _populate_dummy_data():
    """Add sample data."""
    db = SessionLocal()
    try:
        # Sample projects
        proj1 = models.ProjectORM(
            project_id="proj-website-redesign",
            name="Website Redesign",
            description="Redesign company website with new branding",
            status="active",
            owner="Product Team",
            tags=json.dumps(["frontend", "design"]),
        )
        proj2 = models.ProjectORM(
            project_id="proj-api-v2",
            name="API v2 Migration",
            description="Migrate to new REST API architecture",
            status="active",
            owner="Backend Team",
            tags=json.dumps(["backend", "api"]),
        )
        db.add_all([proj1, proj2])
        db.commit()

        # Sample tasks
        now = datetime.utcnow()
        task1 = models.TaskORM(
            task_id="task-design-mockups",
            title="Create design mockups",
            description="Design homepage and product pages",
            status="in_progress",
            priority="high",
            due_date=(now + timedelta(days=3)).date(),
            project_id="proj-website-redesign",
        )
        task2 = models.TaskORM(
            task_id="task-api-docs",
            title="Write API documentation",
            description="Document all endpoints and auth flow",
            status="todo",
            priority="medium",
            due_date=(now + timedelta(days=7)).date(),
            project_id="proj-api-v2",
        )
        task3 = models.TaskORM(
            task_id="task-testing",
            title="Integration testing",
            description="Test all critical user flows",
            status="todo",
            priority="high",
            due_date=(now + timedelta(days=5)).date(),
            project_id="proj-website-redesign",
        )
        db.add_all([task1, task2, task3])
        db.commit()

        # Sample alerts
        alert1 = models.AlertORM(
            alert_id="alert-deadline",
            title="Design mockups due soon",
            severity="warning",
            source="task_due_soon",
            is_read=False,
        )
        alert2 = models.AlertORM(
            alert_id="alert-milestone",
            title="API v2 release milestone reached",
            severity="info",
            source="milestone_completed",
            is_read=True,
        )
        db.add_all([alert1, alert2])
        db.commit()

        print("Sample data loaded.")
    except Exception as e:
        print(f"Note: Could not load sample data ({e})")
    finally:
        db.close()


def _migrate():
    """Add new columns to existing tables that predate them."""
    from sqlalchemy import text
    # These migrations handle both SQLite (standard ALTER TABLE) and PostgreSQL
    migrations = [
        "ALTER TABLE projects ADD COLUMN application_id TEXT",
        "ALTER TABLE tasks ADD COLUMN assignee_id TEXT",
        "ALTER TABLE tasks ADD COLUMN application_id TEXT",
        "ALTER TABLE estimations ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception as e:
                # column already exists or other error (e.g., can't run DDL in transaction)
                try:
                    conn.rollback()
                except Exception:
                    pass


if __name__ == "__main__":
    create_all()
