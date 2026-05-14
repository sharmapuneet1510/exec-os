def test_seed_data_creates_team_members():
    """Verify seed_data.py creates expected team members"""
    import subprocess
    result = subprocess.run(
        ["python3", "seed_data.py"],
        cwd="/Users/puneetsharma/Workspace/projects/ai-lab/command-center",
        capture_output=True,
        timeout=30
    )
    assert result.returncode == 0, result.stderr.decode()

    from db.base import SessionLocal
    from db.models import TeamMemberORM
    db = SessionLocal()
    members = db.query(TeamMemberORM).all()
    db.close()

    assert len(members) == 5
    names = [m.name for m in members]
    assert "Alice Chen" in names
    assert "Bob Johnson" in names
    assert "Carol Martinez" in names
    assert "David Lee" in names
    assert "Eva Patel" in names


def test_seed_data_creates_mock_jira_issues():
    """Verify seed_data.py creates expected mock Jira issues"""
    from db.base import SessionLocal
    from db.models import MockJiraIssueORM
    db = SessionLocal()
    issues = db.query(MockJiraIssueORM).all()
    db.close()

    assert len(issues) >= 10
    keys = [i.key for i in issues]
    assert "ENG-101" in keys
    assert "WEB-201" in keys
    assert "QA-301" in keys
    assert "OPS-401" in keys


def test_seed_data_creates_mock_gitlab_mrs():
    """Verify seed_data.py creates expected mock GitLab MRs"""
    from db.base import SessionLocal
    from db.models import MockGitLabMRORM
    db = SessionLocal()
    mrs = db.query(MockGitLabMRORM).all()
    db.close()

    assert len(mrs) >= 6
    authors = [m.author_username for m in mrs]
    assert "achen" in authors
    assert "bjohnson" in authors
    assert "dlee" in authors


def test_seed_data_assigns_tasks_to_team_members():
    """Verify seed_data.py assigns tasks to team members"""
    from db.base import SessionLocal
    from db.models import TaskORM, TeamMemberORM
    db = SessionLocal()

    tasks = db.query(TaskORM).filter(TaskORM.assignee_id != None).all()
    members = db.query(TeamMemberORM).all()

    db.close()

    # At least some tasks should be assigned
    assert len(tasks) >= 5
    # At least team members should exist
    assert len(members) == 5
