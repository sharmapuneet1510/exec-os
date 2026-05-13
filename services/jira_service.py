"""Jira integration service — fetch sprints, issues, and create team members."""

import requests
import json
from typing import Optional, List, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from db.models import AppJiraConfigORM, TeamMemberORM


class JiraService:
    def __init__(self, base_url: str, pat: str):
        self.base_url = base_url.rstrip("/")
        self.pat = pat
        self.headers = {
            "Authorization": f"Bearer {pat}",
            "Content-Type": "application/json"
        }

    def get_sprints(self, project_key: str) -> List[Dict]:
        """Fetch sprints for a Jira project."""
        try:
            url = f"{self.base_url}/rest/api/3/board"
            resp = requests.get(url, headers=self.headers, params={"projectKeyOrId": project_key})
            resp.raise_for_status()
            boards = resp.json().get("values", [])

            sprints = []
            for board in boards:
                board_id = board.get("id")
                sprint_url = f"{self.base_url}/rest/api/3/board/{board_id}/sprint"
                sprint_resp = requests.get(sprint_url, headers=self.headers)
                if sprint_resp.status_code == 200:
                    sprint_data = sprint_resp.json().get("values", [])
                    sprints.extend(sprint_data)

            return sprints
        except Exception as e:
            print(f"Error fetching sprints: {e}")
            return []

    def get_sprint_issues(self, project_key: str, sprint_id: int) -> List[Dict]:
        """Fetch issues in a sprint."""
        try:
            url = f"{self.base_url}/rest/api/3/search"
            jql = f'project="{project_key}" AND sprint={sprint_id}'
            resp = requests.get(
                url,
                headers=self.headers,
                params={"jql": jql, "maxResults": 100, "expand": "changelog"}
            )
            resp.raise_for_status()
            return resp.json().get("issues", [])
        except Exception as e:
            print(f"Error fetching sprint issues: {e}")
            return []

    def extract_members_from_issues(self, issues: List[Dict]) -> List[Dict]:
        """Extract reporter and assignee from issues."""
        members = {}

        for issue in issues:
            fields = issue.get("fields", {})

            # Reporter
            reporter = fields.get("reporter", {})
            if reporter and reporter.get("emailAddress"):
                email = reporter["emailAddress"].lower()
                if email not in members:
                    members[email] = {
                        "email": email,
                        "name": reporter.get("displayName", email),
                        "role": "reporter"
                    }

            # Assignee
            assignee = fields.get("assignee", {})
            if assignee and assignee.get("emailAddress"):
                email = assignee["emailAddress"].lower()
                if email not in members:
                    members[email] = {
                        "email": email,
                        "name": assignee.get("displayName", email),
                        "role": "assignee"
                    }

        return list(members.values())

    def sync_members_to_db(self, members_data: List[Dict], db: Session):
        """Create or update team members from Jira data."""
        created = []
        existing = []

        for member_info in members_data:
            email = member_info["email"].lower()

            # Check if member already exists
            existing_member = db.query(TeamMemberORM).filter(
                TeamMemberORM.email == email
            ).first()

            if existing_member:
                existing.append(existing_member)
            else:
                new_member = TeamMemberORM(
                    name=member_info["name"],
                    email=email,
                    role=member_info.get("role", ""),
                    is_team_member=False,  # Requires manual approval
                    is_active=True
                )
                db.add(new_member)
                created.append(new_member)

        if created:
            db.commit()

        return {"created": len(created), "existing": len(existing), "members": created + existing}


def get_jira_service(app_id: str, db: Session) -> Optional[JiraService]:
    """Get configured Jira service for an application."""
    config = db.query(AppJiraConfigORM).filter(
        AppJiraConfigORM.application_id == app_id
    ).first()

    if not config or not config.enabled or not config.base_url or not config.pat:
        return None

    return JiraService(config.base_url, config.pat)
