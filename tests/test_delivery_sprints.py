from fastapi.testclient import TestClient
from web.app import app
from db.init_db import create_all

create_all()
client = TestClient(app)


def _new_release():
    return client.post("/api/delivery/releases", json={"name": "SprintRel"}).json()["release_id"]


def test_attach_list_detach_sprint():
    rid = _new_release()
    a = client.post(f"/api/delivery/releases/{rid}/sprints",
                    json={"board_id": "12", "sprint_id": "340", "sprint_name": "Sprint 24"})
    assert a.status_code == 201
    attach_id = a.json()["attach_id"]

    listed = client.get(f"/api/delivery/releases/{rid}/sprints").json()
    assert len(listed["sprints"]) == 1
    assert listed["sprints"][0]["sprint_name"] == "Sprint 24"
    assert "issues" in listed["sprints"][0]           # empty when Jira not configured

    d = client.delete(f"/api/delivery/releases/{rid}/sprints/{attach_id}")
    assert d.status_code == 204
    assert client.get(f"/api/delivery/releases/{rid}/sprints").json()["sprints"] == []
