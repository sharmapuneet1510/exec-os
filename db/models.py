import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Date, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.orm import relationship
from .base import Base


class EmailConfigORM(Base):
    __tablename__ = "email_config"

    id               = Column(Integer, primary_key=True, default=1)
    recipient_email  = Column(String(255), default="")
    smtp_host        = Column(String(255), default="smtp.gmail.com")
    smtp_port        = Column(Integer,     default=587)
    smtp_user        = Column(String(255), default="")
    smtp_password    = Column(Text,        default="")  # stored as plaintext; use App Password
    smtp_mode        = Column(String(20),  default="starttls")  # starttls | ssl | plain
    sod_time         = Column(String(5),   default="08:00")  # HH:MM local
    eod_time         = Column(String(5),   default="18:00")
    sod_enabled      = Column(Boolean,     default=True)
    eod_enabled      = Column(Boolean,     default=True)
    reminder_priority_filter = Column(String(20), default="all")
    created_at       = Column(DateTime,    default=datetime.utcnow)
    updated_at       = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)


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
    application_id = Column(String, nullable=True)
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
    application_id = Column(String, ForeignKey("applications.application_id", ondelete="SET NULL"), nullable=True)
    assignee_id = Column(String, ForeignKey("team_members.member_id", ondelete="SET NULL"), nullable=True)
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
    application_id = Column(String, ForeignKey("applications.application_id", ondelete="SET NULL"), nullable=True)
    due_date = Column(Date, nullable=True)
    status = Column(String(50), default="planned")
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("ProjectORM", lazy="select")


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


class ReminderORM(Base):
    __tablename__ = "reminders"

    reminder_id = Column(String, primary_key=True, default=_uuid)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    reminder_type = Column(String(20), default="independent")  # 'task' | 'independent'
    task_id = Column(String, ForeignKey("tasks.task_id", ondelete="SET NULL"), nullable=True)
    trigger_type = Column(String(20), nullable=False)  # 'fixed_time' | 'relative_interval'
    trigger_value = Column(String(50), nullable=False)  # "HH:MM" or "-1d" / "2h"
    trigger_date = Column(Date, nullable=True)  # for fixed_time reminders
    due_date = Column(Date, nullable=True)  # reference date for relative_interval
    recurrence_pattern = Column(Text, default='{}')  # JSON: {"type": "daily"} etc
    is_active = Column(Boolean, default=True)
    last_triggered = Column(DateTime, nullable=True)
    snooze_until = Column(DateTime, nullable=True)
    include_in_sod = Column(Boolean, default=True)
    include_in_eod = Column(Boolean, default=True)
    priority = Column(String(20), default="medium")  # 'low' | 'medium' | 'high'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLogORM(Base):
    __tablename__ = "audit_logs"

    log_id = Column(String, primary_key=True, default=_uuid)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String, nullable=False)
    action = Column(String(50), nullable=False)
    detail = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class JiraConfigORM(Base):
    __tablename__ = "jira_config"

    id           = Column(Integer, primary_key=True, default=1)
    base_url     = Column(String(500), default="")   # https://company.atlassian.net
    pat          = Column(Text,        default="")   # Personal Access Token (bearer auth)
    project_keys = Column(Text,        default="[]") # JSON list e.g. ["ENG","OPS"]
    enabled      = Column(Boolean,     default=False)
    last_synced  = Column(DateTime,    nullable=True)
    created_at   = Column(DateTime,    default=datetime.utcnow)
    updated_at   = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)


class GitLabConfigORM(Base):
    __tablename__ = "gitlab_config"

    id           = Column(Integer, primary_key=True, default=1)
    base_url     = Column(String(500), default="https://gitlab.com")
    access_token = Column(Text,        default="")   # Personal or project access token
    project_ids  = Column(Text,        default="[]") # JSON list of project IDs or "namespace/path"
    enabled      = Column(Boolean,     default=False)
    last_synced  = Column(DateTime,    nullable=True)
    created_at   = Column(DateTime,    default=datetime.utcnow)
    updated_at   = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)


