"""Read WoW chat messages from addon's in-memory buffer string.

The WoW addon (ChatTranslatorHelper) hooks CHAT_MSG_* events, serializes
each message into a ring buffer Lua string with unique markers:

    __WCT_BUF__<seq>|<channel>|<author>|<text>\n...\n__WCT_END__

This module finds that string in WoW's process memory via ReadProcessMemory
and delivers new messages to the translation pipeline.

No game-specific offsets needed — we search for our own markers.
Safety: Read-only memory access. Warden does not flag external ReadProcessMemory.
"""

from __future__ import annotations

import contextlib
import ctypes
import ctypes.wintypes
import logging
import threading
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)

# Markers written by the addon into ChatTranslatorHelperDB.wctbuf
MARKER_START = b"__WCT_BUF__"
MARKER_END = b"__WCT_END__"

# Polling and retry intervals
POLL_INTERVAL = 0.5  # 500ms between buffer reads
ATTACH_RETRY_INTERVAL = 5.0  # seconds between WoW attach attempts
SCAN_RETRY_INTERVAL = 3.0  # seconds between marker scan attempts
MAX_BUF_READ = 65536  # 64KB max read-ahead for the buffer

# Process names to try
WOW_PROCESS_NAMES = ["Wow.exe", "WowT.exe", "WowB.exe"]

# Memory region protection constants
_MEM_COMMIT = 0x1000
_PAGE_READWRITE = 0x04
_PAGE_READONLY = 0x02
_PAGE_EXECUTE_READ = 0x20
_PAGE_EXECUTE_READWRITE = 0x40
_PAGE_WRITECOPY = 0x08
_READABLE_PROTECT = {
    _PAGE_READWRITE, _PAGE_READONLY, _PAGE_EXECUTE_READ,
    _PAGE_EXECUTE_READWRITE, _PAGE_WRITECOPY,
}


class _MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", ctypes.wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", ctypes.wintypes.DWORD),
        ("Protect", ctypes.wintypes.DWORD),
        ("Type", ctypes.wintypes.DWORD),
    ]


# Channel name mapping: addon event name -> log format for synthetic lines
_ADDON_CHANNEL_TO_LOG: dict[str, str] = {
    "SAY": "Say",
    "YELL": "Yell",
    "PARTY": "Party",
    "PARTY_LEADER": "Party Leader",
    "RAID": "Raid",
    "RAID_LEADER": "Raid Leader",
    "RAID_WARNING": "Raid Warning",
    "GUILD": "Guild",
    "OFFICER": "Officer",
    "INSTANCE_CHAT": "Instance",
    "INSTANCE_CHAT_LEADER": "Instance Leader",
}


def _make_synthetic_log_line(channel: str, author: str, text: str) -> str | None:
    """Convert addon buffer entry to a WoW chat log line for parse_line().

    Returns a string in the format that parser.py already handles:
      - Channel messages: "M/D HH:MM:SS.000  [Channel] Author: text"
      - Whisper from:     "M/D HH:MM:SS.000  [Author] whispers: text"  (EN)
                          "M/D HH:MM:SS.000  [Author] шепчет: text"    (RU)
      - Whisper to:       "M/D HH:MM:SS.000  To [Author]: text"
    """
    t = time.localtime()
    ts = f"{t.tm_mon}/{t.tm_mday} {t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}.000"

    if channel == "WHISPER":
        # Incoming whisper: [Author-Server] whispers: text
        return f"{ts}  [{author}] whispers: {text}"
    if channel == "WHISPER_INFORM":
        # Outgoing whisper: To [Author-Server]: text
        return f"{ts}  To [{author}]: {text}"

    log_channel = _ADDON_CHANNEL_TO_LOG.get(channel)
    if log_channel is None:
        return None

    return f"{ts}  [{log_channel}] {author}: {text}"


