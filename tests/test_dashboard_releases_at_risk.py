from datetime import date, timedelta
from fastapi.testclient import TestClient
from web.app import app
from db.init_db import create_all
from db.base import SessionLocal
from db.models import DeliveryReleaseORM, DeliveryReleaseItemORM

create_all()
client = TestClient(app)


def test_breached_release_item_appears_in_sod():
    db = SessionLocal()
    r = DeliveryReleaseORM(name="AtRisk Rel", status="in_progress")
    db.add(r)
    db.commit()
    db.refresh(r)
    db.add(DeliveryReleaseItemORM(release_id=r.release_id, order=0, title="Dev Completion",
           stage="development", status="pending", planned_date=date.today() - timedelta(days=5)))
    db.commit()
    db.close()

    sod = client.get("/api/dashboard/sod").json()
    assert "releases_at_risk" in sod
    hit = [x for x in sod["releases_at_risk"] if x["item"] == "Dev Completion"]
    assert hit and hit[0]["state"] == "breached" and hit[0]["days"] == 5
