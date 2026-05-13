#!/usr/bin/env python3
"""
Migration: Add reminders table and update schema

NON-DESTRUCTIVE MIGRATION PATTERN:
All operations check IF NOT EXISTS to avoid dropping data or re-creating tables.
- Creates reminders table (if not exists) — preserves data if table already created
- Adds application_id column to releases (if not exists) — idempotent
- Adds reminder_priority_filter column to email_config (if not exists) — safe to re-run

Never delete or overwrite existing data. Always verify existence first.
"""

import sqlite3
import pathlib
import os


def get_db_path():
    """Extract SQLite database file path from DATABASE_URL or DB_PATH env var."""
    # Check for DB_PATH first (simple file path)
    db_path = os.getenv("DB_PATH")
    if db_path:
        return db_path

    # Check for DATABASE_URL (full URL)
    database_url = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{pathlib.Path.home() / '.commanddesk/execos.db'}"
    )

    # Parse SQLite URL: sqlite:////path/to/file or sqlite:///path/to/file
    if database_url.startswith("sqlite:"):
        # Remove 'sqlite:///' or 'sqlite://'
        path = database_url.replace("sqlite:///", "", 1)
        # Handle absolute paths on Unix/Mac (///path becomes /path)
        if path.startswith("/"):
            return "/" + path if not path.startswith("//") else path[1:]
        return path

    raise ValueError(f"Invalid DATABASE_URL: {database_url}")


def table_exists(conn, table_name):
    """Check if a table exists in the database."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def column_exists(conn, table_name, column_name):
    """Check if a column exists in a table.

    Note: PRAGMA table_info() does not support parameterized queries,
    so table_name is validated to contain only alphanumeric chars, _, and -.
    """
    # Validate table_name to prevent SQL injection (PRAGMA doesn't support params)
    if not all(c.isalnum() or c in ('_', '-') for c in table_name):
        raise ValueError(f"Invalid table name: {table_name}")

    cursor = conn.cursor()
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        return any(col[1] == column_name for col in columns)
    except sqlite3.OperationalError:
        return False


def run_migration():
    """Run the migration."""
    conn = None
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. Create reminders table
        if not table_exists(conn, "reminders"):
            cursor.execute("""
                CREATE TABLE reminders (
                    reminder_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    reminder_type TEXT DEFAULT 'independent',
                    task_id TEXT,
                    trigger_type TEXT NOT NULL,
                    trigger_value TEXT NOT NULL,
                    trigger_date DATE,
                    due_date DATE,
                    recurrence_pattern TEXT DEFAULT '{}',
                    is_active INTEGER DEFAULT 1,
                    last_triggered DATETIME,
                    snooze_until DATETIME,
                    include_in_sod INTEGER DEFAULT 1,
                    include_in_eod INTEGER DEFAULT 1,
                    priority TEXT DEFAULT 'medium',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE SET NULL
                )
            """)
            print("✓ Created reminders table")
        else:
            print("✓ Reminders table already exists")

        # 2. Add application_id to releases if not exists
        if table_exists(conn, "releases"):
            if not column_exists(conn, "releases", "application_id"):
                cursor.execute("""
                    ALTER TABLE releases
                    ADD COLUMN application_id TEXT
                """)
                print("✓ Added application_id column to releases")
            else:
                print("✓ application_id column already exists in releases")
        else:
            # Create releases table if it doesn't exist
            cursor.execute("""
                CREATE TABLE releases (
                    release_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT DEFAULT '',
                    project_id TEXT,
                    application_id TEXT,
                    due_date DATE,
                    status TEXT DEFAULT 'planned',
                    description TEXT DEFAULT '',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id)
                        REFERENCES projects(project_id) ON DELETE CASCADE,
                    FOREIGN KEY(application_id)
                        REFERENCES applications(application_id) ON DELETE SET NULL
                )
            """)
            print("✓ Created releases table")

        # 3. Add reminder_priority_filter to email_config if not exists
        if table_exists(conn, "email_config"):
            if not column_exists(conn, "email_config", "reminder_priority_filter"):
                cursor.execute("""
                    ALTER TABLE email_config
                    ADD COLUMN reminder_priority_filter TEXT DEFAULT 'all'
                """)
                print("✓ Added reminder_priority_filter column to email_config")
            else:
                print("✓ reminder_priority_filter column already exists in email_config")
        else:
            # Create email_config table if it doesn't exist
            cursor.execute("""
                CREATE TABLE email_config (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    recipient_email TEXT DEFAULT '',
                    smtp_host TEXT DEFAULT 'smtp.gmail.com',
                    smtp_port INTEGER DEFAULT 587,
                    smtp_user TEXT DEFAULT '',
                    smtp_password TEXT DEFAULT '',
                    smtp_mode TEXT DEFAULT 'starttls',
                    sod_time TEXT DEFAULT '08:00',
                    eod_time TEXT DEFAULT '18:00',
                    sod_enabled INTEGER DEFAULT 1,
                    eod_enabled INTEGER DEFAULT 1,
                    reminder_priority_filter TEXT DEFAULT 'all',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✓ Created email_config table")

        conn.commit()
        print("\nMigration completed successfully")
        return True

    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    success = run_migration()
    exit(0 if success else 1)
