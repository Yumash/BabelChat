"""Two-level translation cache: in-memory LRU + SQLite persistent."""

from __future__ import annotations

import logging
import sqlite3
import time
from collections import OrderedDict
from pathlib import Path

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS translations (
    source_text TEXT NOT NULL,
    source_lang TEXT NOT NULL,
    target_lang TEXT NOT NULL,
    translated TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY (source_text, source_lang, target_lang)
);
CREATE INDEX IF NOT EXISTS idx_created_at ON translations(created_at);
"""

CacheKey = tuple[str, str, str]  # (source_text, source_lang, target_lang)

DEFAULT_TTL = 7 * 24 * 3600  # 7 days
DEFAULT_MEMORY_SIZE = 1000
DEFAULT_DB_PATH = "translations.db"


class TranslationCache:
    """Two-level translation cache.

    Level 1: In-memory LRU OrderedDict (fast, volatile).
    Level 2: SQLite database (persistent, survives restart).
    """

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        memory_size: int = DEFAULT_MEMORY_SIZE,
        ttl: int = DEFAULT_TTL,
    ) -> None:
        self._memory_size = memory_size
        self._ttl = ttl
        self._memory: OrderedDict[CacheKey, tuple[str, float]] = OrderedDict()
        self._db_path = str(db_path)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)

    def get(self, text: str, source_lang: str, target_lang: str) -> str | None:
        """Look up translation in cache.

        Checks memory first, then SQLite. Returns None on miss.
        """
        key: CacheKey = (text, source_lang.upper(), target_lang.upper())

        # Level 1: memory
        if key in self._memory:
            value, created_at = self._memory[key]
            if time.time() - created_at > self._ttl:
                del self._memory[key]
            else:
                self._memory.move_to_end(key)
                return value

        # Level 2: SQLite
        row = self._conn.execute(
            "SELECT translated, created_at FROM translations "
            "WHERE source_text = ? AND source_lang = ? AND target_lang = ?",
            key,
        ).fetchone()

        if row is None:
            return None

        translated, created_at = row

        # Check TTL
        if time.time() - created_at > self._ttl:
            self._conn.execute(
                "DELETE FROM translations "
                "WHERE source_text = ? AND source_lang = ? AND target_lang = ?",
                key,
            )
            self._conn.commit()
            return None

        # Promote to memory
        self._memory_put(key, translated, created_at)
        return translated

    def put(self, text: str, source_lang: str, target_lang: str, translated: str) -> None:
        """Store translation in both cache levels."""
        key: CacheKey = (text, source_lang.upper(), target_lang.upper())
        now = time.time()

        # Level 1: memory
        self._memory_put(key, translated, now)

        # Level 2: SQLite
        self._conn.execute(
            "INSERT OR REPLACE INTO translations "
            "(source_text, source_lang, target_lang, translated, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (*key, translated, now),
        )
        self._conn.commit()

    def _memory_put(self, key: CacheKey, value: str, created_at: float | None = None) -> None:
        """Add to memory LRU, evicting oldest if full."""
        ts = created_at if created_at is not None else time.time()
        if key in self._memory:
            self._memory.move_to_end(key)
            self._memory[key] = (value, ts)
        else:
            if len(self._memory) >= self._memory_size:
                self._memory.popitem(last=False)
            self._memory[key] = (value, ts)

    def cleanup(self) -> int:
        """Remove expired entries from SQLite. Returns count of deleted rows."""
        cutoff = time.time() - self._ttl
        cursor = self._conn.execute(
            "DELETE FROM translations WHERE created_at < ?", (cutoff,)
        )
        self._conn.commit()
        deleted = cursor.rowcount
        if deleted:
            logger.info("Cleaned up %d expired translations", deleted)
        return deleted

    def stats(self) -> dict[str, int]:
        """Return cache statistics."""
        row = self._conn.execute("SELECT COUNT(*) FROM translations").fetchone()
        return {
            "memory_entries": len(self._memory),
            "memory_max": self._memory_size,
            "db_entries": row[0] if row else 0,
        }

    def close(self) -> None:
        """Close database connection."""
        self._conn.close()
