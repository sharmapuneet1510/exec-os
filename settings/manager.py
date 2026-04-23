import json
import os
from pathlib import Path

from .model import UserSettings

_APP_DIR = Path.home() / ".commanddesk"
_SETTINGS_FILE = _APP_DIR / "settings.json"


class SettingsManager:
    def __init__(self, settings_path: Path = _SETTINGS_FILE):
        self._path = settings_path
        self._settings: UserSettings | None = None

    def is_first_run(self) -> bool:
        return not self._path.exists()

    def load(self) -> UserSettings:
        if self._path.exists():
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._settings = UserSettings.from_dict(data)
        else:
            self._settings = UserSettings()
        return self._settings

    def save(self, settings: UserSettings) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(settings.to_dict(), f, indent=2)
        self._settings = settings

    def get(self) -> UserSettings:
        if self._settings is None:
            return self.load()
        return self._settings

    def update(self, **kwargs) -> UserSettings:
        current = self.get()
        for key, value in kwargs.items():
            if not hasattr(current, key):
                raise ValueError(f"Unknown setting: {key}")
            setattr(current, key, value)
        self.save(current)
        return current

    def reset_to_defaults(self) -> UserSettings:
        defaults = UserSettings()
        self.save(defaults)
        return defaults
