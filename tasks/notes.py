import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

_DEFAULT_NOTES_DIR = Path.home() / ".commanddesk" / "task_notes"
_DEFAULT_HISTORY_DIR = Path.home() / ".commanddesk" / "task_history"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TaskNote:
    task_id: str
    content: str
    note_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict:
        return {
            "note_id": self.note_id,
            "task_id": self.task_id,
            "content": self.content,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TaskNote":
        return cls(
            note_id=d["note_id"],
            task_id=d["task_id"],
            content=d["content"],
            created_at=d.get("created_at", ""),
        )


@dataclass
class HistoryEvent:
    task_id: str
    event_type: str          # e.g. "status_changed", "field_updated", "note_added"
    description: str
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: str = field(default_factory=_now_iso)
    actor: str = "system"

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "task_id": self.task_id,
            "event_type": self.event_type,
            "description": self.description,
            "occurred_at": self.occurred_at,
            "actor": self.actor,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HistoryEvent":
        return cls(
            event_id=d["event_id"],
            task_id=d["task_id"],
            event_type=d["event_type"],
            description=d["description"],
            occurred_at=d.get("occurred_at", ""),
            actor=d.get("actor", "system"),
        )


class TaskNoteStore:
    def __init__(self, store_dir: Path = _DEFAULT_NOTES_DIR):
        self._dir = Path(store_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, task_id: str) -> Path:
        return self._dir / f"{task_id}.json"

    def _load_all(self, task_id: str) -> List[TaskNote]:
        p = self._path(task_id)
        if not p.exists():
            return []
        data = json.loads(p.read_text())
        return [TaskNote.from_dict(n) for n in data]

    def _save_all(self, task_id: str, notes: List[TaskNote]) -> None:
        self._path(task_id).write_text(json.dumps([n.to_dict() for n in notes], indent=2))

    def add(self, note: TaskNote) -> None:
        notes = self._load_all(note.task_id)
        notes.append(note)
        self._save_all(note.task_id, notes)

    def all_for_task(self, task_id: str) -> List[TaskNote]:
        return self._load_all(task_id)

    def delete(self, task_id: str, note_id: str) -> bool:
        notes = self._load_all(task_id)
        new_notes = [n for n in notes if n.note_id != note_id]
        if len(new_notes) == len(notes):
            return False
        self._save_all(task_id, new_notes)
        return True


class TaskHistoryStore:
    def __init__(self, store_dir: Path = _DEFAULT_HISTORY_DIR):
        self._dir = Path(store_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, task_id: str) -> Path:
        return self._dir / f"{task_id}.jsonl"

    def append(self, event: HistoryEvent) -> None:
        with open(self._path(event.task_id), "a") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    def all_for_task(self, task_id: str) -> List[HistoryEvent]:
        p = self._path(task_id)
        if not p.exists():
            return []
        events = []
        for line in p.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    events.append(HistoryEvent.from_dict(json.loads(line)))
                except (json.JSONDecodeError, KeyError):
                    pass
        return events


class TaskNoteService:
    def __init__(
        self,
        task_service,
        note_store: Optional[TaskNoteStore] = None,
        history_store: Optional[TaskHistoryStore] = None,
    ):
        self._tasks = task_service
        self._notes = note_store or TaskNoteStore()
        self._history = history_store or TaskHistoryStore()

    def add_note(self, task_id: str, content: str, actor: str = "user") -> TaskNote:
        if self._tasks.get(task_id) is None:
            raise KeyError(f"task {task_id!r} not found")
        if not content or not content.strip():
            raise ValueError("note content must not be empty")
        note = TaskNote(task_id=task_id, content=content.strip())
        self._notes.add(note)
        self._history.append(HistoryEvent(
            task_id=task_id, event_type="note_added",
            description=f"Note added: {content[:60]}", actor=actor,
        ))
        return note

    def get_notes(self, task_id: str) -> List[TaskNote]:
        return self._notes.all_for_task(task_id)

    def delete_note(self, task_id: str, note_id: str) -> bool:
        return self._notes.delete(task_id, note_id)

    def record_event(self, task_id: str, event_type: str, description: str, actor: str = "system") -> HistoryEvent:
        event = HistoryEvent(task_id=task_id, event_type=event_type, description=description, actor=actor)
        self._history.append(event)
        return event

    def get_history(self, task_id: str) -> List[HistoryEvent]:
        return self._history.all_for_task(task_id)
