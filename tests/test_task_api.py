"""Test task API responses include assignee_id"""
import pytest
from fastapi.testclient import TestClient
from db.base import SessionLocal, engine
from db.models import Base, TaskORM, TeamMemberORM


@pytest.fixture
def client():
    """Create a test client with clean database"""
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield TestClient(TestClient)
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Get a fresh database session"""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_task_response_includes_assignee(db):
    """Verify task GET response includes assignee_id"""
    from web.app import app
    from fastapi.testclient import TestClient

    # Create team member
    member = TeamMemberORM(name="Alice", email="alice@company.com")
    db.add(member)
    db.commit()
    db.refresh(member)
    member_id = member.member_id

    # Create task with assignee
    task = TaskORM(title="Test", assignee_id=member_id)
    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.task_id

    # Test GET single task
    client = TestClient(app)
    response = client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 200

    data = response.json()
    assert "assignee_id" in data, "assignee_id should be in response"
    assert data["assignee_id"] == member_id, f"assignee_id should be {member_id}, got {data.get('assignee_id')}"


def test_task_list_includes_assignee(db):
    """Verify task list response includes assignee_id"""
    from web.app import app
    from fastapi.testclient import TestClient

    # Create team member
    member = TeamMemberORM(name="Bob", email="bob@company.com")
    db.add(member)
    db.commit()
    db.refresh(member)
    member_id = member.member_id

    # Create task with assignee
    task = TaskORM(title="List Test", assignee_id=member_id)
    db.add(task)
    db.commit()

    # Test GET list
    client = TestClient(app)
    response = client.get("/api/tasks")
    assert response.status_code == 200

    data = response.json()
    assert len(data) > 0
    assert "assignee_id" in data[0], "assignee_id should be in list response"


def test_task_patch_accepts_assignee(db):
    """Verify PATCH can update assignee_id"""
    from web.app import app
    from fastapi.testclient import TestClient

    # Create team members
    member1 = TeamMemberORM(name="Charlie", email="charlie@company.com")
    member2 = TeamMemberORM(name="Diana", email="diana@company.com")
    db.add(member1)
    db.add(member2)
    db.commit()
    db.refresh(member1)
    db.refresh(member2)

    # Create task with first assignee
    task = TaskORM(title="Update Test", assignee_id=member1.member_id)
    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.task_id

    # Update with second assignee
    client = TestClient(app)
    response = client.patch(f"/api/tasks/{task_id}", json={"assignee_id": member2.member_id})
    assert response.status_code == 200

    data = response.json()
    assert data["assignee_id"] == member2.member_id, "assignee_id should be updated"
