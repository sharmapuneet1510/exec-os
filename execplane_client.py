"""
ExecPlane Agent Client  v4.2.0
==============================
Python mediator between AI agents and the ExecPlane execution mesh API.
Agents MUST use this client - do not derive API logic independently.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY STARTUP - run these three lines before ANY work:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    client.login(email, password)
    info = client.check_version()          # always check on startup
    if info["needs_update"]:
        client.download_latest_client()    # auto-update then restart
        raise SystemExit("Restarting with updated client")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY COMMENT POINTS - post a comment at every step:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. AFTER CLAIM     - state your plan ("I will implement X by doing Y")
  2. MID-WORK        - progress update ("50% done - migration added, endpoint WIP")
  3. ON BLOCKED      - explain blocker ("BLOCKED: need clarification on field Z")
  4. ON COMPLETE     - summary ("Done: added migration, endpoint, tests. Files: a.py b.py")
  5. ON FAILURE      - detail failures ("FAILED: test_login fails - see attached log")
  6. AFTER DEPLOY    - deploy result ("DEPLOYED: build succeeded. Containers restarted.")

  Use: client.add_comment(item_id, item_type, message)
  Humans watch comments - they are the primary audit trail.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY AFTER DEV_DONE - deploy and restart before QA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  result = client.deploy_and_restart("bash deploy.sh", working_dir="/path/to/project")
  client.add_comment(item_id, item_type,
      f"[DEPLOYED] {'OK' if result['success'] else 'FAILED'}\n{result['output'][-500:]}")
  if not result["success"]:
      raise SystemExit("Deploy failed - fix before marking dev_done")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY CLAUDE.MD UPDATE - after every completed task:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Call client.update_claude_md(item_id, item_type, summary, files_changed)
  This keeps the project memory current for other agents and humans.

Download latest client:
    curl -O http://localhost:8000/api/client/download
    # or
    client.download_latest_client()
"""

import sys
import os
import json
import textwrap
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

try:
    import requests
except ImportError:
    sys.exit("ExecPlane client requires 'requests'. Install with: pip install requests")

CLIENT_VERSION = "4.2.0"

# ── Unified 16-state item transitions (applies to stories, tasks, and bugs) ───
ITEM_TRANSITIONS: Dict[str, List[str]] = {
    "created":             ["under_review", "closed"],
    "under_review":        ["approved", "needs_clarification", "closed"],
    "needs_clarification": ["under_review", "created"],
    "approved":            ["ready_for_execution", "needs_clarification"],
    "ready_for_execution": ["dev_claimed", "approved"],
    "dev_claimed":         ["in_progress", "ready_for_execution"],
    "in_progress":         ["dev_done", "dev_claimed"],
    "dev_done":            ["ready_for_qa", "in_progress"],
    "ready_for_qa":        ["qa_claimed", "in_progress"],
    "qa_claimed":          ["under_testing", "ready_for_qa"],
    "under_testing":       ["test_passed", "test_failed"],
    "test_passed":         ["completed"],
    "test_failed":         ["reopened", "in_progress"],
    "completed":           ["closed", "reopened"],
    "closed":              ["reopened"],
    "reopened":            ["ready_for_execution", "in_progress"],
}

# Aliases kept for backward compatibility
STORY_TRANSITIONS = ITEM_TRANSITIONS
TASK_TRANSITIONS  = ITEM_TRANSITIONS
BUG_TRANSITIONS   = ITEM_TRANSITIONS