class EstimationORM(Base):
    __tablename__ = "estimations"

    estimation_id = Column(String, primary_key=True, default=_uuid)
    title = Column(String(500), nullable=False)
    task_id = Column(String, nullable=True)
    project_id = Column(String, ForeignKey("projects.project_id", ondelete="SET NULL"), nullable=True)

    # Inputs
    story_points = Column(Integer, default=1)
    complexity = Column(String(20), default="medium")       # low / medium / high / very_high
    testing_effort = Column(String(20), default="moderate") # none / light / moderate / thorough
    has_release_paperwork = Column(Boolean, default=False)
    velocity = Column(Integer, default=2)                   # story points per working day
    start_date = Column(Date, nullable=True)
    holidays = Column(Text, default="[]")                   # JSON list of "YYYY-MM-DD" strings

    # Computed outputs (stored for history)
    dev_days = Column(Integer, default=0)
    testing_days = Column(Integer, default=0)
    paperwork_days = Column(Integer, default=0)
    holiday_buffer_days = Column(Integer, default=0)
    total_working_days = Column(Integer, default=0)
    estimated_end_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class OutlookConfigORM(Base):
    __tablename__ = "outlook_config"

    id            = Column(Integer, primary_key=True, default=1)
    ics_url       = Column(Text,    default="")       # Outlook ICS feed URL
    enabled       = Column(Boolean, default=False)
    working_start = Column(String(5), default="09:00")  # HH:MM
    working_end   = Column(String(5), default="18:00")
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ApplicationORM(Base):
    __tablename__ = "applications"

    application_id = Column(String, primary_key=True, default=_uuid)
    name           = Column(String(255), nullable=False)
    code           = Column(String(50), default="")   # short identifier e.g. "MYAPP"
    description    = Column(Text, default="")
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProjEstimateORM(Base):
    __tablename__ = "proj_estimates"

    est_id               = Column(String, primary_key=True, default=_uuid)
    name                 = Column(String(255), nullable=False)
    description          = Column(Text, default="")
    start_date           = Column(Date, nullable=True)
    end_date_constraint  = Column(Date, nullable=True)   # hard deadline
    jira_project_key     = Column(String(50), default="")
    application_id       = Column(String, nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProjEstMilestoneORM(Base):
    __tablename__ = "proj_est_milestones"

    ms_id          = Column(String, primary_key=True, default=_uuid)
    est_id         = Column(String, ForeignKey("proj_estimates.est_id", ondelete="CASCADE"), nullable=False)
    name           = Column(String(255), nullable=False)
    description    = Column(Text, default="")
    order          = Column(Integer, default=0)
    execution_type = Column(String(20), default="sequential")  # sequential | parallel
    created_at     = Column(DateTime, default=datetime.utcnow)


class ProjEstTaskORM(Base):
    __tablename__ = "proj_est_tasks"

    task_id        = Column(String, primary_key=True, default=_uuid)
    ms_id          = Column(String, ForeignKey("proj_est_milestones.ms_id", ondelete="CASCADE"), nullable=False)
    name           = Column(String(500), nullable=False)
    description    = Column(Text, default="")
    duration_days  = Column(Integer, default=1)
    execution_type = Column(String(20), default="sequential")  # sequential | parallel
    order          = Column(Integer, default=0)
    assignee       = Column(String(255), default="")
    jira_key       = Column(String(50), default="")
    created_at     = Column(DateTime, default=datetime.utcnow)


class DeliveryTemplateORM(Base):
    __tablename__ = "delivery_templates"

    template_id  = Column(String, primary_key=True, default=_uuid)
    name         = Column(String(255), nullable=False)
    description  = Column(Text, default="")
    is_default   = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DeliveryTemplateItemORM(Base):
    __tablename__ = "delivery_template_items"

    item_id          = Column(String, primary_key=True, default=_uuid)
    template_id      = Column(String, ForeignKey("delivery_templates.template_id", ondelete="CASCADE"), nullable=False)
    order            = Column(Integer, default=0)
    title            = Column(String(500), nullable=False)
    description      = Column(Text, default="")
    category         = Column(String(30), default="pre_release")  # pre_release | release | post_release
    responsible_role = Column(String(255), default="")
    is_required      = Column(Boolean, default=True)


class DeliveryReleaseORM(Base):
    __tablename__ = "delivery_releases"

    release_id       = Column(String, primary_key=True, default=_uuid)
    name             = Column(String(255), nullable=False)
    version          = Column(String(50), default="")
    project_id       = Column(String, nullable=True)
    template_id      = Column(String, nullable=True)
    release_manager  = Column(String(255), default="")
    target_date      = Column(Date, nullable=True)
    status           = Column(String(30), default="planned")  # planned|in_progress|released|rollback
    description      = Column(Text, default="")
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DeliveryReleaseItemORM(Base):
    __tablename__ = "delivery_release_items"

    item_id          = Column(String, primary_key=True, default=_uuid)
    release_id       = Column(String, ForeignKey("delivery_releases.release_id", ondelete="CASCADE"), nullable=False)
    order            = Column(Integer, default=0)
    title            = Column(String(500), nullable=False)
    description      = Column(Text, default="")
    category         = Column(String(30), default="pre_release")
    responsible_role = Column(String(255), default="")
    status           = Column(String(30), default="pending")  # pending|in_progress|done|skipped|blocked
    assignee         = Column(String(255), default="")
    notes            = Column(Text, default="")
    is_required      = Column(Boolean, default=True)
    completed_at     = Column(DateTime, nullable=True)


class SprintConfigORM(Base):
    __tablename__ = "sprint_config"

    id                 = Column(Integer, primary_key=True, default=1)
    board_id           = Column(String(100), default="")
    sprint_id          = Column(String(100), default="")
    sprint_name        = Column(String(255), default="")
    my_jira_email      = Column(String(255), default="")
    my_gitlab_username = Column(String(255), default="")
    created_at         = Column(DateTime, default=datetime.utcnow)
    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AppJiraConfigORM(Base):
    __tablename__ = "app_jira_configs"

    id             = Column(String, primary_key=True, default=_uuid)
    application_id = Column(String, nullable=False, unique=True)
    base_url       = Column(String(500), default="")
    pat            = Column(Text,        default="")   # Personal Access Token (bearer auth)
    project_keys   = Column(Text,        default="[]")
    enabled        = Column(Boolean,     default=False)
    last_synced    = Column(DateTime,    nullable=True)
    created_at     = Column(DateTime,    default=datetime.utcnow)
    updated_at     = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)


