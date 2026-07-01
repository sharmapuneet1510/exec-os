from db.base import SessionLocal
from db.init_db import create_all, _seed_default_template
from db.models import DeliveryTemplateORM, DeliveryTemplateItemORM


def test_default_template_seeded_once():
    create_all()
    db = SessionLocal()
    _seed_default_template(db)          # second call must be a no-op
    tmpls = db.query(DeliveryTemplateORM).filter(DeliveryTemplateORM.name == "Standard Release").all()
    assert len(tmpls) == 1
    items = db.query(DeliveryTemplateItemORM).filter(
        DeliveryTemplateItemORM.template_id == tmpls[0].template_id).all()
    stages = {i.stage for i in items}
    assert len(items) == 6
    assert stages == {"requirement_gathering", "development", "qa", "uat", "in_prod"}
    db.close()