# ── Function catalogue (used by help()) ───────────────────────────────────────
_FUNCTIONS = [
    # Auth
    ("login",                  "login(email, password)",
     "Authenticate and store JWT token for all subsequent calls."),
    ("check_version",          "check_version()",
     "Compare local client version against the server. Prints update notice if outdated."),
    ("download_latest_client", "download_latest_client(save_as='execplane_client.py')",
     "Download the latest client file from the server and save it locally."),
    ("help",                   "help()",
     "Print this function reference."),

    # Projects
    ("list_projects",          "list_projects()",
     "List all projects accessible to this agent."),
    ("get_project",            "get_project(project_id)",
     "Get full details of a single project."),

    # Epics
    ("list_epics",             "list_epics(project_id)",
     "List all epics in a project."),
    ("get_epic",               "get_epic(epic_id)",
     "Get full details of an epic."),

    # Stories
    ("list_stories",           "list_stories(project_id, epic_id=None, status=None, limit=50)",
     "List stories, optionally filtered by epic or status."),
    ("get_story",              "get_story(story_id)",
     "Get full details of a story including technical translation if available."),

    # Tasks
    ("list_tasks",             "list_tasks(project_id=None, story_id=None, status=None, limit=50)",
     "List tasks, optionally filtered by project, story or status."),
    ("get_task",               "get_task(task_id)",
     "Get full details of a task."),

    # Bugs
    ("list_bugs",              "list_bugs(project_id=None, status=None, limit=50)",
     "List bugs, optionally filtered by project or status."),
    ("get_bug",                "get_bug(bug_id)",
     "Get full details of a bug."),

    # Work claiming  (REQUIRED before doing any work)
    ("get_next_work_item",     "get_next_work_item(project_id, role=None)",
     "Ask the mesh for the next recommended work item. "
     "role='dev' filters to implementation tasks; role='qa' filters to test_plan tasks. "
     "Omit role to get the next item regardless of type."),
    ("list_tasks_by_role",     "list_tasks_by_role(project_id, role, status=None, limit=50)",
     "List tasks filtered by role. role='dev' returns non-test-plan tasks; "
     "role='qa' returns tasks whose title starts with 'Test Plan:'. "
     "Optionally filter by status."),
    ("claim_work_item",        "claim_work_item(work_item_id, work_item_type, role=None)",
     "Claim exclusive ownership of a work item. MUST be called before starting work. "
     "role='dev' → dev_claimed, role='qa' → qa_claimed, role=None → auto from status. "
     "work_item_type: story | task | bug"),
    ("get_current_claim",      "get_current_claim()",
     "Return the agent's currently active claim, or None."),
    ("release_work_item",      "release_work_item(work_item_id, work_item_type, reason=None)",
     "Release a claimed work item (done, blocked, or handing off)."),

    # Status transitions
    ("transition_story",       "transition_story(story_id, new_status)",
     f"Move a story to a new status. Valid transitions: {json.dumps(STORY_TRANSITIONS, indent=2)}"),
    ("transition_task",        "transition_task(task_id, new_status)",
     f"Move a task to a new status. Valid transitions: {json.dumps(TASK_TRANSITIONS, indent=2)}"),
    ("transition_bug",         "transition_bug(bug_id, new_status)",
     f"Move a bug to a new status. Valid transitions: {json.dumps(BUG_TRANSITIONS, indent=2)}"),

    # Work logging
    ("add_worklog",            "add_worklog(work_item_id, work_item_type, description, started_at, ended_at=None)",
     "Log work done on an item. description = plain-language summary of what was done (not code). "
     "started_at / ended_at = ISO-8601 datetime strings. work_item_type: epic | story | task | bug"),
    ("list_worklogs",          "list_worklogs(work_item_id, work_item_type)",
     "Return all work log entries for an item."),

    # Comments - MANDATORY at claim, mid-work, completion, failure
    ("add_comment",            "add_comment(work_item_id, work_item_type, content, is_internal=False)",
     "MANDATORY: Post a comment at claim, mid-work, completion, and failure. "
     "is_internal=False (default) = visible to humans. "
     "is_internal=True = agent-only debug note."),
    ("list_comments",          "list_comments(work_item_id, work_item_type)",
     "Return all comments on an item."),

    # CLAUDE.md update - MANDATORY after every completed task
    ("update_claude_md",       "update_claude_md(item_id, item_type, summary, files_changed=None, claude_md_path='CLAUDE.md')",
     "MANDATORY after every completed task: appends a completion record to CLAUDE.md "
     "so the project memory stays current for other agents and humans. "
     "files_changed: list of file paths modified. claude_md_path: path to CLAUDE.md (default: './CLAUDE.md')."),

    # Attachments
    ("upload_attachment",      "upload_attachment(work_item_id, work_item_type, file_path, attachment_type=None)",
     "Upload a file to MinIO and attach it to a work item. "
     "attachment_type: 'requirement' | 'test_evidence' | 'screenshot' | None"),
    ("list_attachments",       "list_attachments(work_item_id, work_item_type)",
     "Return all attachments for a work item."),
    ("get_attachment_url",     "get_attachment_url(attachment_id)",
     "Return a pre-signed download URL for an attachment (valid ~1 hour)."),

    # Progress reporting
    ("send_heartbeat",         "send_heartbeat(claim_id, message, progress_pct=None)",
     "Report live progress on a claimed item. Call periodically (every 30-60 s) while working. "
     "progress_pct: 0-100."),

    # Plan & completion
    ("create_plan",            "create_plan(work_item_id, work_item_type, content)",
     "Submit an execution plan AND automatically post it as a visible comment. "
     "content: human-readable design — what you will build, how, edge cases. "
     "This is the DESIGN COMMENT humans review before you write code."),
    ("complete_work",          "complete_work(work_item_id, work_item_type, summary, outcome='completed')",
     "Mark a claimed item as finished AND post summary as a visible comment. "
     "outcome: completed | partial | blocked. "
     "summary = what was done, files changed, decisions made."),

    # Deploy & test (MANDATORY after dev_done)
    ("deploy_and_restart",     "deploy_and_restart(deploy_command='bash deploy.sh', working_dir=None, timeout=600)",
     "MANDATORY after dev_done: run the deploy script and restart containers. "
     "Returns {'success': bool, 'output': str, 'returncode': int}. "
     "Post the result as a [DEPLOYED] comment. If success=False, do NOT mark dev_done — fix first."),
    ("run_playwright_tests",   "run_playwright_tests(test_command='npx playwright test', working_dir=None, timeout=300)",
     "Run Playwright end-to-end tests and return {'success': bool, 'output': str, 'returncode': int}. "
     "Post output as [PLAYWRIGHT] comment. QA agents: run this after deploy to verify the feature."),
]


class ExecPlaneClientError(Exception):
    """Raised when the API returns an error."""
    pass


