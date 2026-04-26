def test_team_member_orm_basic():
    from db.models import TeamMemberORM
    member = TeamMemberORM(
        name="Alice Chen",
        email="alice@company.com",
        gitlab_username="achen",
        role="Backend",
        max_concurrent_tasks=8,
        is_active=True
    )
    assert member.name == "Alice Chen"
    assert member.email == "alice@company.com"
    assert member.is_active is True
    assert member.max_concurrent_tasks == 8


def test_mock_jira_issue_orm():
    from db.models import MockJiraIssueORM
    issue = MockJiraIssueORM(
        key="ENG-123",
        summary="Fix bug",
        assignee_email="alice@company.com",
        status="In Progress",
        priority="High",
        project_key="ENG"
    )
    assert issue.key == "ENG-123"
    assert issue.assignee_email == "alice@company.com"


def test_mock_gitlab_mr_orm():
    from db.models import MockGitLabMRORM
    mr = MockGitLabMRORM(
        iid=45,
        title="Add feature",
        author_username="achen",
        project_path="team/api",
        state="opened",
        reviewers='["bjohnson"]'
    )
    assert mr.iid == 45
    assert mr.author_username == "achen"
