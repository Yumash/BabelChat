"""Message deduplication with TTL-based expiry."""

import threading
import time
from collections import OrderedDict

_DEDUP_TTL = 60.0  # seconds
_DEDUP_MAX_SIZE = 10000  # safety cap to prevent unbounded growth


class DeduplicationBuffer:
    """Thread-safe dedup buffer with TTL eviction."""

    def __init__(self, ttl: float = _DEDUP_TTL) -> None:
        self._ttl = ttl
        self._lock = threading.Lock()
        self._recent: OrderedDict[tuple[str, str], float] = OrderedDict()

    def is_duplicate(self, key: tuple[str, str]) -> bool:
        """Check if key was seen recently. If not, record it. Thread-safe."""
        now = time.monotonic()
        with self._lock:
            # Evict expired entries first so stale keys don't cause false dupes
            while self._recent:
                oldest_key, oldest_ts = next(iter(self._recent.items()))
                if now - oldest_ts > self._ttl:
                    self._recent.pop(oldest_key)
                else:
                    break
            if key in self._recent:
                return True
            self._recent[key] = now
            # Safety cap: prevent unbounded growth if eviction can't keep up
            while len(self._recent) > _DEDUP_MAX_SIZE:
                self._recent.popitem(last=False)
        return False
