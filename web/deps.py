import time
from typing import Any, Optional

_store: dict[str, tuple[Any, float]] = {}


class _SimpleCache:
    def get(self, key: str) -> Optional[str]:
        entry = _store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            _store.pop(key, None)
            return None
        return value

    def setex(self, key: str, ttl: int, value: str) -> None:
        _store[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        _store.pop(key, None)


_cache = _SimpleCache()


def get_redis() -> _SimpleCache:
    return _cache
