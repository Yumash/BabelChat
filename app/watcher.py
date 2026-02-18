"""File watcher for WoW Chat Log using polling.

WoW buffers chat log writes, so filesystem events (watchdog) are unreliable.
Instead we poll the file size every POLL_INTERVAL seconds.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)

POLL_INTERVAL = 1.0  # seconds (addon flushes chat log every 5s)


class ChatLogWatcher:
    """Monitors WoWChatLog.txt for new lines by polling file size.

    Usage:
        watcher = ChatLogWatcher(Path("WoWChatLog.txt"), handle_line)
        watcher.start()
        # ... later ...
        watcher.stop()
    """

    def __init__(self, file_path: Path, on_new_line: Callable[[str], None]) -> None:
        self._file_path = file_path.resolve()
        self._on_new_line = on_new_line
        self._position: int = 0
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def read_tail(self, max_lines: int = 50) -> list[str]:
        """Read last N lines from the file (for history on startup)."""
        try:
            with open(self._file_path, encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
        except (FileNotFoundError, OSError):
            return []
        result = []
        for line in all_lines[-max_lines:]:
            stripped = line.strip()
            if stripped:
                result.append(stripped)
        return result

    def start(self) -> None:
        """Start polling the chat log file."""
        self._seek_to_end()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("Watching (poll) %s", self._file_path)

    def stop(self) -> None:
        """Stop polling."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Stopped watching")

    def _seek_to_end(self) -> None:
        """Move position to end of file so we only get new lines."""
        try:
            self._position = self._file_path.stat().st_size
        except FileNotFoundError:
            self._position = 0

    def _poll_loop(self) -> None:
        """Poll file for changes every POLL_INTERVAL seconds."""
        while not self._stop_event.is_set():
            self._read_new_lines()
            self._stop_event.wait(POLL_INTERVAL)

    def _read_new_lines(self) -> None:
        """Read any new lines from current position."""
        try:
            size = self._file_path.stat().st_size
        except FileNotFoundError:
            return

        # File was truncated or recreated — reset position
        if size < self._position:
            logger.info("File truncated or recreated, resetting position")
            self._position = 0

        if size == self._position:
            return

        try:
            with open(self._file_path, encoding="utf-8", errors="replace") as f:
                f.seek(self._position)
                data = f.read()
                self._position = f.tell()
        except (OSError, PermissionError) as e:
            logger.warning("Cannot read chat log: %s", e)
            return

        for line in data.splitlines():
            stripped = line.strip()
            if stripped:
                self._on_new_line(stripped)
