import pytest
from fastapi.testclient import TestClient
from db.base import SessionLocal, engine
from db.models import Base

@pytest.fixture
def db():
    """Get a fresh database session"""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_export_database(db):
    from web.app import app
    client = TestClient(app)

    response = client.get("/api/admin/export")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    # Verify it's valid JSON
    data = response.json()
    assert isinstance(data, dict)
    assert "tables" in data
    assert "exported_at" in data
    assert "version" in data


def test_export_contains_tables(db):
    from web.app import app
    client = TestClient(app)

    response = client.get("/api/admin/export")
    data = response.json()
    tables = data["tables"]
    # Should have at least some tables
    assert len(tables) > 0
    # Each table should have a "rows" key
    for table_name, table_data in tables.items():
        assert "rows" in table_data
        assert isinstance(table_data["rows"], list)
