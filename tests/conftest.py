"""Pytest configuration and fixtures."""
import pytest


def pytest_configure(config):
    """Initialize database schema before test collection."""
    from db.init_db import create_all
    # Ensure all tables are created (idempotent - only creates missing tables)
    create_all()


@pytest.fixture(autouse=True)
def ensure_database_tables():
    """Ensure all database tables exist before each test (handles cleanup by other tests)."""
    from db.init_db import create_all
    # Recreate any missing tables (in case a previous test dropped them)
    create_all()
    yield
