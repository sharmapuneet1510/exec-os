import logging
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .service import BackupService

logger = logging.getLogger(__name__)

_APP_DIR = Path.home() / ".commanddesk"
_SAFETY_DIR = Path.home() / ".commanddesk_safety_backups"


@dataclass
class RestoreResult:
    success: bool
    safety_backup_path: Optional[str] = None
    restored_files: int = 0
    error: Optional[str] = None


class RestoreService:
    """
    Safely restores data from a backup zip.
    Always creates a safety backup of current data before overwriting.
    """

    def __init__(
        self,
        app_dir: Path = _APP_DIR,
        safety_dir: Path = _SAFETY_DIR,
        backup_service: Optional[BackupService] = None,
    ):
        self._app_dir = app_dir
        self._safety_dir = safety_dir
        self._backup_svc = backup_service or BackupService(app_dir=app_dir)

    def validate_backup(self, backup_path: Path) -> tuple[bool, Optional[str]]:
        """
        Returns (is_valid, error_message).
        Checks file exists, is a valid zip, and is non-empty.
        """
        if not backup_path.exists():
            return False, f"File not found: {backup_path}"
        if not zipfile.is_zipfile(backup_path):
            return False, "File is not a valid zip archive"
        with zipfile.ZipFile(backup_path, "r") as zf:
            if not zf.namelist():
                return False, "Backup archive is empty"
            bad = zf.testzip()
            if bad:
                return False, f"Corrupt file in archive: {bad}"
        return True, None

    def create_safety_backup(self) -> Path:
        """Zip current app data to safety dir before restore. Returns the zip path."""
        manifest = self._backup_svc.create_backup(self._safety_dir)
        logger.info("Safety backup created: %s", manifest.path)
        return Path(manifest.path)

    def restore(self, backup_path: Path, confirm: bool = False) -> RestoreResult:
        """
        Restore data from backup_path into app_dir.
        confirm=True is required to proceed (represents user confirmation).
        Creates a safety backup first.
        """
        if not confirm:
            return RestoreResult(success=False, error="Restore requires explicit confirmation (confirm=True)")

        valid, err = self.validate_backup(backup_path)
        if not valid:
            return RestoreResult(success=False, error=err)

        # Safety backup first
        try:
            safety_path = self.create_safety_backup()
        except Exception as exc:
            return RestoreResult(success=False, error=f"Safety backup failed: {exc}")

        # Extract
        try:
            with zipfile.ZipFile(backup_path, "r") as zf:
                members = zf.namelist()
                # Strip leading path component (the .commanddesk parent) on extraction
                for member in members:
                    p = Path(member)
                    # Rebase under app_dir: skip the first component (.commanddesk)
                    parts = p.parts
                    if len(parts) > 1:
                        dest = self._app_dir / Path(*parts[1:])
                    else:
                        dest = self._app_dir / p
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(dest, "wb") as dst:
                        dst.write(src.read())

            logger.info("Restore complete: %d files from %s", len(members), backup_path)
            return RestoreResult(
                success=True,
                safety_backup_path=str(safety_path),
                restored_files=len(members),
            )
        except Exception as exc:
            logger.error("Restore failed: %s", exc)
            return RestoreResult(
                success=False,
                safety_backup_path=str(safety_path),
                error=str(exc),
            )
