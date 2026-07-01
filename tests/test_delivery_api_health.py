from fastapi.testclient import TestClient
from web.app import app
from db.init_db import create_all
from db.base import SessionLocal
from db.models import DeliveryTemplateORM

create_all()
client = TestClient(app)


def _std_template_id():
    db = SessionLocal()
    t = db.query(DeliveryTemplateORM).filter(DeliveryTemplateORM.name == "Standard Release").first()
    db.close()
    return t.template_id


def test_release_from_template_has_health_and_stages():
    r = client.post("/api/delivery/releases", json={
        "name": "Rel HealthTest", "version": "9.9", "template_id": _std_template_id(),
        "status": "in_progress"})
    assert r.status_code == 201
    rid = r.json()["release_id"]
    detail = client.get(f"/api/delivery/releases/{rid}").json()
    assert "health" in detail
    assert detail["health"]["derived_status"] in ("TODO", "IN_PROGRESS", "COMPLETED")
    assert len(detail["items"]) == 6
    assert detail["items"][0]["stage"] in ("requirement_gathering", "development", "qa", "uat", "in_prod")


def test_patch_item_planned_date_and_done_stamps_completed():
    rid = client.post("/api/delivery/releases", json={
        "name": "Rel PatchTest", "template_id": _std_template_id(), "status": "in_progress"}).json()["release_id"]
    item = client.get(f"/api/delivery/releases/{rid}").json()["items"][0]
    patched = client.patch(f"/api/delivery/releases/{rid}/items/{item['item_id']}",
                           json={"planned_date": "2026-06-20", "status": "done"}).json()
    assert patched["planned_date"] == "2026-06-20"
    assert patched["completed_at"] is not None
