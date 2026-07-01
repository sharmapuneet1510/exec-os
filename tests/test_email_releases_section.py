from datetime import date, timedelta
from db.init_db import create_all
from db.base import SessionLocal
from db.models import DeliveryReleaseORM, DeliveryReleaseItemORM
from web.email_sender import _releases_at_risk_section, build_sod_html

create_all()


def test_section_lists_breached_item():
    db = SessionLocal()
    r = DeliveryReleaseORM(name="Email Rel", status="in_progress")
    db.add(r)
    db.commit()
    db.refresh(r)
    db.add(DeliveryReleaseItemORM(release_id=r.release_id, order=0, title="QA Completion",
           stage="qa", status="pending", planned_date=date.today() - timedelta(days=2)))
    db.commit()
    html = _releases_at_risk_section(db)
    assert "QA Completion" in html and "Email Rel" in html
    assert "Releases at risk" in build_sod_html(db)
    db.close()


def test_section_returns_string():
    assert isinstance(_releases_at_risk_section(SessionLocal()), str)
