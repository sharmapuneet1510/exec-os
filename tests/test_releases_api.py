from datetime import date
from web.routers.releases import ReleaseIn, ReleaseOut

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
        "created_at": date(2026, 5, 7),
        "updated_at": date(2026, 5, 7),
    }
    r = ReleaseOut(**data)
    assert r.release_id == "rel-123"
    assert r.status == "planned"