class WoWAddonBufReader:
    """Reads chat messages from the WoW addon's in-memory buffer string.

    The addon writes a Lua string to ChatTranslatorHelperDB.wctbuf with
    markers __WCT_BUF__ and __WCT_END__. This reader finds and parses
    that string from WoW's process memory.
    """

    def __init__(self, on_new_line: Callable[[str], None]) -> None:
        self._on_new_line = on_new_line
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._pm = None  # pymem.Pymem instance
        self._attached = False
        self._last_seq = 0
        # Cached buffer location
        self._buf_addr: int = 0
        self._buf_region: tuple[int, int] = (0, 0)  # (base, size)

    @property
    def is_attached(self) -> bool:
        return self._attached

    def start(self) -> None:
        """Start the addon buffer reader polling thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Addon buffer reader thread started")

    def stop(self) -> None:
        """Stop the reader."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._detach()
        logger.info("Addon buffer reader stopped")

    def _run_loop(self) -> None:
        """Main loop: attach → find marker → poll → handle errors → retry."""
        while not self._stop_event.is_set():
            # Step 1: attach to WoW process
            if not self._attached:
                try:
                    self._attach()
                except Exception as e:
                    logger.info("Cannot attach to WoW: %s", e)
                    self._stop_event.wait(ATTACH_RETRY_INTERVAL)
                    continue

            # Step 2: find or verify the buffer marker
            if self._buf_addr == 0:
                try:
                    found = self._find_marker()
                except Exception as e:
                    logger.warning("Error scanning for marker: %s", e)
                    self._detach()
                    self._stop_event.wait(ATTACH_RETRY_INTERVAL)
                    continue

                if not found:
                    logger.debug("Addon buffer marker not found, retrying...")
                    self._stop_event.wait(SCAN_RETRY_INTERVAL)
                    continue

            # Step 3: read and deliver new messages
            try:
                self._poll_buffer()
            except Exception as e:
                logger.warning("Buffer read error: %s", e)
                self._buf_addr = 0  # invalidate cache, will rescan
                # Check if process is still alive
                try:
                    if self._pm:
                        self._pm.read_bytes(self._buf_region[0], 1)
                except Exception:
                    logger.info("WoW process gone, detaching")
                    self._detach()
                    self._stop_event.wait(ATTACH_RETRY_INTERVAL)
                    continue

            self._stop_event.wait(POLL_INTERVAL)

    # ------------------------------------------------------------------
    # Process attach/detach
    # ------------------------------------------------------------------

    def _attach(self) -> None:
        """Attach to WoW process via pymem."""
        import pymem
        import pymem.exception

        for proc_name in WOW_PROCESS_NAMES:
            try:
                self._pm = pymem.Pymem(proc_name)
                logger.info(
                    "Attached to %s (PID %d)",
                    proc_name, self._pm.process_id,
                )
                self._attached = True
                return
            except pymem.exception.ProcessNotFound:
                continue

        raise RuntimeError("WoW process not found")

    def _detach(self) -> None:
        """Detach from WoW process."""
        if self._pm:
            with contextlib.suppress(Exception):
                self._pm.close_process()
        self._pm = None
        self._attached = False
        self._buf_addr = 0
        self._buf_region = (0, 0)

    # ------------------------------------------------------------------
    # Marker search
    # ------------------------------------------------------------------

    def _find_marker(self) -> bool:
        """Search WoW's memory for the __WCT_BUF__ marker.

        If previously found in a specific region, search that region first.
        Falls back to full memory scan.
        """
        if not self._pm:
            return False

        # Try cached region first (Lua GC often reallocates in same area)
        if self._buf_region != (0, 0):
            addr = self._search_region_for_marker(*self._buf_region)
            if addr:
                self._buf_addr = addr
                logger.info(
                    "Marker re-found in cached region at 0x%X", addr,
                )
                return True

        # Full scan
        logger.info("Scanning WoW memory for addon buffer marker...")
        regions = self._get_memory_regions()
        for base, size in regions:
            addr = self._search_region_for_marker(base, size)
            if addr:
                self._buf_addr = addr
                self._buf_region = (base, size)
                logger.info(
                    "Marker found at 0x%X (region 0x%X, %d bytes)",
                    addr, base, size,
                )
                return True

        return False

    def _search_region_for_marker(self, base: int, size: int) -> int:
        """Search a single memory region for MARKER_START. Returns address or 0."""
        if not self._pm:
            return 0

        chunk_size = min(size, 4 * 1024 * 1024)  # read in 4MB chunks
        offset = 0

        while offset < size:
            read_size = min(chunk_size, size - offset)
            try:
                data = self._pm.read_bytes(base + offset, read_size)
            except Exception:
                break

            idx = data.find(MARKER_START)
            if idx != -1:
                return base + offset + idx

            # Overlap to avoid missing markers split across chunks
            offset += read_size - len(MARKER_START)

        return 0

    # ------------------------------------------------------------------
    # Buffer reading and parsing
    # ------------------------------------------------------------------

    def _poll_buffer(self) -> None:
        """Read the addon buffer from memory and deliver new messages."""
        if not self._pm or self._buf_addr == 0:
            return

        content = self._read_buffer_content()
        if content is None:
            return

        self._deliver_new_messages(content)

    def _read_buffer_content(self) -> str | None:
        """Read the buffer string between markers.

        Returns the content between __WCT_BUF__ and __WCT_END__,
        or None if the markers are no longer valid.
        """
        if not self._pm:
            return None

        try:
            raw = self._pm.read_bytes(self._buf_addr, MAX_BUF_READ)
        except Exception:
            self._buf_addr = 0
            return None

        # Verify the marker is still at our cached address
        if not raw.startswith(MARKER_START):
            logger.info("Marker moved (GC?), will rescan")
            self._buf_addr = 0
            return None

        # Find the end marker
        end_idx = raw.find(MARKER_END, len(MARKER_START))
        if end_idx == -1:
            # Buffer might be larger than MAX_BUF_READ, or corrupt
            logger.debug("End marker not found within %d bytes", MAX_BUF_READ)
            return None

        # Extract content between markers
        content_bytes = raw[len(MARKER_START):end_idx]

        try:
            return content_bytes.decode("utf-8", errors="replace")
        except Exception:
            return None

    def _deliver_new_messages(self, content: str) -> None:
        """Parse buffer content and deliver messages with seq > last_seq."""
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue

            # Parse: SEQ|CHANNEL|Author-Server|Text
            parts = line.split("|", 3)
            if len(parts) < 4:
                continue

            seq_str, channel, author, text = parts

            try:
                seq = int(seq_str)
            except ValueError:
                continue

            if seq <= self._last_seq:
                continue

            self._last_seq = seq

            # Convert to synthetic log line for parse_line()
            log_line = _make_synthetic_log_line(channel, author, text)
            if log_line:
                logger.debug("Addon msg #%d: %s", seq, log_line[:80])
                self._on_new_line(log_line)

    # ------------------------------------------------------------------
    # Low-level memory access
    # ------------------------------------------------------------------

    def _get_memory_regions(self) -> list[tuple[int, int]]:
        """Get readable memory regions of WoW process via VirtualQueryEx."""
        if not self._pm:
            return []

        regions: list[tuple[int, int]] = []
        kernel32 = ctypes.windll.kernel32
        mbi = _MEMORY_BASIC_INFORMATION()
        address = 0
        max_address = 0x7FFFFFFFFFFF  # 64-bit user space

        while address < max_address:
            result = kernel32.VirtualQueryEx(
                self._pm.process_handle,
                ctypes.c_void_p(address),
                ctypes.byref(mbi),
                ctypes.sizeof(mbi),
            )
            if result == 0:
                break

            if (
                mbi.State == _MEM_COMMIT
                and mbi.Protect in _READABLE_PROTECT
                and 0 < mbi.RegionSize <= 100 * 1024 * 1024
            ):
                regions.append((address, mbi.RegionSize))

            address += mbi.RegionSize
            if mbi.RegionSize == 0:
                address += 0x1000

        logger.debug("Found %d readable memory regions", len(regions))
        return regions


class MemoryChatWatcher:
    """High-level watcher: bridges WoWAddonBufReader to the pipeline.

    Produces synthetic chat log lines (same format as WoWChatLog.txt)
    so the pipeline's parse_line() works unchanged.
    """

    def __init__(self, on_new_line: Callable[[str], None]) -> None:
        self._on_new_line = on_new_line
        self._reader = WoWAddonBufReader(on_new_line=on_new_line)

    def start(self) -> None:
        """Start reading WoW chat from memory."""
        self._reader.start()

    def stop(self) -> None:
        """Stop reading."""
        self._reader.stop()

    @property
    def is_attached(self) -> bool:
        return self._reader.is_attached
