import time
import threading
from typing import Any, Optional


class TTLCache:
    """Thread-safe in-memory cache with Time-To-Live (TTL) expiration."""

    def __init__(self, default_ttl: int = 60):
        self._default_ttl = default_ttl
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            value, expires_at = self._cache[key]
            if time.time() > expires_at:
                del self._cache[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl if ttl is not None else self._default_ttl
        with self._lock:
            expires_at = time.time() + ttl
            self._cache[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def count(self) -> int:
        with self._lock:
            now = time.time()
            return sum(1 for _, expires_at in self._cache.values() if expires_at > now)


class FirestoreReadCounter:
    """
    Tracks Firestore document reads performed by the web server
    to monitor the shared Spark free tier quota (50k reads/day).
    """

    def __init__(self):
        self._count = 0
        self._lock = threading.Lock()
        self._date = time.strftime("%Y-%m-%d")

    def increment(self, amount: int = 1) -> int:
        with self._lock:
            current_date = time.strftime("%Y-%m-%d")
            if current_date != self._date:
                self._date = current_date
                self._count = 0
            self._count += amount
            return self._count

    def get_count(self) -> int:
        with self._lock:
            current_date = time.strftime("%Y-%m-%d")
            if current_date != self._date:
                self._date = current_date
                self._count = 0
            return self._count


# Global singleton cache instances
user_cache = TTLCache(default_ttl=60)        # 60s for users/{uid}
config_cache = TTLCache(default_ttl=300)    # 5 min for config/app
counts_cache = TTLCache(default_ttl=60)     # 60s for aggregate count()
explore_cache = TTLCache(default_ttl=90)    # 90s for Explore feed pages
read_counter = FirestoreReadCounter()
