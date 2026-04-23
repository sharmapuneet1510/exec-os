import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Literal, Optional
from uuid import uuid4

Role = Literal["owner", "contributor", "reviewer", "observer"]
_DEFAULT_DIR = Path.home() / ".commanddesk" / "project_stakeholders"
_DEFAULT_NOTES_DIR = Path.home() / ".commanddesk" / "project_notes"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Stakeholder:
    project_id: str
    name: str
    email: str
    role: Role = "contributor"
    stakeholder_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict:
        return {
            "stakeholder_id": self.stakeholder_id,
            "project_id": self.project_id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Stakeholder":
        return cls(
            stakeholder_id=d["stakeholder_id"],
            project_id=d["project_id"],
            name=d["name"],
            email=d["email"],
            role=d.get("role", "contributor"),
        )


@dataclass
class ProjectNote:
    project_id: str
    content: str
    note_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=_now_iso)
    author: str = "user"

    def to_dict(self) -> dict:
        return {
            "note_id": self.note_id,
            "project_id": self.project_id,
            "content": self.content,
            "created_at": self.created_at,
            "author": self.author,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ProjectNote":
        return cls(
            note_id=d["note_id"],
            project_id=d["project_id"],
            content=d["content"],
            created_at=d.get("created_at", ""),
            author=d.get("author", "user"),
        )


class StakeholderStore:
    def __init__(self, store_dir: Path = _DEFAULT_DIR):
        self._dir = Path(store_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, project_id: str) -> Path:
        return self._dir / f"{project_id}.json"

    def _load(self, project_id: str) -> List[Stakeholder]:
        p = self._path(project_id)
        return [Stakeholder.from_dict(s) for s in json.loads(p.read_text())] if p.exists() else []

    def _save(self, project_id: str, stakeholders: List[Stakeholder]) -> None:
        self._path(project_id).write_text(json.dumps([s.to_dict() for s in stakeholders], indent=2))

    def add(self, stakeholder: Stakeholder) -> None:
        existing = self._load(stakeholder.project_id)
        existing.append(stakeholder)
        self._save(stakeholder.project_id, existing)

    def all_for_project(self, project_id: str) -> List[Stakeholder]:
        return self._load(project_id)

    def remove(self, project_id: str, stakeholder_id: str) -> bool:
        stakeholders = self._load(project_id)
        new = [s for s in stakeholders if s.stakeholder_id != stakeholder_id]
        if len(new) == len(stakeholders):
            return False
        self._save(project_id, new)
        return True

    def update_role(self, project_id: str, stakeholder_id: str, role: Role) -> bool:
        stakeholders = self._load(project_id)
        for s in stakeholders:
            if s.stakeholder_id == stakeholder_id:
                s.role = role
                self._save(project_id, stakeholders)
                return True
        return False


class ProjectNoteStore:
    def __init__(self, store_dir: Path = _DEFAULT_NOTES_DIR):
        self._dir = Path(store_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, project_id: str) -> Path:
        return self._dir / f"{project_id}.json"

    def _load(self, project_id: str) -> List[ProjectNote]:
        p = self._path(project_id)
        return [ProjectNote.from_dict(n) for n in json.loads(p.read_text())] if p.exists() else []

    def _save(self, project_id: str, notes: List[ProjectNote]) -> None:
        self._path(project_id).write_text(json.dumps([n.to_dict() for n in notes], indent=2))

    def add(self, note: ProjectNote) -> None:
        notes = self._load(note.project_id)
        notes.append(note)
        self._save(note.project_id, notes)

    def all_for_project(self, project_id: str) -> List[ProjectNote]:
        return self._load(project_id)

    def delete(self, project_id: str, note_id: str) -> bool:
        notes = self._load(project_id)
        new_notes = [n for n in notes if n.note_id != note_id]
        if len(new_notes) == len(notes):
            return False
        self._save(project_id, new_notes)
        return True


class StakeholderService:
    def __init__(
        self,
        stakeholder_store: Optional[StakeholderStore] = None,
        note_store: Optional[ProjectNoteStore] = None,
    ):
        self._stakeholders = stakeholder_store or StakeholderStore()
        self._notes = note_store or ProjectNoteStore()

    def add_stakeholder(self, project_id: str, name: str, email: str, role: Role = "contributor") -> Stakeholder:
        if not name or not name.strip():
            raise ValueError("stakeholder name must not be empty")
        if not email or "@" not in email:
            raise ValueError("invalid email address")
        s = Stakeholder(project_id=project_id, name=name.strip(), email=email.strip(), role=role)
        self._stakeholders.add(s)
        return s

    def list_stakeholders(self, project_id: str) -> List[Stakeholder]:
        return self._stakeholders.all_for_project(project_id)

    def remove_stakeholder(self, project_id: str, stakeholder_id: str) -> bool:
        return self._stakeholders.remove(project_id, stakeholder_id)

    def update_role(self, project_id: str, stakeholder_id: str, role: Role) -> bool:
        return self._stakeholders.update_role(project_id, stakeholder_id, role)

    def add_note(self, project_id: str, content: str, author: str = "user") -> ProjectNote:
        if not content or not content.strip():
            raise ValueError("note content must not be empty")
        note = ProjectNote(project_id=project_id, content=content.strip(), author=author)
        self._notes.add(note)
        return note

    def get_notes(self, project_id: str) -> List[ProjectNote]:
        return self._notes.all_for_project(project_id)

    def delete_note(self, project_id: str, note_id: str) -> bool:
        return self._notes.delete(project_id, note_id)
