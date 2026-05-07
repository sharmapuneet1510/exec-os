from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text

from db.base import get_db, engine
from db.models import Base

router = APIRouter(prefix="/api/admin", tags=["admin"])


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
