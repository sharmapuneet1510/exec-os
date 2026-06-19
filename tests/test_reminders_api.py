"""End-to-end tests for the reminders API (router must be mounted)."""
import pytest
from fastapi.testclient import TestClient
from web.app import app

client = TestClient(app)


@pytest.fixture
def cleanup_reminders():
    created = []
    yield created
    for rid in created:
        client.delete(f"/api/reminders/{rid}")


def test_list_reminders_endpoint_is_mounted():
    resp = client.get("/api/reminders")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_fixed_time_reminder(cleanup_reminders):
    resp = client.post("/api/reminders", json={
        "title": "Standup", "trigger_type": "fixed_time",
        "trigger_value": "09:30", "priority": "medium",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Standup"
    assert data["trigger_value"] == "09:30"
    assert data["is_active"] is True
    cleanup_reminders.append(data["reminder_id"])


def test_create_relative_interval_reminder(cleanup_reminders):
    resp = client.post("/api/reminders", json={
        "title": "Day before deadline", "trigger_type": "relative_interval",
        "trigger_value": "-1d", "due_date": "2026-07-01", "priority": "high",
    })
    assert resp.status_code == 201
    cleanup_reminders.append(resp.json()["reminder_id"])


def test_create_rejects_bad_fixed_time():
    resp = client.post("/api/reminders", json={
        "title": "Bad", "trigger_type": "fixed_time", "trigger_value": "99:99",
    })
    assert resp.status_code == 400


def test_create_rejects_bad_interval():
    resp = client.post("/api/reminders", json={
        "title": "Bad", "trigger_type": "relative_interval", "trigger_value": "soon",
    })
    assert resp.status_code == 400


def test_get_patch_delete_lifecycle(cleanup_reminders):
    rid = client.post("/api/reminders", json={
        "title": "Temp", "trigger_type": "fixed_time", "trigger_value": "10:00",
    }).json()["reminder_id"]

    assert client.get(f"/api/reminders/{rid}").status_code == 200

    patched = client.patch(f"/api/reminders/{rid}", json={"title": "Renamed"})
    assert patched.status_code == 200
    assert patched.json()["title"] == "Renamed"

    assert client.delete(f"/api/reminders/{rid}").status_code == 204
    assert client.get(f"/api/reminders/{rid}").status_code == 404


def test_snooze_sets_snooze_until(cleanup_reminders):
    rid = client.post("/api/reminders", json={
        "title": "Snoozable", "trigger_type": "fixed_time", "trigger_value": "11:00",
    }).json()["reminder_id"]
    cleanup_reminders.append(rid)

    resp = client.post(f"/api/reminders/{rid}/snooze?minutes=30")
    assert resp.status_code == 200
    assert resp.json()["snooze_until"] is not None


def test_manual_trigger_creates_alert(cleanup_reminders):
    rid = client.post("/api/reminders", json={
        "title": "Fire me", "trigger_type": "fixed_time", "trigger_value": "12:00",
        "priority": "high",
    }).json()["reminder_id"]
    cleanup_reminders.append(rid)

    before = len(client.get("/api/alerts").json())
    resp = client.post(f"/api/reminders/{rid}/trigger")
    assert resp.status_code == 200
    after = len(client.get("/api/alerts").json())
    assert after == before + 1
