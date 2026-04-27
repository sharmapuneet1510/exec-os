from .base import engine
from . import models  # noqa: F401 — ensures all ORM classes are registered


def create_all():
    models.Base.metadata.create_all(bind=engine)
    _migrate()
    print("Database tables created.")


def _migrate():
    """Add new columns to existing tables that predate them."""
    from sqlalchemy import text
    # These migrations handle both SQLite (standard ALTER TABLE) and PostgreSQL
    migrations = [
        "ALTER TABLE projects ADD COLUMN application_id TEXT",
        "ALTER TABLE tasks ADD COLUMN assignee_id TEXT",
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
