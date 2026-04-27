#!/usr/bin/env python3
"""
Reset ExecOS database and cache to start fresh.
Deletes all data and recreates empty database on next run.
"""

import os
import shutil
from pathlib import Path


def reset_data():
    """Delete database and cache files."""
    db_dir = Path.home() / ".commanddesk"
    db_file = db_dir / "execos.db"

    if not db_file.exists():
        print(f"✓ Database not found at {db_file}")
        return

    confirm = input(f"Delete database at {db_file}? This cannot be undone. (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Cancelled.")
        return

    try:
        db_file.unlink()
        print(f"✓ Deleted {db_file}")
        print("✓ Database will be recreated on next run")
    except Exception as e:
        print(f"✗ Error deleting database: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(reset_data())