class ExecPlaneClient:
    """
    Mediator between AI agents and the ExecPlane execution mesh.

    Agents must NOT call the API directly. All interactions go through
    this client to ensure correct protocol, version compatibility, and
    proper work-claiming semantics.

    Workflow:
        1. client.login(email, password)
        2. client.check_version()           # update if prompted
        3. item = client.get_next_work_item(project_id)
        4. claim = client.claim_work_item(item['id'], item['type'])
        5. client.create_plan(item['id'], item['type'], "My plan...")
        6. client.transition_story/task/bug(item['id'], 'in_progress')
        7. ... do work, call send_heartbeat() every ~60s ...
        8. client.add_worklog(item['id'], item['type'], "What I did", started, ended)
        9. client.transition_story/task/bug(item['id'], 'done')
       10. client.complete_work(item['id'], item['type'], "Summary")
       11. client.release_work_item(item['id'], item['type'])
    """

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        auto_check_version: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self._token = token
        self._session = requests.Session()
        if token:
            self._session.headers.update({"Authorization": f"Bearer {token}"})
        if auto_check_version and token:
            self._silent_version_check()

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _auth_headers(self) -> dict:
        if not self._token:
            raise ExecPlaneClientError("Not authenticated. Call client.login(email, password) first.")
        return {"Authorization": f"Bearer {self._token}"}

    def _get(self, path: str, params: dict = None) -> Any:
        r = self._session.get(f"{self.base_url}{path}", params=params,
                              headers=self._auth_headers())
        self._raise_for_status(r)
        return r.json()

    def _post(self, path: str, data: dict = None, params: dict = None) -> Any:
        r = self._session.post(f"{self.base_url}{path}", json=data, params=params,
                               headers=self._auth_headers())
        self._raise_for_status(r)
        return r.json()

    def _patch(self, path: str, data: dict = None) -> Any:
        r = self._session.patch(f"{self.base_url}{path}", json=data,
                                headers=self._auth_headers())
        self._raise_for_status(r)
        return r.json()

    @staticmethod
    def _raise_for_status(r: requests.Response):
        if not r.ok:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text
            raise ExecPlaneClientError(f"API error {r.status_code}: {detail}")

    def _silent_version_check(self):
        try:
            info = self._version_info(CLIENT_VERSION)
            if info.get("needs_update"):
                print(
                    f"[ExecPlane] ⚠  Client update available: {CLIENT_VERSION} → "
                    f"{info['latest_version']}. Run client.download_latest_client() to update."
                )
        except Exception:
            pass

    # ── Auth ──────────────────────────────────────────────────────────────────

    def login(self, email: str, password: str) -> str:
        """Authenticate. Returns and stores the JWT token."""
        r = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"email": email, "password": password},
        )
        self._raise_for_status(r)
        token = r.json()["access_token"]
        self._token = token
        self._session.headers.update({"Authorization": f"Bearer {token}"})
        self._silent_version_check()
        return token

    # ── Version ───────────────────────────────────────────────────────────────

    def _version_info(self, client_version: str = CLIENT_VERSION) -> dict:
        r = requests.get(
            f"{self.base_url}/api/client/version",
            params={"client_version": client_version},
        )
        self._raise_for_status(r)
        return r.json()

    def check_version(self) -> dict:
        """
        Check whether this client is up to date.
        Prints a message and returns version info dict.
        """
        info = self._version_info(CLIENT_VERSION)
        if info["needs_update"]:
            print(
                f"[ExecPlane] ⚠  Update available!\n"
                f"  Current : {CLIENT_VERSION}\n"
                f"  Latest  : {info['latest_version']}\n"
                f"  Run     : client.download_latest_client()\n"
                f"  Or      : curl -O {self.base_url}{info['download_url']}"
            )
        else:
            print(f"[ExecPlane] ✓ Client {CLIENT_VERSION} is up to date.")
        return info

    def download_latest_client(self, save_as: str = "execplane_client.py") -> str:
        """Download the latest client file and save it locally."""
        r = requests.get(f"{self.base_url}/api/client/download")
        self._raise_for_status(r)
        with open(save_as, "wb") as f:
            f.write(r.content)
        print(f"[ExecPlane] ✓ Latest client saved to '{save_as}'. Restart your script to use it.")
        return save_as

    # ── Help ──────────────────────────────────────────────────────────────────

    def help(self, search: str = None):
        """
        Print all available functions with signatures and descriptions.
        Pass search= to filter by keyword.
        """
        funcs = _FUNCTIONS
        if search:
            funcs = [f for f in funcs if search.lower() in f[0].lower() or search.lower() in f[2].lower()]

        print(f"\n{'═'*70}")
        print(f"  ExecPlane Agent Client  v{CLIENT_VERSION}")
        print(f"{'═'*70}")
        if search:
            print(f"  Showing results for: '{search}'\n")

        for _, sig, desc in funcs:
            print(f"\n  client.{sig}")
            for line in textwrap.wrap(desc, width=64):
                print(f"      {line}")
        print(f"\n{'═'*70}\n")

    # ── Projects ──────────────────────────────────────────────────────────────

    def list_projects(self) -> List[dict]:
        """List all projects accessible to this agent."""
        return self._get("/api/projects")

    def get_project(self, project_id: str) -> dict:
        """Get full details of a single project."""
        return self._get(f"/api/projects/{project_id}")

    # ── Epics ─────────────────────────────────────────────────────────────────

    def list_epics(self, project_id: str) -> List[dict]:
        """List all epics in a project."""
        return self._get("/api/epics", params={"project_id": project_id})

    def get_epic(self, epic_id: str) -> dict:
        """Get full details of an epic."""
        return self._get(f"/api/epics/{epic_id}")

    # ── Stories ───────────────────────────────────────────────────────────────

    def list_stories(
        self,
        project_id: str,
        epic_id: str = None,
        status: str = None,
        limit: int = 50,
    ) -> List[dict]:
        """List stories filtered by project, optional epic or status."""
        params = {"project_id": project_id, "limit": limit}
        if epic_id:
            params["epic_id"] = epic_id
        if status:
            params["status"] = status
        return self._get("/api/stories", params=params)

    def get_story(self, story_id: str) -> dict:
        """Get full story details including technical translation if available."""
        return self._get(f"/api/stories/{story_id}")

    # ── Tasks ─────────────────────────────────────────────────────────────────

    def list_tasks(
        self,
        project_id: str = None,
        story_id: str = None,
        status: str = None,
        limit: int = 50,
    ) -> List[dict]:
        """List tasks filtered by project, story, or status."""
        params: dict = {"limit": limit}
        if project_id:
            params["project_id"] = project_id
        if story_id:
            params["story_id"] = story_id
        if status:
            params["status"] = status
        return self._get("/api/tasks", params=params)

    def get_task(self, task_id: str) -> dict:
        """Get full details of a task."""
        return self._get(f"/api/tasks/{task_id}")

    # ── Bugs ──────────────────────────────────────────────────────────────────

    def list_bugs(
        self,
        project_id: str = None,
        status: str = None,
        limit: int = 50,
    ) -> List[dict]:
        """List bugs filtered by project or status."""
        params: dict = {"limit": limit}
        if project_id:
            params["project_id"] = project_id
        if status:
            params["status"] = status
        return self._get("/api/bugs", params=params)

    def get_bug(self, bug_id: str) -> dict:
        """Get full details of a bug."""
        return self._get(f"/api/bugs/{bug_id}")

    # ── Work claiming ─────────────────────────────────────────────────────────

    def get_next_work_item(self, project_id: str, role: Optional[str] = None) -> dict:
        """
        Ask the mesh for the next recommended work item for this agent.
        Returns item details with type, id, title, status, priority.
        Returns empty dict if nothing is queued.

        role='dev'  - only returns implementation tasks (not test plans)
        role='qa'   - only returns tasks whose title starts with 'Test Plan:'
        role=None   - next item regardless of type
        """
        params: dict = {"project_id": project_id}
        if role:
            params["role"] = role
        return self._get("/api/agent/work-items/next", params=params)

    def list_tasks_by_role(
        self,
        project_id: str,
        role: str,
        status: str = None,
        limit: int = 50,
    ) -> List[dict]:
        """
        List tasks filtered by agent role.

        role='dev'  - implementation tasks (excludes titles starting with 'Test Plan:')
        role='qa'   - test plan tasks (titles starting with 'Test Plan:')
        """
        all_tasks = self.list_tasks(project_id=project_id, status=status, limit=limit)
        if role == "qa":
            return [t for t in all_tasks if t.get("title", "").startswith("Test Plan:")]
        elif role == "dev":
            return [t for t in all_tasks if not t.get("title", "").startswith("Test Plan:")]
        return all_tasks

    def claim_work_item(
        self,
        work_item_id: str,
        work_item_type: str,
        role: Optional[str] = None,
    ) -> dict:
        """
        Claim exclusive ownership of a work item.
        MUST be called before starting any work.
        work_item_type: story | task | bug
        role: 'dev' → transitions to dev_claimed
              'qa'  → transitions to qa_claimed
              None  → auto-detected from current status
        """
        return self._post(
            f"/api/agent/work-items/{work_item_id}/claim",
            data={"role": role} if role else {},
            params={"work_item_type": work_item_type},
        )

    def get_current_claim(self) -> Optional[dict]:
        """Return this agent's currently active claim, or None."""
        return self._get("/api/agent/work-items/current")

    def release_work_item(
        self,
        work_item_id: str,
        work_item_type: str,
        reason: str = None,
    ) -> dict:
        """
        Release a claimed work item.
        Call after completing, getting blocked, or handing off.
        """
        return self._post(
            f"/api/agent/work-items/{work_item_id}/release",
            data={"reason": reason},
            params={"work_item_type": work_item_type},
        )

    # ── Status transitions ────────────────────────────────────────────────────

    def _validate_transition(self, transitions: dict, current: str, new_status: str, item_type: str):
        allowed = transitions.get(current, [])
        if new_status not in allowed:
            raise ExecPlaneClientError(
                f"Invalid {item_type} transition: '{current}' → '{new_status}'. "
                f"Allowed from '{current}': {allowed}"
            )

    def transition_story(self, story_id: str, new_status: str) -> dict:
        """
        Move a story to a new status.
        Client validates the transition before sending to the API.
        """
        story = self.get_story(story_id)
        self._validate_transition(ITEM_TRANSITIONS, story["status"], new_status, "story")
        return self._post(f"/api/stories/{story_id}/status", data={"status": new_status})

    def transition_task(self, task_id: str, new_status: str) -> dict:
        """Move a task to a new status."""
        task = self.get_task(task_id)
        self._validate_transition(ITEM_TRANSITIONS, task["status"], new_status, "task")
        return self._post(f"/api/tasks/{task_id}/status", data={"status": new_status})

    def transition_bug(self, bug_id: str, new_status: str) -> dict:
        """Move a bug to a new status."""
        bug = self.get_bug(bug_id)
        self._validate_transition(ITEM_TRANSITIONS, bug["status"], new_status, "bug")
        return self._post(f"/api/bugs/{bug_id}/status", data={"status": new_status})

    # ── Work logging ──────────────────────────────────────────────────────────

    def add_worklog(
        self,
        work_item_id: str,
        work_item_type: str,
        description: str,
        started_at: str,
        ended_at: str = None,
    ) -> dict:
        """
        Log what was done on a work item.
        description: plain-language summary (NOT code - what was accomplished).
        started_at / ended_at: ISO-8601 datetime strings
            e.g. datetime.now(timezone.utc).isoformat()
        work_item_type: epic | story | task | bug
        """
        if not ended_at:
            ended_at = datetime.now(timezone.utc).isoformat()
        return self._post("/api/worklogs", data={
            "work_item_id": work_item_id,
            "work_item_type": work_item_type,
            "description": description,
            "started_at": started_at,
            "ended_at": ended_at,
        })

    def list_worklogs(self, work_item_id: str, work_item_type: str) -> List[dict]:
        """Return all work log entries for a work item."""
        return self._get("/api/worklogs", params={
            "work_item_id": work_item_id,
            "work_item_type": work_item_type,
        })

    # ── Comments ──────────────────────────────────────────────────────────────

    def add_comment(
        self,
        work_item_id: str,
        work_item_type: str,
        content: str,
        is_internal: bool = False,
    ) -> dict:
        """
        Post a comment on any work item.
        is_internal=True marks the comment as agent-only (not visible to humans by default).
        """
        return self._post("/api/comments", data={
            "work_item_id": work_item_id,
            "work_item_type": work_item_type,
            "content": content,
            "is_internal": is_internal,
        })

    def list_comments(self, work_item_id: str, work_item_type: str) -> List[dict]:
        """Return all comments on a work item."""
        return self._get("/api/comments", params={
            "work_item_id": work_item_id,
            "work_item_type": work_item_type,
        })

    def update_claude_md(
        self,
        item_id: str,
        item_type: str,
        summary: str,
        files_changed: Optional[List[str]] = None,
        claude_md_path: str = "CLAUDE.md",
    ) -> None:
        """
        MANDATORY after every completed task.
        Appends a completion record to CLAUDE.md so the project memory
        stays current for other agents and humans.

        item_id        : UUID of the completed work item
        item_type      : story | task | bug
        summary        : plain-English summary of what was done
        files_changed  : list of file paths that were modified/created
        claude_md_path : path to CLAUDE.md (default: './CLAUDE.md')

        Example:
            client.update_claude_md(
                item["id"], item["type"],
                "Implemented POST /api/orders endpoint with validation and DB persistence.",
                files_changed=["backend/app/orders/router.py", "backend/app/orders/service.py",
                               "backend/alembic/versions/0011_orders.py"],
            )
        """
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        files_str = ""
        if files_changed:
            files_str = "\n" + "\n".join(f"  - {f}" for f in files_changed)

        entry = (
            f"\n- [{now}] [{item_type.upper()} {item_id[:8]}] {summary}"
            f"{files_str}"
        )

        try:
            if os.path.exists(claude_md_path):
                with open(claude_md_path, "r", encoding="utf-8") as fh:
                    content = fh.read()
            else:
                content = "# Project Memory\n\n## Agent Activity Log\n"

            # Find or create the Agent Activity Log section
            if "## Agent Activity Log" not in content:
                content += "\n\n## Agent Activity Log\n"

            content += entry
            with open(claude_md_path, "w", encoding="utf-8") as fh:
                fh.write(content)
            print(f"[ExecPlane] ✓ CLAUDE.md updated ({claude_md_path})")
        except Exception as exc:
            print(f"[ExecPlane] ⚠  Could not update CLAUDE.md: {exc}")

    # ── Attachments ───────────────────────────────────────────────────────────

    def upload_attachment(
        self,
        work_item_id: str,
        work_item_type: str,
        file_path: str,
        attachment_type: Optional[str] = None,
    ) -> dict:
        """
        Upload a local file to MinIO and attach it to a work item.
        file_path: absolute or relative path to the file on disk.
        attachment_type: 'requirement' | 'test_evidence' | 'screenshot' | None
        Returns the created Attachment record.
        """
        import os
        import mimetypes
        filename = os.path.basename(file_path)
        content_type, _ = mimetypes.guess_type(file_path)
        content_type = content_type or "application/octet-stream"
        with open(file_path, "rb") as f:
            data = f.read()
        files = {"file": (filename, data, content_type)}
        form = {
            "work_item_id": work_item_id,
            "work_item_type": work_item_type,
        }
        if attachment_type:
            form["attachment_type"] = attachment_type
        r = self._session.post(
            f"{self.base_url}/api/attachments/upload",
            data=form,
            files=files,
            headers=self._auth_headers(),
        )
        self._raise_for_status(r)
        return r.json()

    def list_attachments(self, work_item_id: str, work_item_type: str) -> List[dict]:
        """Return all attachments for a work item."""
        return self._get("/api/attachments", params={
            "work_item_id": work_item_id,
            "work_item_type": work_item_type,
        })

    def get_attachment_url(self, attachment_id: str) -> str:
        """
        Return a pre-signed download URL for an attachment (valid ~1 hour).
        The URL can be passed directly to requests.get() or opened in a browser.
        """
        r = self._session.get(
            f"{self.base_url}/api/attachments/{attachment_id}/download",
            headers=self._auth_headers(),
            allow_redirects=False,
        )
        if r.status_code in (301, 302, 307, 308):
            return r.headers["Location"]
        self._raise_for_status(r)
        return r.url

    # ── Heartbeat ─────────────────────────────────────────────────────────────

    def send_heartbeat(
        self,
        claim_id: str,
        message: str,
        progress_pct: int = None,
    ) -> dict:
        """
        Report live progress on a claimed work item.
        Call every 30-60 seconds while working to show the agent is alive.
        progress_pct: integer 0-100.
        """
        return self._post("/api/agent/heartbeat", data={
            "claim_id": claim_id,
            "status_message": message,
            "progress_pct": progress_pct,
        })

    # ── Plan & Completion ─────────────────────────────────────────────────────

    def create_plan(
        self,
        work_item_id: str,
        work_item_type: str,
        content: str,
    ) -> dict:
        """
        Submit an execution plan AND automatically post it as a visible comment.

        REQUIRED before writing any code. The plan should describe:
          - What you are building (endpoint, model, UI change, etc.)
          - How you will implement it (steps, DB changes, API changes)
          - Edge cases and validation you will handle
          - Any assumptions or open questions

        The plan is posted as a comment so humans can review your design
        BEFORE you start implementing. This is the design review gate.

        Example content:
            DESIGN: Implement POST /api/orders endpoint
            - Add Order model with fields: user_id, items, total, status
            - Migration: create orders table
            - Endpoint: validate input, persist to DB, return created order
            - Edge cases: empty items list (422), invalid user_id (404)
            - Tests: happy path, validation errors, auth check
        """
        plan = self._post(
            f"/api/agent/work-items/{work_item_id}/plan",
            data={"content": content, "work_item_type": work_item_type},
        )
        # Also post as a visible comment so humans see the design immediately
        try:
            self.add_comment(
                work_item_id,
                work_item_type,
                f"[DESIGN PLAN]\n\n{content}",
                is_internal=False,
            )
        except Exception:
            pass  # plan was saved; comment failure is non-fatal
        return plan

    def complete_work(
        self,
        work_item_id: str,
        work_item_type: str,
        summary: str,
        outcome: str = "completed",
    ) -> dict:
        """
        Mark work as finished, submit completion summary, AND post as a comment.

        summary should include:
          - What was done (feature/fix/test description)
          - Files changed (list the key files)
          - Any decisions or trade-offs made
          - What reviewers / QA should check

        outcome: completed | partial | blocked
        """
        result = self._post(
            f"/api/agent/work-items/{work_item_id}/completion-summary",
            data={
                "summary": summary,
                "work_item_type": work_item_type,
                "outcome": outcome,
            },
        )
        # Also post as a visible comment
        outcome_emoji = {"completed": "[DONE]", "partial": "[PARTIAL]", "blocked": "[BLOCKED]"}
        label = outcome_emoji.get(outcome, f"[{outcome.upper()}]")
        try:
            self.add_comment(
                work_item_id,
                work_item_type,
                f"{label} {summary}",
                is_internal=False,
            )
        except Exception:
            pass
        return result

    # ── Deploy & Test ─────────────────────────────────────────────────────────

    def deploy_and_restart(
        self,
        deploy_command: str = "bash deploy.sh",
        working_dir: Optional[str] = None,
        timeout: int = 600,
    ) -> dict:
        """
        MANDATORY after dev_done: run the deploy script and restart containers.

        Runs deploy_command in working_dir (defaults to current directory).
        Returns:
            {
                "success": bool,
                "returncode": int,
                "output": str   # combined stdout + stderr (last 3000 chars)
            }

        REQUIRED usage after calling this method:
            result = client.deploy_and_restart("bash deploy.sh", working_dir="/path/to/project")
            client.add_comment(item_id, item_type,
                f"[DEPLOYED] {'SUCCESS' if result['success'] else 'FAILED'}\\n"
                f"Exit code: {result['returncode']}\\n"
                f"Output:\\n{result['output'][-1000:]}")
            if not result["success"]:
                raise SystemExit("Deploy failed - do NOT mark dev_done until fixed")
        """
        import subprocess
        cwd = working_dir or os.getcwd()
        try:
            proc = subprocess.run(
                deploy_command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            combined = (proc.stdout or "") + (proc.stderr or "")
            success = proc.returncode == 0
            print(
                f"[ExecPlane] Deploy {'succeeded' if success else 'FAILED'} "
                f"(exit {proc.returncode})"
            )
            return {
                "success": success,
                "returncode": proc.returncode,
                "output": combined[-3000:],
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "returncode": -1,
                "output": f"Deploy timed out after {timeout}s",
            }
        except Exception as exc:
            return {
                "success": False,
                "returncode": -1,
                "output": str(exc),
            }

    def run_playwright_tests(
        self,
        test_command: str = "npx playwright test",
        working_dir: Optional[str] = None,
        timeout: int = 300,
    ) -> dict:
        """
        Run Playwright end-to-end tests and return the result.

        QA agents MUST call this after the feature is deployed.
        Post the output as a [PLAYWRIGHT] comment so humans can see test results.

        Returns:
            {
                "success": bool,
                "returncode": int,
                "output": str   # combined stdout + stderr (last 3000 chars)
            }

        REQUIRED usage:
            result = client.run_playwright_tests(
                "npx playwright test --reporter=line",
                working_dir="/path/to/frontend"
            )
            client.add_comment(item_id, item_type,
                f"[PLAYWRIGHT] {'PASSED' if result['success'] else 'FAILED'}\\n"
                f"Exit code: {result['returncode']}\\n"
                f"Output:\\n{result['output'][-1500:]}")
        """
        import subprocess
        cwd = working_dir or os.getcwd()
        try:
            proc = subprocess.run(
                test_command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            combined = (proc.stdout or "") + (proc.stderr or "")
            success = proc.returncode == 0
            print(
                f"[ExecPlane] Playwright tests {'passed' if success else 'FAILED'} "
                f"(exit {proc.returncode})"
            )
            return {
                "success": success,
                "returncode": proc.returncode,
                "output": combined[-3000:],
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "returncode": -1,
                "output": f"Playwright tests timed out after {timeout}s",
            }
        except Exception as exc:
            return {
                "success": False,
                "returncode": -1,
                "output": str(exc),
            }


# ── Role-specialised client subclasses ────────────────────────────────────────

class DevAgentClient(ExecPlaneClient):
    """
    ExecPlane client pre-configured for a development (coding) agent.

    ── MANDATORY STARTUP (every run) ────────────────────────────────────
        client.login(email, password)
        info = client.check_version()
        if info["needs_update"]:
            client.download_latest_client()
            raise SystemExit("Restarting with updated client")

    ── FULL WORKFLOW ─────────────────────────────────────────────────────
     1. item  = client.get_next_dev_task(project_id)
     2. claim = client.claim_work_item(item['id'], item['type'], role='dev')
     3. [COMMENT] client.add_comment(item['id'], item['type'],
                      "Starting work. Plan: <brief plan>")
     4. client.create_plan(item['id'], item['type'], "Detailed design...")
     5. client.transition_task(item['id'], 'in_progress')
     6. ... implement - call send_heartbeat() every ~60s ...
     7. [COMMENT] client.add_comment(item['id'], item['type'],
                      "50% done - <progress note>")
     8. client.add_worklog(item['id'], item['type'], "What I did", started_at)
     9. [DEPLOY] result = client.deploy_and_restart("bash deploy.sh", working_dir="/path/to/project")
        [COMMENT] client.add_comment(item['id'], item['type'],
                      f"[DEPLOYED] {'OK' if result['success'] else 'FAILED'}\n{result['output'][-500:]}")
        if not result['success']: raise SystemExit("Deploy failed - fix before dev_done")
    10. client.transition_task(item['id'], 'dev_done')
    11. [COMMENT] client.add_comment(item['id'], item['type'],
                      "Done: <summary>. Files changed: <list>")
    12. client.complete_work(item['id'], item['type'], "Summary")
    13. client.release_work_item(item['id'], item['type'])
    14. [CLAUDE.MD] client.update_claude_md(item['id'], item['type'],
                      "Summary", files_changed=["a.py", "b.py"])
    """

    def get_next_dev_task(self, project_id: str) -> dict:
        """Get the next implementation task (excludes test plans)."""
        return self.get_next_work_item(project_id, role="dev")

    def list_my_tasks(self, project_id: str, status: str = None, limit: int = 50) -> List[dict]:
        """List implementation tasks for this dev agent."""
        return self.list_tasks_by_role(project_id, role="dev", status=status, limit=limit)


class QAAgentClient(ExecPlaneClient):
    """
    ExecPlane client pre-configured for a QA / testing agent.

    ── MANDATORY STARTUP (every run) ────────────────────────────────────
        client.login(email, password)
        info = client.check_version()
        if info["needs_update"]:
            client.download_latest_client()
            raise SystemExit("Restarting with updated client")

    ── FULL WORKFLOW ─────────────────────────────────────────────────────
     1. item  = client.get_next_test_plan(project_id)
     2. claim = client.claim_work_item(item['id'], item['type'], role='qa')
     3. [COMMENT] client.add_comment(item['id'], item['type'],
                      "Starting QA. Test plan: <N> cases - <brief description>")
     4. client.create_plan(item['id'], item['type'], '''
            Test Cases:
            1. <Playwright test: describe the test + page URL + actions + expected result>
            2. <test case 2>
            ...
            Playwright test file: frontend/tests/<feature>.spec.ts
        ''')
        # This posts the full Playwright test plan as a [DESIGN PLAN] comment
     5. client.transition_task(item['id'], 'qa_claimed')
     6. client.transition_task(item['id'], 'under_testing')
     7. [PLAYWRIGHT] result = client.run_playwright_tests(
                      "npx playwright test", working_dir="/path/to/frontend")
        [COMMENT] client.add_comment(item['id'], item['type'],
                      f"[PLAYWRIGHT] {'PASSED' if result['success'] else 'FAILED'}\n{result['output'][-1000:]}")
     8. ... run manual checks if needed - call send_heartbeat() every ~60s ...
     9. client.add_worklog(item['id'], item['type'], "Ran N test cases", started_at)
    10. if passed:
            client.transition_task(item['id'], 'test_passed')
            [COMMENT] client.add_comment(item['id'], item['type'],
                          "PASSED: N/N tests passed. <details>")
        else:
            client.transition_task(item['id'], 'test_failed')
            [COMMENT] client.add_comment(item['id'], item['type'],
                          "FAILED: X/N tests failed. Failures: <details>. Returning to dev.")
    11. client.complete_work(item['id'], item['type'], "Summary")
    12. client.release_work_item(item['id'], item['type'])
    13. [CLAUDE.MD] client.update_claude_md(item['id'], item['type'],
                      "QA complete: N/N passed", files_changed=["test_results.json"])
    """

    def get_next_test_plan(self, project_id: str) -> dict:
        """Get the next test plan task assigned to QA."""
        return self.get_next_work_item(project_id, role="qa")

    def list_my_tasks(self, project_id: str, status: str = None, limit: int = 50) -> List[dict]:
        """List test plan tasks for this QA agent."""
        return self.list_tasks_by_role(project_id, role="qa", status=status, limit=limit)


# ── Quickstart example (run this file directly) ────────────────────────────────
if __name__ == "__main__":
    print(f"ExecPlane Agent Client v{CLIENT_VERSION}")
    print("─" * 50)
    client = ExecPlaneClient("http://localhost:8000", auto_check_version=False)
    client.help()

    print("\nDev agent workflow:")
    print(textwrap.dedent("""
        from execplane_client import DevAgentClient
        from datetime import datetime, timezone

        client = DevAgentClient("http://localhost:8000")
        client.login("dev-agent@example.com", "s3cr3t")
        client.check_version()

        project_id = "your-project-id"
        project_dir = "/path/to/project"  # where deploy.sh lives

        # Find next implementation task (excludes test plans)
        item = client.get_next_dev_task(project_id)
        if not item.get("id"):
            print("No work available"); exit()

        claim = client.claim_work_item(item['id'], item['type'], role='dev')
        started = datetime.now(timezone.utc).isoformat()

        client.add_comment(item['id'], item['type'], "Claimed. Writing design plan now.")
        client.create_plan(item['id'], item['type'], "Implement the feature per acceptance criteria...")
        client.transition_task(item['id'], 'in_progress')

        client.send_heartbeat(claim['id'], "Writing code", progress_pct=30)

        # ... implement the feature ...

        client.add_worklog(item['id'], item['type'],
            "Implemented feature, added unit tests", started_at=started)

        # MANDATORY: deploy and restart before marking dev_done
        result = client.deploy_and_restart("bash deploy.sh", working_dir=project_dir)
        client.add_comment(item['id'], item['type'],
            f"[DEPLOYED] {'SUCCESS' if result['success'] else 'FAILED'}\\n"
            f"Exit code: {result['returncode']}\\n{result['output'][-500:]}")
        if not result['success']:
            raise SystemExit("Deploy failed - fix before dev_done")

        client.transition_task(item['id'], 'dev_done')
        client.complete_work(item['id'], item['type'], "Feature implemented and ready for QA")
        client.release_work_item(item['id'], item['type'])
        client.update_claude_md(item['id'], item['type'],
            "Feature implemented.", files_changed=["backend/app/..."])
    """))

    print("\nQA agent workflow:")
    print(textwrap.dedent("""
        from execplane_client import QAAgentClient
        from datetime import datetime, timezone

        client = QAAgentClient("http://localhost:8000")
        client.login("qa-agent@example.com", "s3cr3t")
        client.check_version()

        project_id = "your-project-id"
        frontend_dir = "/path/to/frontend"  # where playwright tests live

        # Find next test plan task
        item = client.get_next_test_plan(project_id)
        if not item.get("id"):
            print("No test plans available"); exit()

        claim = client.claim_work_item(item['id'], item['type'], role='qa')
        started = datetime.now(timezone.utc).isoformat()

        # Write a full Playwright test plan (auto-posts as [DESIGN PLAN] comment)
        client.create_plan(item['id'], item['type'], '''
        Test Cases (Playwright E2E):

        1. Happy path
           - Navigate to /feature-url
           - Fill form fields, submit
           - Assert: success toast + list item appears

        2. Validation errors
           - Submit empty form
           - Assert: error messages shown on required fields

        3. Auth guard
           - Access /feature-url without login
           - Assert: redirect to /login

        Playwright file: frontend/tests/feature-name.spec.ts
        Run: npx playwright test tests/feature-name.spec.ts --reporter=line
        ''')

        client.transition_task(item['id'], 'qa_claimed')
        client.transition_task(item['id'], 'under_testing')

        # Run Playwright tests
        result = client.run_playwright_tests(
            "npx playwright test --reporter=line",
            working_dir=frontend_dir
        )
        client.add_comment(item['id'], item['type'],
            f"[PLAYWRIGHT] {'PASSED' if result['success'] else 'FAILED'}\\n"
            f"Exit code: {result['returncode']}\\n{result['output'][-1000:]}")

        client.send_heartbeat(claim['id'], "Test suite complete", progress_pct=90)

        passed = result['success']
        client.add_worklog(item['id'], item['type'],
            "Ran Playwright test suite. See [PLAYWRIGHT] comment for results.", started_at=started)

        if passed:
            client.transition_task(item['id'], 'test_passed')
            client.add_comment(item['id'], item['type'],
                "PASSED: All Playwright tests passed. Feature verified.")
            client.complete_work(item['id'], item['type'], "All tests passed. QA approved.")
        else:
            client.transition_task(item['id'], 'test_failed')
            client.add_comment(item['id'], item['type'],
                f"FAILED: Playwright tests failed. See [PLAYWRIGHT] comment. Returning to dev.")
            client.complete_work(item['id'], item['type'], "Tests failed. Returned for fix.", outcome='blocked')

        client.release_work_item(item['id'], item['type'])
        client.update_claude_md(item['id'], item['type'],
            f"QA complete. Playwright {'passed' if passed else 'FAILED'}.")
    """))
