import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Date, DateTime, ForeignKey, Boolean, Integer
from .base import Base


def _uuid():
    return str(uuid.uuid4())


class ProjectORM(Base):
    __tablename__ = "projects"

    project_id = Column(String, primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    status = Column(String(50), default="active")
    owner = Column(String(255), nullable=True)
    due_date = Column(Date, nullable=True)
    tags = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TaskORM(Base):
    __tablename__ = "tasks"

    task_id = Column(String, primary_key=True, default=_uuid)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    due_date = Column(Date, nullable=True)
    reminder_date = Column(Date, nullable=True)
    priority = Column(String(20), default="medium")
    status = Column(String(20), default="todo")
    project_id = Column(String, ForeignKey("projects.project_id", ondelete="SET NULL"), nullable=True)
    tags = Column(Text, default="[]")
    postponed_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class ReleaseORM(Base):
    __tablename__ = "releases"

    release_id = Column(String, primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    version = Column(String(50), default="")
    project_id = Column(String, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=True)
    due_date = Column(Date, nullable=True)
    status = Column(String(50), default="planned")
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MilestoneORM(Base):
    __tablename__ = "milestones"

    milestone_id = Column(String, primary_key=True, default=_uuid)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    project_id = Column(String, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=True)
    release_id = Column(String, ForeignKey("releases.release_id", ondelete="SET NULL"), nullable=True)
    due_date = Column(Date, nullable=True)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CommitmentORM(Base):
    __tablename__ = "commitments"

    commitment_id = Column(String, primary_key=True, default=_uuid)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    due_date = Column(Date, nullable=True)
    status = Column(String(50), default="pending")
    task_id = Column(String, nullable=True)
    project_id = Column(String, ForeignKey("projects.project_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlertORM(Base):
    __tablename__ = "alerts"

    alert_id = Column(String, primary_key=True, default=_uuid)
    title = Column(String(500), nullable=False)
    message = Column(Text, default="")
    severity = Column(String(20), default="info")
    source = Column(String(100), default="system")
    is_read = Column(Boolean, default=False)
    is_snoozed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    snoozed_until = Column(DateTime, nullable=True)


class AuditLogORM(Base):
    __tablename__ = "audit_logs"

    log_id = Column(String, primary_key=True, default=_uuid)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String, nullable=False)
    action = Column(String(50), nullable=False)
    detail = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
