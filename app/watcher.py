"""File watcher for WoW Chat Log using watchdog."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class ChatLogHandler(FileSystemEventHandler):
    """Watches a single file for modifications and creation, reads new lines."""

    def __init__(self, file_path: Path, on_new_line: Callable[[str], None]) -> None:
        super().__init__()
        self._file_path = file_path
        self._on_new_line = on_new_line
        self._position: int = 0
        self._seek_to_end()

    def _seek_to_end(self) -> None:
        """Move position to end of file so we only get new lines."""
        try:
            self._position = self._file_path.stat().st_size
        except FileNotFoundError:
            self._position = 0

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

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory and os.path.normpath(event.src_path) == os.path.normpath(
            str(self._file_path)
        ):
            self._read_new_lines()

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory and os.path.normpath(event.src_path) == os.path.normpath(
            str(self._file_path)
        ):
            logger.info("Chat log file (re)created")
            self._position = 0
            self._read_new_lines()


class ChatLogWatcher:
    """Monitors WoWChatLog.txt for new lines using watchdog.

    Usage:
        def handle_line(line: str) -> None:
            print(line)

        watcher = ChatLogWatcher(Path("WoWChatLog.txt"), handle_line)
        watcher.start()
        # ... later ...
        watcher.stop()
    """

    def __init__(self, file_path: Path, on_new_line: Callable[[str], None]) -> None:
        self._file_path = file_path.resolve()
        self._handler = ChatLogHandler(self._file_path, on_new_line)
        self._observer = Observer()

    def start(self) -> None:
        """Start watching the chat log directory."""
        watch_dir = str(self._file_path.parent)
        self._observer.schedule(self._handler, watch_dir, recursive=False)
        self._observer.start()
        logger.info("Watching %s", self._file_path)

    def stop(self) -> None:
        """Stop watching."""
        self._observer.stop()
        self._observer.join(timeout=5)
        logger.info("Stopped watching")
