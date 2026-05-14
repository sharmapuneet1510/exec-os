from pathlib import Path
import pytest
from backup.model import BackupManifest
from backup.service import BackupService
from backup.schedule import BackupScheduleConfig, ScheduledBackupService
from runtime.scheduler import JobScheduler

@pytest.fixture
def app_dir(tmp_path):
    d = tmp_path / ".commanddesk"
    d.mkdir()
    (d / "settings.json").write_text("{}")
    return d

@pytest.fixture
def dest(tmp_path): return tmp_path / "backups"
@pytest.fixture
def scheduler(): s = JobScheduler(); s.start(); yield s; s.shutdown()
@pytest.fixture
def backup_svc(app_dir): return BackupService(app_dir=app_dir)
@pytest.fixture
def sched_svc(backup_svc, scheduler, tmp_path):
    return ScheduledBackupService(backup_svc, scheduler, config_path=tmp_path / "backup_schedule.json")

# Config
def test_config_defaults():
    c = BackupScheduleConfig()
    assert c.hour == 3 and c.minute == 0 and c.retain_count == 7

def test_config_round_trip():
    c = BackupScheduleConfig(enabled=True, hour=2, minute=30, retain_count=5)
    assert BackupScheduleConfig.from_dict(c.to_dict()).hour == 2

# ScheduledBackupService
def test_schedule_registers_job(sched_svc, scheduler, dest):
    sched_svc.schedule(BackupScheduleConfig(enabled=True, hour=3, minute=0, dest_dir=str(dest)))
    assert sched_svc.is_scheduled()

def test_unschedule_removes_job(sched_svc, scheduler, dest):
    sched_svc.schedule(BackupScheduleConfig(enabled=True, hour=3, minute=0, dest_dir=str(dest)))
    sched_svc.unschedule()
    assert not sched_svc.is_scheduled()

def test_load_config_returns_default_when_missing(sched_svc):
    c = sched_svc.load_config()
    assert c.enabled is False

def test_schedule_persists_config(sched_svc, dest):
    cfg = BackupScheduleConfig(enabled=True, hour=1, minute=15, dest_dir=str(dest))
    sched_svc.schedule(cfg)
    loaded = sched_svc.load_config()
    assert loaded.hour == 1 and loaded.minute == 15

def test_retention_removes_old_backups(backup_svc, sched_svc, dest):
    # Create 4 backups then apply retention of 2
    for _ in range(4):
        backup_svc.create_backup(dest)
    sched_svc._apply_retention(dest, retain_count=2)
    remaining = [p for p in dest.glob("*.zip")]
    assert len(remaining) == 2

def test_run_backup_succeeds(sched_svc, dest):
    sched_svc._run_backup(dest, retain_count=7)
    assert len(list(dest.glob("*.zip"))) == 1

def test_schedule_different_times(sched_svc, scheduler, dest):
    sched_svc.schedule(BackupScheduleConfig(enabled=True, hour=23, minute=59, dest_dir=str(dest)))
    assert "scheduled_backup" in scheduler.list_jobs()
