import zipfile
from pathlib import Path
import pytest
from backup.service import BackupService
from backup.restore import RestoreService, RestoreResult

@pytest.fixture
def app_dir(tmp_path):
    d = tmp_path / ".commanddesk"
    d.mkdir()
    (d / "settings.json").write_text('{"key":"value"}')
    (d / "plans").mkdir()
    (d / "plans" / "2026-04-22.json").write_text('{"plan_date":"2026-04-22"}')
    return d

@pytest.fixture
def safety_dir(tmp_path): return tmp_path / "safety"
@pytest.fixture
def backup_dest(tmp_path): return tmp_path / "backups"

@pytest.fixture
def svc(app_dir, safety_dir):
    return RestoreService(app_dir=app_dir, safety_dir=safety_dir,
                          backup_service=BackupService(app_dir=app_dir))

@pytest.fixture
def valid_backup(app_dir, backup_dest):
    svc = BackupService(app_dir=app_dir)
    m = svc.create_backup(backup_dest)
    return Path(m.path)

# validate_backup
def test_validate_valid_zip(svc, valid_backup):
    ok, err = svc.validate_backup(valid_backup)
    assert ok is True and err is None

def test_validate_missing_file(svc, tmp_path):
    ok, err = svc.validate_backup(tmp_path / "ghost.zip")
    assert ok is False and "not found" in err

def test_validate_corrupt_zip(svc, tmp_path):
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"not a zip")
    ok, err = svc.validate_backup(bad)
    assert ok is False

def test_validate_empty_zip(svc, tmp_path):
    empty = tmp_path / "empty.zip"
    with zipfile.ZipFile(empty, "w"):
        pass
    ok, err = svc.validate_backup(empty)
    assert ok is False and "empty" in err

# create_safety_backup
def test_safety_backup_creates_zip(svc, safety_dir):
    p = svc.create_safety_backup()
    assert p.exists()
    assert p.suffix == ".zip"

# restore
def test_restore_requires_confirm(svc, valid_backup):
    result = svc.restore(valid_backup, confirm=False)
    assert result.success is False and "confirmation" in result.error

def test_restore_invalid_backup_fails(svc, tmp_path):
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"garbage")
    result = svc.restore(bad, confirm=True)
    assert result.success is False

def test_restore_succeeds(svc, valid_backup, app_dir):
    # Corrupt existing data
    (app_dir / "settings.json").write_text("{}")
    result = svc.restore(valid_backup, confirm=True)
    assert result.success is True
    assert result.restored_files > 0
    assert result.safety_backup_path is not None

def test_restore_creates_safety_backup(svc, valid_backup, safety_dir):
    svc.restore(valid_backup, confirm=True)
    assert any(safety_dir.glob("*.zip"))

def test_restore_result_on_success(svc, valid_backup):
    result = svc.restore(valid_backup, confirm=True)
    assert isinstance(result, RestoreResult)
    assert result.success
    assert result.restored_files > 0
