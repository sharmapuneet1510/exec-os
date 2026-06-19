"""Setup status endpoint — onboarding checklist for first-run detection."""
from fastapi import APIRouter
from db.base import SessionLocal
from db.models import (
    JiraConfigORM, AppGitLabConfigORM, SprintConfigORM,
    ApplicationORM, EmailConfigORM,
)

router = APIRouter(prefix="/api/setup", tags=["setup"])


def _check(key: str, label: str, done: bool, action: str) -> dict:
    return {"key": key, "label": label, "done": done, "action": action}


@router.get("/status")
def setup_status():
    """Return a checklist of onboarding steps and their completion state."""
    db = SessionLocal()
    try:
        jira_cfg   = db.query(JiraConfigORM).first()
        sprint_cfg = db.query(SprintConfigORM).first()
        email_cfg  = db.query(EmailConfigORM).first()
        gl_count   = (db.query(AppGitLabConfigORM)
                        .filter(AppGitLabConfigORM.enabled == True).count())
        app_count  = (db.query(ApplicationORM)
                        .filter(ApplicationORM.status != "archived").count())

        jira_ok     = bool(jira_cfg and jira_cfg.enabled
                           and jira_cfg.base_url and jira_cfg.pat)
        gitlab_ok   = gl_count > 0
        identity_ok = bool(sprint_cfg and (
            sprint_cfg.my_jira_email or sprint_cfg.my_gitlab_username
        ))
        app_ok      = app_count > 0
        email_ok    = bool(email_cfg and email_cfg.smtp_host and email_cfg.enabled)

        checks = [
            _check("has_app",  "Create at least one Application",
                   app_ok,      "Applications → New Application"),
            _check("jira",     "Configure Jira (URL + PAT)",
                   jira_ok,     "Settings → Jira"),
            _check("gitlab",   "Configure at least one GitLab project",
                   gitlab_ok,   "Applications → [App] → Integrations → GitLab"),
            _check("identity", "Set your Jira email + GitLab username",
                   identity_ok, "Settings → Sprint Board → My Identity"),
            _check("email",    "Configure SOD/EOD email notifications",
                   email_ok,    "Settings → Email Notifications"),
        ]

        return {
            "complete":    all(c["done"] for c in checks),
            "done_count":  sum(1 for c in checks if c["done"]),
            "total_count": len(checks),
            "checks":      checks,
        }
    finally:
        db.close()
