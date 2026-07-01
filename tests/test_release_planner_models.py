from db.models import DeliveryTemplateItemORM, DeliveryReleaseItemORM, DeliveryReleaseSprintORM


def test_template_item_has_stage_and_offset():
    cols = DeliveryTemplateItemORM.__table__.columns.keys()
    assert "stage" in cols
    assert "planned_offset_days" in cols


def test_release_item_has_stage_and_planned_date():
    cols = DeliveryReleaseItemORM.__table__.columns.keys()
    assert "stage" in cols
    assert "planned_date" in cols


def test_release_sprint_table():
    cols = DeliveryReleaseSprintORM.__table__.columns.keys()
    assert DeliveryReleaseSprintORM.__tablename__ == "delivery_release_sprints"
    for c in ("attach_id", "release_id", "board_id", "sprint_id", "sprint_name", "added_at"):
        assert c in cols
