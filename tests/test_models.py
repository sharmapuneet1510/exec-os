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
