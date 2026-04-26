"""Test workload aggregation endpoints."""
import pytest
from fastapi.testclient import TestClient
from db.base import SessionLocal
from db.models import TeamMemberORM, TaskORM, MockJiraIssueORM, MockGitLabMRORM, ApplicationORM


def test_team_workload_endpoint_structure():
    """Test /api/workload/team returns correct structure"""
    from web.app import app

    client = TestClient(app)

    # Create test app (application_id required)
    db = SessionLocal()
    test_app = ApplicationORM(name="Test App", code="TEST")
    db.add(test_app)
    db.commit()
    app_id = test_app.application_id
    db.close()

    response = client.get(f"/api/workload/team?app_id={app_id}")
    assert response.status_code == 200

    data = response.json()
    assert "team" in data
    assert "summary" in data
    assert isinstance(data["team"], list)
    assert "total_members" in data["summary"]
    assert "overloaded_count" in data["summary"]
    assert "total_local_tasks" in data["summary"]
    assert "total_jira_issues" in data["summary"]
    assert "total_mrs" in data["summary"]
    assert "last_updated" in data["summary"]
