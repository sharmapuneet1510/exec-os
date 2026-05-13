from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

BackupStatus = Literal["success", "failed", "in_progress"]


@dataclass
class BackupManifest:
    backup_id: str
    created_at: datetime
    path: str
    size_bytes: int
    status: BackupStatus
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "backup_id": self.backup_id,
            "created_at": self.created_at.isoformat(),
            "path": self.path,
            "size_bytes": self.size_bytes,
            "status": self.status,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BackupManifest":
        return cls(
            backup_id=d["backup_id"],
            created_at=datetime.fromisoformat(d["created_at"]),
            path=d["path"],
            size_bytes=int(d.get("size_bytes", 0)),
            status=d.get("status", "success"),
            error=d.get("error"),
        )
