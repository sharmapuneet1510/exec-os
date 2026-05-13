import json
import logging
import os
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .model import BackupManifest

logger = logging.getLogger(__name__)

_APP_DIR = Path.home() / ".commanddesk"
_MANIFEST_FILE = "manifest.json"


class BackupService:
    """Creates, lists, and validates local data backups."""

    def __init__(self, app_dir: Path = _APP_DIR):
        self._app_dir = app_dir

    def create_backup(self, dest_dir: Path) -> BackupManifest:
        """
        Zip all CommandDesk data into dest_dir/<timestamp>_backup.zip.
        Returns a BackupManifest. Raises on failure.
        """
        dest_dir.mkdir(parents=True, exist_ok=True)
        backup_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        zip_path = dest_dir / f"{timestamp}_{backup_id[:8]}_backup.zip"

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                if self._app_dir.exists():
                    for file in self._app_dir.rglob("*"):
                        if file.is_file():
                            zf.write(file, file.relative_to(self._app_dir.parent))

            size = zip_path.stat().st_size
            manifest = BackupManifest(
                backup_id=backup_id,
                created_at=datetime.now(timezone.utc),
                path=str(zip_path),
                size_bytes=size,
                status="success",
            )
            self._write_manifest(dest_dir, manifest)
            logger.info("Backup created: %s (%d bytes)", zip_path, size)
            return manifest

        except Exception as exc:
            logger.error("Backup failed: %s", exc)
            manifest = BackupManifest(
                backup_id=backup_id,
                created_at=datetime.now(timezone.utc),
                path=str(zip_path),
                size_bytes=0,
                status="failed",
                error=str(exc),
            )
            self._write_manifest(dest_dir, manifest)
            raise

    def list_backups(self, dest_dir: Path) -> List[BackupManifest]:
        """Return all backup manifests found in dest_dir, newest first."""
        manifests = []
        if not dest_dir.exists():
            return manifests
        for p in dest_dir.glob("*_manifest.json"):
            with open(p, "r", encoding="utf-8") as f:
                manifests.append(BackupManifest.from_dict(json.load(f)))
        return sorted(manifests, key=lambda m: m.created_at, reverse=True)

    def validate_backup(self, backup_path: Path) -> bool:
        """Return True if the zip file is readable and non-empty."""
        if not backup_path.exists():
            return False
        try:
            with zipfile.ZipFile(backup_path, "r") as zf:
                return len(zf.namelist()) > 0
        except zipfile.BadZipFile:
            return False

    # ── Internal ──────────────────────────────────────────────────────────────

    def _write_manifest(self, dest_dir: Path, manifest: BackupManifest) -> None:
        p = dest_dir / f"{manifest.backup_id}_manifest.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2)
