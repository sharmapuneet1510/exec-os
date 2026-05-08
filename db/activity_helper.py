"""Helper functions for logging entity activities."""

import json
from sqlalchemy.orm import Session
from db.models import EntityActivityLogORM


def log_activity(
    db: Session,
    entity_type: str,
    entity_id: str,
    action: str,
    description: str = "",
    details: dict = None,
):
    """Log an entity activity (create, update, delete)."""
    log = EntityActivityLogORM(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        description=description,
        details=json.dumps(details or {}),
    )
    db.add(log)
    db.commit()
    return log
