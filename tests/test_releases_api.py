import pytest
from datetime import date, datetime
from web.routers.releases import ReleaseIn, ReleaseOut
from db.base import SessionLocal, engine
from db.models import Base, ReleaseORM, ProjectORM

@pytest.fixture
def db():
    """Get a fresh database session"""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_release_in_validation():
    # Valid minimal
    r = ReleaseIn(name="v1.0")
    assert r.name == "v1.0"
    assert r.version == ""
    assert r.status == "planned"

def test_release_in_name_required():
    # Name is required
    try:
        ReleaseIn()
        assert False, "Should require name"
    except Exception:
        pass

def test_release_out_fields():
    data = {
        "release_id": "rel-123",
        "name": "v1.0",
        "version": "1.0.0",
        "project_id": "proj-1",
        "project_name": "My Project",
        "application_id": None,
        "due_date": None,
        "status": "planned",
        "description": "Initial release",
        "days_until_due": None,
        "is_overdue": False,
        "created_at": datetime(2026, 5, 7, 12, 0, 0),
        "updated_at": datetime(2026, 5, 7, 12, 0, 0),
    }
    r = ReleaseOut(**data)
    assert r.release_id == "rel-123"
    assert r.status == "planned"


def test_to_out_with_orm_object(db):
    from web.routers.releases import _to_out

    # Create a project
    proj = ProjectORM(project_id="proj-test", name="Test Project", status="active")
    db.add(proj)
    db.commit()

    # Create a release
    rel = ReleaseORM(
        release_id="rel-test",
        name="v1.0",
        version="1.0.0",
        project_id="proj-test",
        due_date=date(2026, 6, 1),
        status="planned",
        description="Test release"
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)

    # Convert to dict
    result = _to_out(rel, db)

    # Verify conversion
    assert result["release_id"] == "rel-test"
    assert result["name"] == "v1.0"
    assert result["project_name"] == "Test Project"
    assert result["due_date"] == date(2026, 6, 1)
    assert result["status"] == "planned"
    assert result["days_until_due"] is not None  # Should be calculated
    assert isinstance(result["created_at"], datetime)
    assert isinstance(result["updated_at"], datetime)


def test_create_release_minimal(db):
    from fastapi.testclient import TestClient
    from web.app import app

    client = TestClient(app)
    response = client.post("/api/releases", json={"name": "v1.0"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "v1.0"
    assert data["status"] == "planned"
    assert data["release_id"]


def test_create_release_full(db):
    from fastapi.testclient import TestClient
    from web.app import app

    client = TestClient(app)
    response = client.post("/api/releases", json={
        "name": "v2.0",
        "version": "2.0.0",
        "project_id": None,
        "due_date": "2026-06-01",
        "status": "in_progress",
        "description": "Major release",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "v2.0"
    assert data["version"] == "2.0.0"
    assert data["status"] == "in_progress"


def test_create_release_empty_name(db):
    from fastapi.testclient import TestClient
    from web.app import app

    client = TestClient(app)
    response = client.post("/api/releases", json={"name": ""})
    assert response.status_code == 400


def test_create_release_invalid_project(db):
    from fastapi.testclient import TestClient
    from web.app import app

    client = TestClient(app)
    response = client.post("/api/releases", json={
        "name": "v1.0",
        "project_id": "nonexistent-proj"
    })
    assert response.status_code == 400
