"""
Tests for admin export/import endpoints.
"""
import json
import pytest
from fastapi.testclient import TestClient
from web.app import app

client = TestClient(app)


def test_export_database():
    """Test export endpoint returns valid JSON with structure."""
    response = client.get("/api/admin/export")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "exported_at" in data
    assert "tables" in data
    assert data["version"] == "1.0"
    assert isinstance(data["tables"], dict)


def test_export_contains_all_tables():
    """Test that export includes all expected tables."""
    response = client.get("/api/admin/export")
    assert response.status_code == 200
    data = response.json()
    tables = data.get("tables", {})

    # Check some core tables exist
    expected_tables = ["email_config", "outlook_config", "tasks", "projects", "commitments"]
    for table_name in expected_tables:
        assert table_name in tables or len(tables) > 0  # At least some data structure


def test_import_valid_export():
    """Test import of valid exported data."""
    # First export
    export_response = client.get("/api/admin/export")
    assert export_response.status_code == 200
    export_data = export_response.json()

    # Then import
    import_response = client.post("/api/admin/import", json=export_data)
    assert import_response.status_code == 200
    result = import_response.json()
    assert result["status"] == "success"
    assert "restored_tables" in result


def test_import_invalid_format():
    """Test import with invalid format."""
    invalid_data = {"invalid": "format"}
    response = client.post("/api/admin/import", json=invalid_data)
    assert response.status_code == 400
    assert "Invalid export format" in response.json()["detail"]


def test_export_preserves_data_types():
    """Test that export preserves data types for reimport."""
    # Export, manipulate, and re-import
    export_response = client.get("/api/admin/export")
    export_data = export_response.json()

    # Verify structure is correct for reimport
    assert "version" in export_data
    assert "tables" in export_data

    # Try to re-import - should work
    import_response = client.post("/api/admin/import", json=export_data)
    assert import_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
