import json
from pathlib import Path

from .model import FocusState

_DEFAULT_PATH = Path.home() / ".commanddesk" / "focus_state.json"


class JSONFocusStore:
    def __init__(self, path: Path = _DEFAULT_PATH):
        self._path = path

    def load(self) -> FocusState:
        if not self._path.exists():
            return FocusState()
        with open(self._path, "r", encoding="utf-8") as f:
            return FocusState.from_dict(json.load(f))

    def save(self, state: FocusState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, indent=2)
