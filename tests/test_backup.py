import zipfile
from datetime import datetime, timezone
from pathlib import Path
import pytest
from backup.model import BackupManifest
from backup.service import BackupService

@pytest.fixture
def app_dir(tmp_path):
    d = tmp_path / ".commanddesk"
    d.mkdir()
    (d / "settings.json").write_text('{"key":"value"}')
    (d / "plans").mkdir()
    (d / "plans" / "2026-04-22.json").write_text('{}')
    return d

@pytest.fixture
def svc(app_dir): return BackupService(app_dir=app_dir)
@pytest.fixture
def dest(tmp_path): return tmp_path / "backups"

# Model
def test_manifest_round_trip():
    m = BackupManifest("id1", datetime.now(timezone.utc), "/path/b.zip", 1024, "success")
    assert BackupManifest.from_dict(m.to_dict()).backup_id == "id1"

def test_manifest_failed_stores_error():
    m = BackupManifest("id2", datetime.now(timezone.utc), "/p", 0, "failed", error="disk full")
    restored = BackupManifest.from_dict(m.to_dict())
    assert restored.error == "disk full"

# Service — create
def test_create_backup_produces_zip(svc, dest):
    m = svc.create_backup(dest)
    assert m.status == "success"
    assert Path(m.path).exists()
    assert m.size_bytes > 0

def test_create_backup_zip_contains_files(svc, dest):
    m = svc.create_backup(dest)
    with zipfile.ZipFile(m.path) as zf:
        names = zf.namelist()
    assert any("settings.json" in n for n in names)

def test_create_backup_writes_manifest(svc, dest):
    m = svc.create_backup(dest)
    manifests = list(dest.glob("*_manifest.json"))
    assert len(manifests) == 1

# Service — list
def test_list_backups_empty(svc, dest):
    assert svc.list_backups(dest) == []

def test_list_backups_returns_newest_first(svc, dest):
    svc.create_backup(dest)
    svc.create_backup(dest)
    results = svc.list_backups(dest)
    assert len(results) == 2
    assert results[0].created_at >= results[1].created_at

# Service — validate
def test_validate_valid_zip(svc, dest):
    m = svc.create_backup(dest)
    assert svc.validate_backup(Path(m.path)) is True

def test_validate_missing_file(svc):
    assert svc.validate_backup(Path("/nonexistent/backup.zip")) is False

def test_validate_corrupt_zip(tmp_path, svc):
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"not a zip")
    assert svc.validate_backup(bad) is False
