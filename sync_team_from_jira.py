#!/usr/bin/env python3
"""Sync team members from Jira assignees."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from db.base import SessionLocal
from db.models import JiraConfigORM, AppJiraConfigORM, TeamMemberORM, ApplicationORM
import json

def sync_jira_team(app_id: str = None):
    """Create team members from all Jira assignees in an application."""
    db = SessionLocal()

    # If no app_id provided, use first available
    if not app_id:
        app = db.query(ApplicationORM).order_by(ApplicationORM.created_at).first()
        if not app:
            print("❌ No applications found")
            return
        app_id = app.application_id
        print(f"📱 Using application: {app.name} ({app_id})")

    # Get Jira config
    jira_cfg = db.query(JiraConfigORM).first()
    if not jira_cfg or not jira_cfg.enabled or not jira_cfg.pat:
        print("❌ Jira not configured")
        return

    # Get app-specific project keys
    app_jira_cfg = db.query(AppJiraConfigORM).filter(
        AppJiraConfigORM.application_id == app_id
    ).first()

    if not app_jira_cfg:
        print(f"❌ No Jira config for app {app_id}")
        return

    # Fetch Jira issues
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    keys = json.loads(app_jira_cfg.project_keys or "[]")
    if not keys:
        print("⚠️  No project keys configured for this app")
        return

    project_filter = "project in (" + ", ".join(f'"{k}"' for k in keys) + ")"
    jql = f"{project_filter} AND statusCategory != Done"

    url = f"{jira_cfg.base_url.rstrip('/')}/rest/api/2/search"

    try:
        resp = requests.get(
            url,
            params={"jql": jql, "fields": "assignee", "maxResults": 100},
            headers={
                "Authorization": f"Bearer {jira_cfg.pat}",
                "Accept": "application/json",
            },
            timeout=15,
            verify=False
        )

        if not resp.ok:
            print(f"❌ Jira error: {resp.status_code} {resp.text[:200]}")
            return

        data = resp.json()
        created = 0
        existing = 0

        for issue in data.get("issues", []):
            assignee = issue.get("fields", {}).get("assignee") or {}
            email = (assignee.get("emailAddress") or "").lower()
            name = assignee.get("displayName", "")

            if not email:
                continue

            # Check if already exists
            existing_member = db.query(TeamMemberORM).filter(
                TeamMemberORM.email == email
            ).first()

            if existing_member:
                existing += 1
            else:
                member = TeamMemberORM(
                    name=name or email.split('@')[0],
                    email=email,
                    role="Engineer",
                    is_active=True,
                    max_concurrent_tasks=8
                )
                db.add(member)
                created += 1
                print(f"✅ Created: {name} ({email})")

        db.commit()

        print(f"\n📊 Summary:")
        print(f"   Created: {created}")
        print(f"   Existing: {existing}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    app_id = sys.argv[1] if len(sys.argv) > 1 else None
    sync_jira_team(app_id)