class AppGitLabConfigORM(Base):
    __tablename__ = "app_gitlab_configs"

    id             = Column(String, primary_key=True, default=_uuid)
    application_id = Column(String, nullable=False, unique=True)
    base_url       = Column(String(500), default="https://gitlab.com")
    access_token   = Column(Text, default="")
    project_ids    = Column(Text, default="[]")
    enabled        = Column(Boolean, default=False)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AppSprintConfigORM(Base):
    __tablename__ = "app_sprint_configs"

    id                 = Column(String, primary_key=True, default=_uuid)
    application_id     = Column(String, nullable=False, unique=True)
    board_id           = Column(String(100), default="")
    sprint_id          = Column(String(100), default="")
    sprint_name        = Column(String(255), default="")
    my_jira_email      = Column(String(255), default="")
    my_gitlab_username = Column(String(255), default="")
    created_at         = Column(DateTime, default=datetime.utcnow)
    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ActivityLogORM(Base):
    __tablename__ = "activity_logs"

    log_id             = Column(String, primary_key=True, default=_uuid)
    method             = Column(String(10), nullable=False)
    endpoint           = Column(String(500), nullable=False)
    status_code        = Column(Integer, default=0)
    request_headers    = Column(Text, default="{}")
    request_body       = Column(Text, nullable=True)
    response_headers   = Column(Text, default="{}")
    response_body      = Column(Text, nullable=True)
    duration_ms        = Column(Integer, default=0)
    error              = Column(Text, nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow)


class DayPlanItemORM(Base):
    __tablename__ = "day_plan_items"

    item_id      = Column(String, primary_key=True, default=_uuid)
    plan_date    = Column(Date,   nullable=False)
    time_start   = Column(String(5), nullable=False)   # HH:MM
    time_end     = Column(String(5), nullable=False)   # HH:MM
    title        = Column(String(500), nullable=False)
    item_type    = Column(String(20), default="task")  # meeting|task|break|focus
    task_id      = Column(String, ForeignKey("tasks.task_id", ondelete="SET NULL"), nullable=True)
    notes        = Column(Text, default="")
    completed    = Column(Boolean, default=False)
    source       = Column(String(50), default="manual")  # manual|auto|calendar
    priority     = Column(String(20), default="medium")
    calendar_uid = Column(String(500), nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TeamMemberORM(Base):
    __tablename__ = "team_members"

    member_id = Column(String, primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    gitlab_username = Column(String(255), nullable=True)
    role = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    max_concurrent_tasks = Column(Integer, default=8)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MockJiraIssueORM(Base):
    __tablename__ = "mock_jira_issues"

    issue_id = Column(String, primary_key=True, default=_uuid)
    key = Column(String(50), nullable=False, unique=True)
    summary = Column(String(500), nullable=False)
    assignee_email = Column(String(255), nullable=True)
    status = Column(String(50), default="To Do")
    priority = Column(String(50), default="Medium")
    project_key = Column(String(50), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MockGitLabMRORM(Base):
    __tablename__ = "mock_gitlab_mrs"

    mr_id = Column(String, primary_key=True, default=_uuid)
    iid = Column(Integer, nullable=False)
    title = Column(String(500), nullable=False)
    author_username = Column(String(255), nullable=False)
    project_path = Column(String(255), default="")
    state = Column(String(50), default="opened")
    reviewers = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    merged_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
