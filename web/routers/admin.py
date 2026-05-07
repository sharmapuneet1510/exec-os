"""
Admin endpoints for database management, exports, and backups.
"""
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from db.base import get_db, engine
from db.models import Base
from db import models
from backup.service import BackupService

router = APIRouter(prefix="/api/admin", tags=["admin"])

_backup_service = BackupService()


def _serialize_value(val):
    """Convert database values to JSON-serializable format."""
    if isinstance(val, datetime):
        return val.isoformat()
    elif val is None:
        return None
    elif isinstance(val, bool):
        return val
    elif isinstance(val, (int, float)):
        return val
    else:
        return str(val)


@router.get("/export")
def export_database(db: Session = Depends(get_db)):
    """Export entire database as JSON."""
    try:
        export_data = {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "tables": {}
        }

        # Get all ORM models from Base.metadata
        for table in Base.metadata.sorted_tables:
            table_name = table.name

            # Execute a raw SELECT to get all rows
            result = db.execute(text(f"SELECT * FROM {table_name}"))
            rows = result.fetchall()

            # Convert rows to dicts
            row_dicts = []
            for row in rows:
                # Get column names from the result
                row_dict = {}
                for col_name in result.keys():
                    val = getattr(row, col_name)
                    row_dict[col_name] = _serialize_value(val)
                row_dicts.append(row_dict)

            export_data["tables"][table_name] = {
                "rows": row_dicts,
                "count": len(row_dicts)
            }

        return export_data
    except Exception as e:
        raise HTTPException(500, f"Export failed: {str(e)}")


@router.post("/import")
def import_database(data: dict, db: Session = Depends(get_db)):
    """Import/restore database from JSON export."""
    try:
        # Validate structure
        if "version" not in data or "tables" not in data:
            raise HTTPException(400, "Invalid export format: missing version or tables")

        tables_restored = {}
        total_rows = 0

        # For each table in the export
        for table_name, table_data in data.get("tables", {}).items():
            if not isinstance(table_data, dict) or "rows" not in table_data:
                continue

            rows = table_data["rows"]
            if not rows:
                tables_restored[table_name] = 0
                continue

            # Find matching ORM model
            model_class = None
            for attr_name in dir(models):
                attr = getattr(models, attr_name)
                if hasattr(attr, '__tablename__') and attr.__tablename__ == table_name:
                    model_class = attr
                    break

            if not model_class:
                continue

            # Clear existing data for this table
            db.query(model_class).delete()

            # Insert rows
            inserted = 0
            for row_dict in rows:
                # Parse datetime strings back to datetime objects
                for key, val in row_dict.items():
                    if isinstance(val, str) and val and 'T' in val:
                        try:
                            row_dict[key] = datetime.fromisoformat(val)
                        except (ValueError, TypeError):
                            pass

                try:
                    obj = model_class(**row_dict)
                    db.add(obj)
                    inserted += 1
                except (IntegrityError, ValueError, TypeError) as e:
                    db.rollback()
                    continue

            db.commit()
            tables_restored[table_name] = inserted
            total_rows += inserted

        return {
            "status": "success",
            "message": f"Restored {total_rows} rows across {len(tables_restored)} tables",
            "restored_tables": tables_restored
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Import failed: {str(e)}")


@router.get("/backups/list")
def list_backups():
    """List all available backups with their metadata."""
    try:
        backup_dir = Path.home() / ".commanddesk" / "backups"
        backups = _backup_service.list_backups(backup_dir)
        return {
            "status": "success",
            "backups": [
                {
                    "id": b.backup_id,
                    "created_at": b.created_at.isoformat(),
                    "path": b.path,
                    "size_bytes": b.size_bytes,
                    "status": b.status,
                    "error": b.error,
                }
                for b in backups
            ]
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to list backups: {str(e)}")


@router.post("/backups/create")
def trigger_backup():
    """Manually trigger an immediate backup."""
    try:
        backup_dir = Path.home() / ".commanddesk" / "backups"
        manifest = _backup_service.create_backup(backup_dir)
        return {
            "status": "success",
            "message": "Backup created successfully",
            "backup": {
                "id": manifest.backup_id,
                "created_at": manifest.created_at.isoformat(),
                "path": manifest.path,
                "size_bytes": manifest.size_bytes,
                "status": manifest.status,
            }
        }
    except Exception as e:
        raise HTTPException(500, f"Backup creation failed: {str(e)}")
