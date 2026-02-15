"""Tests for translation cache."""

import time

import pytest

from app.cache import TranslationCache


@pytest.fixture
def cache(tmp_path):
    """Create a cache with a temp DB."""
    db_path = tmp_path / "test_cache.db"
    c = TranslationCache(db_path=str(db_path), memory_size=3, ttl=2)
    yield c
    c.close()


class TestCacheBasic:
    """Test basic cache operations."""

    def test_miss_returns_none(self, cache):
        assert cache.get("hello", "EN", "RU") is None

    def test_put_and_get(self, cache):
        cache.put("hello", "EN", "RU", "привет")
        assert cache.get("hello", "EN", "RU") == "привет"

    def test_case_insensitive_lang(self, cache):
        cache.put("hello", "en", "ru", "привет")
        assert cache.get("hello", "EN", "RU") == "привет"

    def test_different_lang_pair_is_different(self, cache):
        cache.put("hello", "EN", "RU", "привет")
        cache.put("hello", "EN", "DE", "hallo")
        assert cache.get("hello", "EN", "RU") == "привет"
        assert cache.get("hello", "EN", "DE") == "hallo"

    def test_overwrite(self, cache):
        cache.put("hello", "EN", "RU", "привет")
        cache.put("hello", "EN", "RU", "здравствуйте")
        assert cache.get("hello", "EN", "RU") == "здравствуйте"


class TestCacheLRU:
    """Test LRU eviction in memory cache."""

    def test_eviction(self, cache):
        # Memory size is 3
        cache.put("a", "EN", "RU", "а")
        cache.put("b", "EN", "RU", "б")
        cache.put("c", "EN", "RU", "в")
        cache.put("d", "EN", "RU", "г")  # evicts "a" from memory

        # "a" should still be in SQLite
        assert cache.get("a", "EN", "RU") == "а"

    def test_access_refreshes_lru(self, cache):
        cache.put("a", "EN", "RU", "а")
        cache.put("b", "EN", "RU", "б")
        cache.put("c", "EN", "RU", "в")

        # Access "a" to refresh it
        cache.get("a", "EN", "RU")

        # Now "b" should be evicted first
        cache.put("d", "EN", "RU", "г")

        stats = cache.stats()
        assert stats["memory_entries"] == 3


class TestCacheTTL:
    """Test TTL-based expiration."""

    def test_expired_entry_returns_none(self, cache):
        cache.put("hello", "EN", "RU", "привет")
        time.sleep(2.5)  # TTL is 2 seconds
        assert cache.get("hello", "EN", "RU") is None

    def test_cleanup_removes_expired(self, cache):
        cache.put("hello", "EN", "RU", "привет")
        time.sleep(2.5)
        deleted = cache.cleanup()
        assert deleted == 1


class TestCacheStats:
    """Test cache statistics."""

    def test_empty_stats(self, cache):
        stats = cache.stats()
        assert stats["memory_entries"] == 0
        assert stats["db_entries"] == 0
        assert stats["memory_max"] == 3

    def test_stats_after_put(self, cache):
        cache.put("hello", "EN", "RU", "привет")
        stats = cache.stats()
        assert stats["memory_entries"] == 1
        assert stats["db_entries"] == 1


class TestCachePersistence:
    """Test that cache survives DB close/reopen."""

    def test_persistence(self, tmp_path):
        db_path = tmp_path / "persist.db"

        c1 = TranslationCache(db_path=str(db_path))
        c1.put("hello", "EN", "RU", "привет")
        c1.close()

        c2 = TranslationCache(db_path=str(db_path))
        assert c2.get("hello", "EN", "RU") == "привет"
        c2.close()
