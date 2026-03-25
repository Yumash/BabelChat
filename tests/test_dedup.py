"""Tests for DeduplicationBuffer."""

import threading
import time

from app.dedup import DeduplicationBuffer


def test_basic_duplicate():
    """Same key on second call returns True (duplicate)."""
    buf = DeduplicationBuffer()
    assert buf.is_duplicate(("Alice", "hello")) is False
    assert buf.is_duplicate(("Alice", "hello")) is True


def test_different_keys_not_duplicate():
    """Different keys are independent."""
    buf = DeduplicationBuffer()
    assert buf.is_duplicate(("Alice", "hello")) is False
    assert buf.is_duplicate(("Bob", "hello")) is False
    assert buf.is_duplicate(("Alice", "world")) is False


def test_ttl_expiry():
    """Entries expire after TTL, allowing re-insertion."""
    buf = DeduplicationBuffer(ttl=0.1)
    assert buf.is_duplicate(("Alice", "hello")) is False
    assert buf.is_duplicate(("Alice", "hello")) is True
    time.sleep(0.15)
    # After TTL, same key should be accepted again
    assert buf.is_duplicate(("Alice", "hello")) is False


def test_thread_safety():
    """Concurrent inserts from 10 threads should not raise or lose data."""
    buf = DeduplicationBuffer()
    results: list[bool] = [True] * 10
    barrier = threading.Barrier(10)

    def insert(idx: int) -> None:
        barrier.wait()
        results[idx] = buf.is_duplicate(("user", f"msg-{idx}"))

    threads = [threading.Thread(target=insert, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All 10 keys are unique, so none should be duplicate
    assert all(r is False for r in results)
