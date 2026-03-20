"""Read WoW chat messages from addon's in-memory buffer string.

Architecture (Pointer-Chasing with Tiered Scan Fallback):
    The addon stores chat messages in BabelChatDB.wctbuf as a Lua
    string with __WCT_BUF__/__WCT_END__ markers. Lua strings are immutable —
    every RebuildBuffer() creates a NEW string at a NEW address. The old string
    lingers until GC collects it.

    Primary strategy (pointer-chasing, ~1ms per poll):
    The Lua table BabelChatDB has a hash node whose value TValue
    points to the current wctbuf TString. The TABLE doesn't move — only the
    string pointer changes on each flush. After finding the buffer once via
    scan, we locate the hash node address and cache it. On every subsequent
    poll we read 8 bytes (the pointer) and follow it to the current string.
    This avoids scanning 3GB of memory on every flush cycle.

    Fallback strategy (tiered scan cascade, used when pointer is stale):
    0. Cached region scan: re-scan the SAME region (~50ms)
    1. History scan: check regions where markers were previously found (~30ms)
    1.5 Neighborhood scan: ±16MB around last known address (~200ms)
    2. Heap scan: all ≤8MB regions (~2.5s)
    3. Full pymem scan: last resort (~7s)

    Smart rescan: only triggered when buffer read fails or no new messages for
    >2s. When messages are flowing, no rescan overhead at all.

Safety: Read-only memory access. Warden does not flag external ReadProcessMemory.
"""

from __future__ import annotations

import contextlib
import ctypes
import ctypes.wintypes
import logging
import re
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Markers written by the addon into BabelChatDB.wctbuf
# v2.0: marker now includes seq number: __WCT_BUF_0042__
# We match the fixed prefix for scanning, then parse the full header.
MARKER_START = b"__WCT_BUF_"
MARKER_START_LEGACY = b"__WCT_BUF__"  # v1.x compat
MARKER_END = b"__WCT_END__"

# Polling and retry intervals
POLL_INTERVAL = 0.25  # 250ms between buffer reads (was 500ms)
ATTACH_RETRY_INTERVAL = 5.0  # seconds between WoW attach attempts
SCAN_RETRY_INTERVAL = 2.0  # seconds between marker scan attempts (match addon flush)
MAX_BUF_READ = 65536  # 64KB max read-ahead for the buffer
RAW_LOG_FILE = "babelchat_raw.log"  # debug log of all raw AddMessage lines

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

# Region history size — how many past marker regions to remember
_REGION_HISTORY_SIZE = 16

# Adaptive rescan intervals: ramp up when idle, reset on new messages
_RESCAN_INTERVALS = [2.0, 3.0, 5.0, 10.0]

# Compiled marker pattern: matches both v2 (__WCT_BUF_NNNN__) and v1 (__WCT_BUF__)
_MARKER_PATTERN = re.compile(rb"__WCT_BUF_[\d]{4}__|__WCT_BUF__")

# Neighborhood scan radius (bytes) for fast relocation after GC
_NEIGHBORHOOD_RADIUS = 16 * 1024 * 1024  # 16MB (was 4MB — wider net, still fast)


def _find_content_start(raw: bytes) -> int:
    """Find where buffer content starts after the marker header.

    Handles both v2 format (__WCT_BUF_0042__) and v1 (__WCT_BUF__).
    Returns offset to first byte after header, or -1 if no valid header found.
    """
    if raw.startswith(b"__WCT_BUF_"):
        # v2: __WCT_BUF_NNNN__ (16 bytes)
        end = raw.find(b"__", 10)
        if end != -1:
            return end + 2
    if raw.startswith(MARKER_START_LEGACY):
        return len(MARKER_START_LEGACY)
    return -1


def _has_marker_header(raw: bytes) -> bool:
    """Check if raw bytes start with a valid WCT buffer marker."""
    return raw.startswith(b"__WCT_BUF_") or raw.startswith(MARKER_START_LEGACY)


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


def _extract_max_seq(content: bytes) -> int:
    """Extract the highest sequence number from buffer content."""
    max_seq = 0
    for line in content.split(b"\n"):
        line = line.strip()
        if not line:
            continue
        idx = line.find(b"|")
        if idx <= 0:
            continue
        try:
            seq = int(line[:idx])
            if seq > max_seq:
                max_seq = seq
        except ValueError:
            continue
    return max_seq


def _is_system_noise(text: str) -> bool:
    """Quick check if AddMessage text is obvious system/addon noise."""
    t = re.sub(r"^\d{1,2}:\d{2}:\d{2}\s+", "", text.lstrip())
    if t.startswith(("<DBM>", "<BW>", "<WA>", "|TInterface", "[WCT]", "[MoveAny")):
        return True
    if "|Hachievement:" in t:
        return True
    if "заслужил" in t and "достижение" in t:
        return True
    if "has earned" in t and "achievement" in t:
        return True
    if " создает: " in t or " creates: " in t:
        return True
    if " производит " in t and " в звание " in t:
        return True
    if t.startswith(("Вы превращаете", "You convert")):
        return True
    if t.startswith((
        "Вы не состоите", "You are not in",
        "Смена канала", "Channel ",
        "Вы покинули канал", "You left channel",
        "Ведите себя", "Please keep",
        "Сообщение дня от гильдии", "Guild Message of the Day",
    )):
        return True
    if " ставит маяк " in t or " получает добычу" in t:
        return True
    if " получает предмет" in t or " receives loot" in t:
        return True
    if " засыпает." in t or " очищает " in t or " освобождает " in t:
        return True
    if " находит что-то " in t or " в панике пытается бежать" in t:
        return True
    return bool(t.startswith(("Получено:", "You receive")))


def _read_process_memory(handle: int, base: int, size: int) -> bytes | None:
    """Direct ReadProcessMemory via ctypes — releases GIL during kernel call."""
    buf = ctypes.create_string_buffer(size)
    bytes_read = ctypes.c_size_t(0)
    ok = ctypes.windll.kernel32.ReadProcessMemory(
        handle, ctypes.c_void_p(base), buf, size, ctypes.byref(bytes_read),
    )
    if ok and bytes_read.value > 0:
        return buf.raw[:bytes_read.value]
    return None


def _scan_region_batch(
    handle: int,
    regions: list[tuple[int, int]],
    min_seq: int = 0,
) -> tuple[int, int]:
    """Scan a batch of memory regions for the best (highest seq) marker.

    Two-phase scan: first read 4KB per region to find marker candidates,
    then read full buffer only for regions that contain the marker.
    This reduces total data from ~3GB to ~17MB (4250 regions × 4KB).

    Returns (best_addr, best_seq).
    """
    best_addr = 0
    best_seq = -1

    for base, size in regions:
        raw = _read_process_memory(handle, base, size)
        if raw is None:
            continue

        for match in _MARKER_PATTERN.finditer(raw):
            content_start = match.start()
            remaining = len(raw) - content_start
            chunk = raw[content_start:content_start + min(remaining, MAX_BUF_READ)]

            content_offset = _find_content_start(chunk)
            if content_offset == -1:
                continue
            marker_end = chunk.find(MARKER_END, content_offset)
            if marker_end == -1:
                continue

            content = chunk[content_offset:marker_end]
            max_seq = _extract_max_seq(content)
            if max_seq > best_seq and max_seq > min_seq:
                best_seq = max_seq
                best_addr = base + match.start()

    return best_addr, best_seq


def _scan_regions_for_marker(
    pm: object,
    regions: list[tuple[int, int]],
    min_seq: int = 0,
) -> int:
    """Scan memory regions for the best (highest seq) marker.

    Uses parallel threads for large region lists (>100 regions).
    Direct ctypes ReadProcessMemory releases GIL for true parallelism.

    Returns marker address or 0.
    """
    handle = pm.process_handle

    if len(regions) <= 100:
        addr, _seq = _scan_region_batch(handle, regions, min_seq)
        return addr

    # Measure total data volume
    total_bytes = sum(s for _, s in regions)

    # Split into chunks for parallel scanning
    n_workers = min(8, max(2, len(regions) // 500))
    chunk_size = (len(regions) + n_workers - 1) // n_workers
    chunks = [regions[i:i + chunk_size] for i in range(0, len(regions), chunk_size)]

    best_addr = 0
    best_seq = -1
    t0 = time.monotonic()

    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futures = [
            pool.submit(_scan_region_batch, handle, chunk, min_seq)
            for chunk in chunks
        ]
        for fut in as_completed(futures):
            try:
                addr, seq = fut.result()
                if seq > best_seq:
                    best_seq = seq
                    best_addr = addr
            except Exception:
                continue

    elapsed = time.monotonic() - t0
    logger.debug(
        "Parallel scan: %d regions, %d workers, %.1fMB total, %.0fms",
        len(regions), n_workers, total_bytes / 1024 / 1024, elapsed * 1000,
    )

    return best_addr


class WoWAddonBufReader:
    """Reads chat messages from the WoW addon's in-memory buffer string.

    Uses tiered scan cascade with cached region priority:
    0. Cached region scan (~50ms) — same region where buffer was last found
    1. History scan (~30ms) — regions where markers were previously found
    1.5 Neighborhood scan (~200ms) — ±16MB around last known address
    2. Heap scan (~2.5s) — all ≤8MB regions
    3. Full pymem scan (~7s) — last resort

    Fast path on stale: when buffer read fails (marker gone), immediately
    tries cached region + neighborhood + history before falling back to
    expensive heap/full scans. Smart rescan only triggers when no new
    messages for >2s, avoiding overhead when messages are actively flowing.
    """

    def __init__(self, on_new_line: Callable[..., None]) -> None:
        self._on_new_line = on_new_line
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._pm = None  # pymem.Pymem instance
        self._attached = False
        self._last_seq = 0
        self._player_name: str = ""

        # Current marker address and its region
        self._buf_addr: int = 0
        self._cached_region: tuple[int, int] | None = None  # (base, size)
        self._all_regions: list[tuple[int, int]] = []  # sorted by base addr
        self._cached_region_index: int = -1  # index in _all_regions

        # Region history: regions where markers were previously found.
        # Lua tends to reuse the same heap segments, so scanning these first
        # is much faster than scanning all regions.
        self._region_history: list[tuple[int, int]] = []

        # Track consecutive stale reads to trigger rescan (with backoff)
        self._stale_count: int = 0
        self._stale_tier: int = 0  # exponential backoff tier for marker-gone

        # Seq freshness: detect frozen buffer (readable but outdated)
        # Tracks last 3 max_seq values read from buffer. If unchanged for 3
        # consecutive reads while messages should be flowing, the buffer is
        # likely a zombie (GC'd string still in memory).
        self._seq_history: list[int] = []  # last 3 seq values
        self._frozen_count: int = 0  # consecutive polls with same seq

        # Blacklisted addresses with TTL: zombie markers expire after 60s
        # so GC-reused memory regions can be re-scanned.
        self._blacklisted_addrs: dict[int, float] = {}  # addr -> expiry monotonic time
        self._blacklist_ttl: float = 60.0

        # Seq reset guard: track actually delivered payloads to avoid re-delivery
        self._delivered_payloads: set[str] = set()
        self._pre_reset_texts: set[str] = set()
        self._pre_reset_expire: float = 0.0

        # Periodic rescan: check if a newer buffer exists every N seconds.
        self._last_rescan: float = 0.0
        self._rescan_interval: float = 2.0  # match addon FLUSH_INTERVAL
        self._same_addr_count: int = 0  # consecutive rescans finding same addr

        # Smart rescan: track when we last got new messages
        self._last_new_msg_time: float = 0.0

        # Pointer-chasing: address of the Lua table hash node that holds the
        # pointer to the current wctbuf string.  Once found, we read 8 bytes
        # here on every poll (~1ms) instead of scanning 3GB of memory.
        self._ptr_addr: int = 0
        # Offset from TString header start to the marker content within the string
        self._ptr_offset: int = 0

    def _is_blacklisted(self, addr: int) -> bool:
        """Check if address is blacklisted (with TTL expiry)."""
        if addr not in self._blacklisted_addrs:
            return False
        if time.monotonic() > self._blacklisted_addrs[addr]:
            del self._blacklisted_addrs[addr]
            return False
        return True

    @property
    def is_attached(self) -> bool:
        return self._attached

    @property
    def player_name(self) -> str:
        return self._player_name

    def start(self) -> None:
        """Start the addon buffer reader polling thread."""
        # Truncate raw debug log on start (prevents unbounded growth)
        with contextlib.suppress(OSError):
            open(RAW_LOG_FILE, "w").close()
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
        """Main loop: attach → find marker → poll → rescan on stale."""
        while not self._stop_event.is_set():
            # Step 1: attach to WoW process
            if not self._attached:
                try:
                    self._attach()
                except Exception as e:
                    logger.info("Cannot attach to WoW: %s", e)
                    self._stop_event.wait(ATTACH_RETRY_INTERVAL)
                    continue

            # Step 2: find marker if we don't have one
            if self._buf_addr == 0:
                try:
                    found = self._find_marker()
                except Exception as e:
                    logger.warning("Marker scan error: %s", e)
                    if not self._is_process_alive():
                        logger.info("WoW process gone, detaching")
                        self._detach()
                    self._stop_event.wait(SCAN_RETRY_INTERVAL)
                    continue

                if not found:
                    self._stop_event.wait(SCAN_RETRY_INTERVAL)
                    continue

            # Step 3: read buffer and deliver messages
            try:
                self._poll_buffer()
            except Exception as e:
                logger.warning("Buffer read error: %s", e)
                if not self._is_process_alive():
                    logger.info("WoW process gone, detaching")
                    self._detach()
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
                # Cache memory regions for fast rescans
                self._all_regions = self._get_memory_regions()
                logger.info("Cached %d readable memory regions", len(self._all_regions))
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
        self._cached_region = None
        self._cached_region_index = -1
        self._all_regions = []
        self._stale_count = 0
        self._ptr_addr = 0
        self._ptr_offset = 0

    def _is_process_alive(self) -> bool:
        """Check if the WoW process is still accessible."""
        if not self._pm:
            return False
        try:
            self._pm.read_bytes(self._pm.base_address, 1)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Memory region enumeration
    # ------------------------------------------------------------------

    def _get_memory_regions(self) -> list[tuple[int, int]]:
        """Get readable memory regions of WoW process via VirtualQueryEx.

        Returns list of (base_address, region_size) sorted by base address.
        """
        if not self._pm:
            return []

        regions: list[tuple[int, int]] = []
        kernel32 = ctypes.windll.kernel32
        mbi = _MEMORY_BASIC_INFORMATION()
        address = 0
        max_address = 0x7FFFFFFFFFFF

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

        regions.sort(key=lambda r: r[0])
        return regions

    def _find_region_for_addr(self, addr: int) -> tuple[int, int, int] | None:
        """Find which cached region contains the given address.

        Returns (region_base, region_size, index_in_all_regions) or None.
        """
        for i, (base, size) in enumerate(self._all_regions):
            if base <= addr < base + size:
                return base, size, i
        return None

    # ------------------------------------------------------------------
    # Region history
    # ------------------------------------------------------------------

    def _record_region_hit(self, base: int, size: int) -> None:
        """Record a region where a marker was successfully found.

        Move-to-front if already present; bounded to _REGION_HISTORY_SIZE.
        """
        entry = (base, size)
        if entry in self._region_history:
            self._region_history.remove(entry)
        self._region_history.insert(0, entry)
        if len(self._region_history) > _REGION_HISTORY_SIZE:
            self._region_history.pop()

    def _update_cached_region(self, addr: int) -> None:
        """Update the cached region to the one containing addr."""
        region_info = self._find_region_for_addr(addr)
        if region_info:
            base, size, idx = region_info
            self._cached_region = (base, size)
            self._cached_region_index = idx

    def _record_hit_from_addr(self, addr: int) -> None:
        """Record the region containing addr in history + update cache."""
        region_info = self._find_region_for_addr(addr)
        if region_info:
            base, size, idx = region_info
            self._cached_region = (base, size)
            self._cached_region_index = idx
            self._record_region_hit(base, size)

    def _try_setup_pointer(self, buf_addr: int) -> None:
        """Try to set up pointer-chasing for fast buffer reads.

        Called after a successful marker find.  Runs pointer search in the
        background to avoid blocking the poll loop.  If it fails, we just
        keep using the normal scan-based approach.
        """
        # Pointer chasing disabled — needs more research on WoW's Lua internals.
        # TODO: implement in separate branch with proper two-pass verification.
        pass

    # ------------------------------------------------------------------
    # Pointer-chasing: find & use the hash node pointer to the buffer
    # ------------------------------------------------------------------

    def _find_ptr_to_buffer(self, buf_addr: int) -> bool:
        """Find the Lua table hash node via two-pass verification.

        Pass 1: find buffer at addr A, collect all pointer candidates to A.
        Pass 2: wait for addon flush (new buffer at addr B), check which
                 candidate now points to B.  That's the real hash node.

        This eliminates false positives (stack refs, backup copies) because
        only the table hash node updates when the addon assigns a new string.

        Args:
            buf_addr: address of the marker text (__WCT_BUF_...) in memory.

        Returns:
            True if a valid pointer was found and cached.
        """
        if not self._pm:
            return False

        handle = self._pm.process_handle
        t0 = time.monotonic()

        # Step 1: collect all pointers to buf_addr (with TString header offsets)
        # WoW's modified Lua 5.1 TString header size is unknown — try wide range
        candidate_offsets = list(range(0, 96, 8))
        candidates: list[tuple[int, bytes]] = []
        for off in candidate_offsets:
            tstring_addr = buf_addr - off
            if tstring_addr > 0:
                candidates.append((off, tstring_addr.to_bytes(8, "little")))

        # Scan all heap regions ≤8MB
        rw_regions = [
            (b, s) for b, s in self._all_regions if s <= 8 * 1024 * 1024
        ]

        logger.info(
            "Pointer search pass 1: scanning %d regions (buf=0x%X)",
            len(rw_regions), buf_addr,
        )

        # Parallel scan using C-speed bytes.find() for each pattern
        def _search_batch(regions: list[tuple[int, int]]) -> list[tuple[int, int]]:
            results: list[tuple[int, int]] = []
            for base, size in regions:
                raw = _read_process_memory(handle, base, size)
                if raw is None:
                    continue
                for off, pattern in candidates:
                    pos = 0
                    while True:
                        idx = raw.find(pattern, pos)
                        if idx == -1:
                            break
                        if idx % 8 == 0:  # pointers are 8-byte aligned
                            results.append((base + idx, off))
                        pos = idx + 1
            return results

        pass1_matches: list[tuple[int, int]] = []
        if len(rw_regions) > 100:
            n_workers = min(8, max(2, len(rw_regions) // 500))
            chunk_size = (len(rw_regions) + n_workers - 1) // n_workers
            chunks = [rw_regions[i:i + chunk_size] for i in range(0, len(rw_regions), chunk_size)]
            with ThreadPoolExecutor(max_workers=n_workers) as pool:
                futures = [pool.submit(_search_batch, chunk) for chunk in chunks]
                for fut in as_completed(futures):
                    with contextlib.suppress(Exception):
                        pass1_matches.extend(fut.result())
        else:
            pass1_matches = _search_batch(rw_regions)

        elapsed1 = time.monotonic() - t0
        logger.info(
            "Pointer search pass 1: %d candidates in %.0fms",
            len(pass1_matches), elapsed1 * 1000,
        )

        if not pass1_matches:
            return False

        # Step 2: wait for the addon to flush a NEW buffer (new string addr)
        # Poll for up to 10 seconds watching for the buffer to move
        logger.info("Pointer search pass 2: waiting for buffer flush...")
        new_buf_addr = 0
        wait_start = time.monotonic()
        while time.monotonic() - wait_start < 10.0:
            time.sleep(0.5)
            # Try to find a newer buffer via scan
            self._all_regions = self._get_memory_regions()
            new_addr = self._scan_heap_regions(min_seq=0)
            if new_addr and new_addr != buf_addr:
                # Verify it's a valid buffer
                raw = _read_process_memory(handle, new_addr, MAX_BUF_READ)
                if raw and raw.find(MARKER_START) != -1 and raw.find(MARKER_END) != -1:
                    new_buf_addr = new_addr
                    break

        if not new_buf_addr:
            logger.info("Pointer search pass 2: buffer didn't move in 10s, giving up")
            return False

        elapsed2 = time.monotonic() - t0
        logger.info(
            "Pointer search pass 2: buffer moved 0x%X → 0x%X (%.0fms)",
            buf_addr, new_buf_addr, elapsed2 * 1000,
        )

        # Step 3: check which pass1 candidates now point to the NEW buffer
        for ptr_addr, off in pass1_matches:
            try:
                ptr_bytes = _read_process_memory(handle, ptr_addr, 8)
                if ptr_bytes is None or len(ptr_bytes) < 8:
                    continue
                target = int.from_bytes(ptr_bytes, "little")
                if target == 0:
                    continue

                # The target should point to TString of the NEW buffer
                expected_tstring = new_buf_addr - off
                if target != expected_tstring:
                    continue

                # Final verify: follow pointer and check marker
                target_raw = _read_process_memory(handle, target, MAX_BUF_READ)
                if target_raw is None:
                    continue
                marker_pos = target_raw.find(MARKER_START, 0, 64)
                if marker_pos == -1:
                    continue
                end_pos = target_raw.find(MARKER_END, marker_pos)
                if end_pos == -1:
                    continue

                # This is the REAL hash node pointer!
                self._ptr_addr = ptr_addr
                self._ptr_offset = marker_pos
                self._buf_addr = new_buf_addr

                elapsed_total = time.monotonic() - t0
                logger.info(
                    "Pointer VERIFIED & CACHED at 0x%X "
                    "(offset=%d, marker_pos=%d, %.0fms total, "
                    "%d candidates checked)",
                    ptr_addr, off, marker_pos,
                    elapsed_total * 1000, len(pass1_matches),
                )
                return True
            except Exception:
                continue

        elapsed_total = time.monotonic() - t0
        logger.info(
            "Pointer search: no candidate updated to new buffer (%.0fms)",
            elapsed_total * 1000,
        )
        return False

    def _read_buffer_via_ptr(self) -> str | None:
        """Fast-path buffer read: follow the cached pointer to the current string.

        Reads 8 bytes at self._ptr_addr to get the TString pointer, then reads
        MAX_BUF_READ bytes from the TString and extracts the buffer content.

        Returns buffer content string, or None if the pointer is stale.
        """
        if not self._pm or self._ptr_addr == 0:
            return None

        handle = self._pm.process_handle

        # Step 1: Read the pointer (8 bytes)
        ptr_bytes = _read_process_memory(handle, self._ptr_addr, 8)
        if ptr_bytes is None or len(ptr_bytes) < 8:
            logger.debug("Pointer read failed at 0x%X", self._ptr_addr)
            return None

        target = int.from_bytes(ptr_bytes, "little")
        if target == 0:
            logger.debug("Pointer at 0x%X is null", self._ptr_addr)
            return None

        # Step 2: Read the TString content
        raw = _read_process_memory(handle, target, MAX_BUF_READ)
        if raw is None:
            logger.debug(
                "Pointer read: 0x%X -> target 0x%X unreadable",
                self._ptr_addr, target,
            )
            return None

        # Step 3: Find the marker within the TString
        # Use cached offset as a hint, but also search if not found there
        marker_pos = -1
        if self._ptr_offset < len(raw) and raw[self._ptr_offset:].startswith(MARKER_START):
            marker_pos = self._ptr_offset
        else:
            marker_pos = raw.find(MARKER_START, 0, 64)

        if marker_pos == -1:
            logger.debug(
                "Pointer read: 0x%X -> 0x%X no marker (first 64b: %r)",
                self._ptr_addr, target, raw[:64],
            )
            return None

        chunk = raw[marker_pos:]
        co = _find_content_start(chunk)
        if co == -1:
            return None

        end_idx = chunk.find(MARKER_END, co)
        if end_idx == -1:
            return None

        content_bytes = chunk[co:end_idx]

        # Update _buf_addr to the marker address in case fallback code needs it
        new_buf_addr = target + marker_pos
        if new_buf_addr != self._buf_addr:
            logger.info(
                "Pointer read: buffer moved 0x%X -> 0x%X (via ptr 0x%X)",
                self._buf_addr, new_buf_addr, self._ptr_addr,
            )
            self._buf_addr = new_buf_addr
            self._record_hit_from_addr(new_buf_addr)

        try:
            return content_bytes.decode("utf-8", errors="replace")
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Marker scanning (tiered cascade)
    # ------------------------------------------------------------------

    def _scan_cached_region(self, min_seq: int = 0) -> int:
        """Fast scan of the cached region only (~50ms).

        Lua often allocates new strings in the same heap region. This is a
        single ReadProcessMemory call + string search — extremely fast.

        Returns marker address or 0.
        """
        if not self._pm or not self._cached_region:
            return 0

        base, size = self._cached_region
        t0 = time.monotonic()
        addr = _scan_regions_for_marker(self._pm, [self._cached_region], min_seq=min_seq)
        elapsed = time.monotonic() - t0

        if addr and addr not in self._blacklisted_addrs:
            logger.info(
                "Cached region scan HIT: marker at 0x%X (%.0fms)",
                addr, elapsed * 1000,
            )
            return addr

        logger.debug("Cached region scan MISS (%.0fms)", elapsed * 1000)
        return 0

    def _fast_relocate_buffer(self, min_seq: int = 0) -> int:
        """Fast path: try cached region + neighborhood before expensive scans.

        Called immediately when _read_buffer() returns None (marker gone).
        Returns new marker address or 0.
        """
        if not self._pm:
            return 0

        # Step 1: Cached region scan (~50ms)
        addr = self._scan_cached_region(min_seq=min_seq)
        if addr and addr != self._buf_addr:
            return addr

        # Step 2: Neighborhood scan (~200ms)
        if self._buf_addr:
            addr = self._neighborhood_scan(self._buf_addr, min_seq=min_seq)
            if addr and addr not in self._blacklisted_addrs and addr != self._buf_addr:
                return addr

        # Step 3: History scan (~30ms)
        if self._region_history:
            addr = _scan_regions_for_marker(self._pm, self._region_history, min_seq=min_seq)
            if addr and addr not in self._blacklisted_addrs and addr != self._buf_addr:
                return addr

        return 0

    def _find_marker(self, min_seq: int = 0) -> bool:
        """Find the __WCT_BUF__ marker using tiered scan cascade.

        Args:
            min_seq: only accept markers with max_seq > min_seq.

        Cascade:
        0. Cached region scan (~50ms) — same region, new string
        1. History scan (~30ms) — regions where markers were previously found
        1.5 Neighborhood scan (~200ms) — ±16MB around last known address
        2. Heap scan (~2.5s) — all ≤8MB regions
        3. Full pymem scan (~7s) — last resort
        """
        if not self._pm:
            return False

        # Tier 0: Cached region scan (fastest, ~50ms)
        if self._cached_region:
            t0 = time.monotonic()
            addr = self._scan_cached_region(min_seq=min_seq)
            if addr and addr not in self._blacklisted_addrs:
                self._buf_addr = addr
                self._stale_count = 0
                self._record_hit_from_addr(addr)
                self._maybe_skip_existing(addr)
                self._try_setup_pointer(addr)
                return True

        # Tier 1: History scan (very fast, ~30ms)
        if self._region_history:
            t0 = time.monotonic()
            addr = _scan_regions_for_marker(
                self._pm, self._region_history, min_seq=min_seq,
            )
            elapsed = time.monotonic() - t0
            if addr and addr not in self._blacklisted_addrs:
                logger.info(
                    "History scan HIT: marker at 0x%X (%.0fms)",
                    addr, elapsed * 1000,
                )
                self._buf_addr = addr
                self._stale_count = 0
                self._record_hit_from_addr(addr)
                self._maybe_skip_existing(addr)
                self._try_setup_pointer(addr)
                return True
            logger.info("History scan MISS (%.0fms)", elapsed * 1000)

        # Tier 1.5: Neighborhood scan (~200ms) — if we have a last known address
        if self._buf_addr:
            t0 = time.monotonic()
            addr = self._neighborhood_scan(self._buf_addr, min_seq=min_seq)
            elapsed = time.monotonic() - t0
            if addr and addr not in self._blacklisted_addrs:
                logger.info(
                    "Neighborhood scan HIT in _find_marker: 0x%X (%.0fms)",
                    addr, elapsed * 1000,
                )
                self._buf_addr = addr
                self._stale_count = 0
                self._record_hit_from_addr(addr)
                self._maybe_skip_existing(addr)
                self._try_setup_pointer(addr)
                return True
            logger.info("Neighborhood scan MISS in _find_marker (%.0fms)", elapsed * 1000)

        # Tier 2: Heap scan (~2.5s)
        self._all_regions = self._get_memory_regions()
        t0 = time.monotonic()
        addr = self._scan_heap_regions(min_seq=min_seq)
        elapsed = time.monotonic() - t0
        if addr and addr not in self._blacklisted_addrs:
            logger.info(
                "Heap scan HIT: marker at 0x%X (%.1fs)",
                addr, elapsed,
            )
            self._buf_addr = addr
            self._stale_count = 0
            self._record_hit_from_addr(addr)
            self._maybe_skip_existing(addr)
            self._try_setup_pointer(addr)
            return True
        logger.info("Heap scan MISS (%.1fs)", elapsed)

        # Tier 3: Full pymem scan (~7s, last resort)
        t0 = time.monotonic()
        addr = self._full_marker_scan(min_seq=min_seq)
        elapsed = time.monotonic() - t0
        if addr and addr not in self._blacklisted_addrs:
            logger.info(
                "Full scan: marker at 0x%X (%.1fs)", addr, elapsed,
            )
            self._buf_addr = addr
            self._stale_count = 0
            self._record_hit_from_addr(addr)
            self._maybe_skip_existing(addr)
            self._try_setup_pointer(addr)
            return True

        logger.warning("All scans failed: marker not found (%.1fs total)", elapsed)
        return False

    def _maybe_skip_existing(self, addr: int) -> None:
        """Skip existing buffer history on first connect."""
        if self._last_seq != 0:
            return
        try:
            raw = self._pm.read_bytes(addr, MAX_BUF_READ)
            co = _find_content_start(raw)
            if co != -1:
                end_idx = raw.find(MARKER_END, co)
                if end_idx != -1:
                    content = raw[co:end_idx].decode("utf-8", errors="replace")
                    # Parse META lines (e.g. player name)
                    for line in content.splitlines():
                        parts = line.strip().split("|", 2)
                        if len(parts) >= 3 and parts[1] == "META":
                            meta = parts[2].split("|", 1)
                            if meta[0] == "PLAYER" and len(meta) > 1:
                                name = meta[1].strip()
                                if name:
                                    self._player_name = name
                                    logger.info("Player name from addon: %s", name)
                    max_seq = _extract_max_seq(raw[co:end_idx])
                    if max_seq > 0:
                        self._last_seq = max_seq
                        logger.info("Skipping existing buffer (last_seq=%d)", max_seq)
        except Exception:
            pass

    def _full_marker_scan(self, min_seq: int = 0) -> int:
        """Full process scan for the marker via pymem.

        Returns the address of the best (highest seq) marker, or 0.
        """
        if not self._pm:
            return 0

        logger.info("Full scan: searching for addon buffer marker...")

        import pymem.pattern
        try:
            addrs = pymem.pattern.pattern_scan_all(
                self._pm.process_handle,
                rb"__WCT_BUF_",  # Matches both v2 (__WCT_BUF_NNNN__) and prefix of v1
                return_multiple=True,
            )
        except Exception as e:
            logger.warning("pattern_scan_all failed: %s", e)
            return 0

        if not addrs:
            return 0

        logger.info("Full scan: found %d raw matches, min_seq=%d", len(addrs), min_seq)

        best_addr = 0
        best_seq = -1
        for a in addrs:
            if a in self._blacklisted_addrs:
                continue
            try:
                raw = self._pm.read_bytes(a, MAX_BUF_READ)
            except Exception:
                continue
            co = _find_content_start(raw)
            if co == -1:
                logger.debug("Full scan: 0x%X — no header, first 40b: %r", a, raw[:40])
                continue
            end_idx = raw.find(MARKER_END, co)
            if end_idx == -1:
                logger.debug("Full scan: 0x%X — no END, content preview: %r", a, raw[co:co+100])
                continue
            content = raw[co:end_idx]
            max_seq = _extract_max_seq(content)
            logger.debug("Full scan: 0x%X — seq=%d, content_len=%d", a, max_seq, len(content))
            if max_seq > best_seq and max_seq > min_seq:
                best_seq = max_seq
                best_addr = a

        if best_addr:
            logger.info(
                "Full scan: best marker at 0x%X (max_seq=%d, %d candidates)",
                best_addr, best_seq, len(addrs),
            )
        return best_addr

    def _quick_rescan_for_newer_buffer(self) -> None:
        """Fast rescan: cached region + history only (~50-100ms).

        Used for periodic checks.  Does NOT do expensive heap/full scans.
        Falls back to full _check_for_newer_buffer after repeated misses.
        """
        if not self._pm:
            return

        t0 = time.monotonic()
        new_addr = 0

        # Try cached region first
        if self._cached_region:
            new_addr = self._scan_cached_region()
            if new_addr in self._blacklisted_addrs or new_addr == self._buf_addr:
                new_addr = 0

        # Try history regions
        if not new_addr and self._region_history:
            new_addr = _scan_regions_for_marker(self._pm, self._region_history)
            if new_addr in self._blacklisted_addrs or new_addr == self._buf_addr:
                new_addr = 0

        elapsed = time.monotonic() - t0

        if new_addr and new_addr != self._buf_addr:
            logger.info(
                "Quick rescan HIT: 0x%X → 0x%X (%.0fms)",
                self._buf_addr, new_addr, elapsed * 1000,
            )
            self._buf_addr = new_addr
            self._stale_count = 0
            self._stale_tier = 0
            self._same_addr_count = 0
            self._frozen_count = 0
            self._rescan_interval = _RESCAN_INTERVALS[0]
            self._record_hit_from_addr(new_addr)
            self._try_setup_pointer(new_addr)
        else:
            self._same_addr_count += 1
            # After 2 quick misses, do a full rescan
            if self._same_addr_count >= 2 and self._same_addr_count % 2 == 0:
                self._check_for_newer_buffer()
            else:
                tier = min(self._same_addr_count // 3, len(_RESCAN_INTERVALS) - 1)
                self._rescan_interval = _RESCAN_INTERVALS[tier]

    def _check_for_newer_buffer(self) -> None:
        """Full rescan: try all scan tiers including expensive heap scan.

        Strategy (fast to slow):
        0. Cached region scan (~50ms) — same region, different address
        1. History scan (~30ms) — known good regions
        2. Neighborhood scan (~200ms) — ±16MB around current address
        3. Heap scan (~2.5s) — all small regions
        4. Full pymem scan (~7s) — last resort after 5 failed attempts
        """
        if not self._pm:
            return

        t0 = time.monotonic()

        # Try cached region first — single ReadProcessMemory call
        new_addr = 0
        scan_type = "cached_region"
        if self._cached_region:
            new_addr = self._scan_cached_region()
            if new_addr in self._blacklisted_addrs or new_addr == self._buf_addr:
                new_addr = 0

        # Try history regions — but only accept if it's a DIFFERENT address
        if not new_addr:
            scan_type = "history"
            if self._region_history:
                new_addr = _scan_regions_for_marker(self._pm, self._region_history)
                if new_addr in self._blacklisted_addrs or new_addr == self._buf_addr:
                    new_addr = 0

        if not new_addr and self._buf_addr:
            # Neighborhood scan: Lua GC often reallocates nearby (~200ms vs 2.5s)
            new_addr = self._neighborhood_scan(self._buf_addr)
            if new_addr in self._blacklisted_addrs or new_addr == self._buf_addr:
                new_addr = 0
            scan_type = "neighborhood"

        if not new_addr:
            # Full heap scan — find buffer with highest seq
            self._all_regions = self._get_memory_regions()
            new_addr = self._scan_heap_regions()
            if new_addr in self._blacklisted_addrs or new_addr == self._buf_addr:
                new_addr = 0
            scan_type = "heap"

        # If heap scan didn't find a newer buffer after many attempts, try full pymem scan
        if not new_addr and self._same_addr_count >= 5:
            new_addr = self._full_marker_scan(min_seq=self._last_seq)
            if new_addr in self._blacklisted_addrs or new_addr == self._buf_addr:
                new_addr = 0
            scan_type = "full"

        elapsed = time.monotonic() - t0

        if new_addr and new_addr != self._buf_addr:
            logger.info(
                "Found newer buffer at 0x%X (was 0x%X), %s scan took %.0fms",
                new_addr, self._buf_addr, scan_type, elapsed * 1000,
            )
            self._buf_addr = new_addr
            self._stale_count = 0
            self._stale_tier = 0
            self._same_addr_count = 0
            self._frozen_count = 0
            self._rescan_interval = _RESCAN_INTERVALS[0]
            self._record_hit_from_addr(new_addr)
            self._try_setup_pointer(new_addr)
        else:
            self._same_addr_count += 1
            # Adaptive: ramp up rescan interval when idle
            tier = min(self._same_addr_count // 3, len(_RESCAN_INTERVALS) - 1)
            self._rescan_interval = _RESCAN_INTERVALS[tier]
            if self._same_addr_count <= 3 or self._same_addr_count % 10 == 0:
                logger.info(
                    "Periodic rescan #%d: same buffer (%s, %.0fms, next in %.0fs)",
                    self._same_addr_count, scan_type, elapsed * 1000,
                    self._rescan_interval,
                )

    def _neighborhood_scan(self, center_addr: int, min_seq: int = 0) -> int:
        """Scan ±4MB around the last known buffer address.

        Lua GC often reallocates strings nearby. This is much faster than
        a full heap scan (~200ms vs ~2.5s).
        """
        if not self._pm or center_addr == 0:
            return 0

        start = max(0, center_addr - _NEIGHBORHOOD_RADIUS)
        end = center_addr + _NEIGHBORHOOD_RADIUS
        best_addr = 0
        best_seq = -1

        for region in self._get_memory_regions():
            base, size = region
            region_end = base + size
            # Only scan regions that overlap the neighborhood
            if region_end < start or base > end:
                continue
            if size > 8 * 1024 * 1024:
                continue

            try:
                raw = self._pm.read_bytes(base, min(size, MAX_BUF_READ))
            except Exception:
                continue

            offset = 0
            while offset < len(raw):
                idx = raw.find(b"__WCT_BUF_", offset)
                if idx == -1:
                    break
                chunk = raw[idx:]
                co = _find_content_start(chunk)
                if co == -1:
                    offset = idx + 10
                    continue
                me = chunk.find(MARKER_END, co)
                if me == -1:
                    break
                content = chunk[co:me]
                ms = _extract_max_seq(content)
                if ms > best_seq and ms > min_seq:
                    best_seq = ms
                    best_addr = base + idx
                offset = idx + me

        if best_addr:
            logger.info(
                "Neighborhood scan found buffer at 0x%X (seq=%d)", best_addr, best_seq,
            )
            self._record_hit_from_addr(best_addr)
        return best_addr

    def _scan_heap_regions(self, min_seq: int = 0) -> int:
        """Scan likely Lua heap regions for the best (highest seq) marker.

        Lua allocates strings in PAGE_READWRITE regions, typically 1-4MB.
        We scan only regions ≤ 8MB to avoid image/resource regions.

        Returns marker address or 0.
        """
        if not self._pm:
            return 0

        heap_regions = [(b, s) for b, s in self._all_regions if s <= 8 * 1024 * 1024]
        addr = _scan_regions_for_marker(self._pm, heap_regions, min_seq=min_seq)

        logger.debug(
            "Heap scan: %d regions, best found=%s",
            len(heap_regions), f"0x{addr:X}" if addr else "none",
        )
        return addr

    # ------------------------------------------------------------------
    # Buffer reading and polling
    # ------------------------------------------------------------------

    def _read_buffer(self) -> str | None:
        """Read buffer content at the current marker address."""
        if not self._pm or self._buf_addr == 0:
            return None
        try:
            raw = self._pm.read_bytes(self._buf_addr, MAX_BUF_READ)
        except Exception:
            return None

        co = _find_content_start(raw)
        if co == -1:
            if self._stale_count <= 1:
                logger.warning("_read_buffer: no valid header at 0x%X, first 80 bytes: %r",
                               self._buf_addr, raw[:80])
            return None

        end_idx = raw.find(MARKER_END, co)
        if end_idx == -1:
            if self._stale_count <= 1:
                logger.warning("_read_buffer: no END marker at 0x%X, header OK (co=%d), preview: %r",
                               self._buf_addr, co, raw[co:co+200])
            return None

        content_bytes = raw[co:end_idx]
        try:
            return content_bytes.decode("utf-8", errors="replace")
        except Exception:
            return None

    def _poll_buffer(self) -> None:
        """Read the addon buffer and deliver new messages.

        Fast path: if we have a cached pointer (_ptr_addr), follow it to read
        the current buffer in ~1ms without any memory scanning.

        Fallback scenarios:
        1. Marker gone (read returns None) — string was GC'd → IMMEDIATE fast
           relocate (cached region + neighborhood + history, <300ms), then
           fall back to heap/full scan only if fast path fails.
        2. Frozen buffer — old Lua string still readable but outdated.
           Smart rescan: only trigger when no new messages for >2s, NOT on a
           fixed timer when messages are actively flowing.
        """
        if not self._pm or self._buf_addr == 0:
            return

        # ---- FAST PATH: pointer-chasing (~1ms) ----
        content = None
        if self._ptr_addr:
            content = self._read_buffer_via_ptr()
            if content is None:
                logger.info(
                    "Pointer stale at 0x%X, falling back to direct read",
                    self._ptr_addr,
                )
                self._ptr_addr = 0
                self._ptr_offset = 0

        # ---- NORMAL PATH: direct read at cached address ----
        if content is None:
            content = self._read_buffer()
        if content is None:
            # ---- FAST PATH: marker gone, try to relocate immediately ----
            self._stale_count += 1

            if self._stale_count == 1:
                logger.info("Marker gone at 0x%X, trying fast relocate...", self._buf_addr)
                old_addr = self._buf_addr
                new_addr = self._fast_relocate_buffer(min_seq=self._last_seq)
                if new_addr:
                    logger.info(
                        "Fast relocate SUCCESS: 0x%X → 0x%X",
                        old_addr, new_addr,
                    )
                    self._buf_addr = new_addr
                    self._stale_count = 0
                    self._stale_tier = 0
                    self._record_hit_from_addr(new_addr)
                    self._try_setup_pointer(new_addr)
                    # Immediately try to read from new address
                    content = self._read_buffer()
                    if content is not None:
                        stripped = content.strip()
                        if stripped:
                            self._deliver_new_messages(content)
                    return

                logger.info("Fast relocate MISS, will try full scan on next cycle")

            # Exponential backoff: threshold doubles each tier (2→4→8→16)
            stale_threshold = min(2 << self._stale_tier, 16)
            if self._stale_count >= stale_threshold:
                if self._stale_tier == 0:
                    logger.info("Marker gone, triggering full rescan (tier 0)")
                else:
                    logger.debug(
                        "Marker still gone (tier=%d, count=%d), rescan",
                        self._stale_tier, self._stale_count,
                    )
                # After 3 failed tiers, blacklist this address and purge from history
                if self._stale_tier >= 3:
                    old_addr = self._buf_addr if self._buf_addr else 0
                    if old_addr:
                        expiry = time.monotonic() + self._blacklist_ttl
                        self._blacklisted_addrs[old_addr] = expiry
                        logger.info(
                            "Blacklisted zombie marker at 0x%X (expires in %.0fs)",
                            old_addr, self._blacklist_ttl,
                        )
                        # Cleanup expired blacklist entries
                        now_bl = time.monotonic()
                        expired = [a for a, t in self._blacklisted_addrs.items() if t <= now_bl]
                        for a in expired:
                            del self._blacklisted_addrs[a]
                        if expired:
                            logger.debug("Expired %d blacklist entries", len(expired))
                    if self._cached_region and self._cached_region in self._region_history:
                        self._region_history.remove(self._cached_region)
                        logger.info(
                            "Purged zombie region (%d bytes @ 0x%X) from history",
                            self._cached_region[1], self._cached_region[0],
                        )
                self._stale_tier += 1
                self._buf_addr = 0
                self._stale_count = 0
            return

        stripped = content.strip()
        if not stripped:
            return

        self._stale_count = 0
        self._stale_tier = 0

        # ---- SEQ FRESHNESS CHECK ----
        # Extract max seq from buffer to detect frozen (zombie) buffers.
        buf_max_seq = _extract_max_seq(content.encode("utf-8", errors="replace"))
        if buf_max_seq > 0:
            if self._seq_history and buf_max_seq == self._seq_history[-1]:
                self._frozen_count += 1
            else:
                self._frozen_count = 0
            self._seq_history.append(buf_max_seq)
            if len(self._seq_history) > 3:
                self._seq_history.pop(0)

            # If seq unchanged for 3+ polls AND no new messages recently,
            # this buffer is likely a zombie — trigger rescan
            if self._frozen_count >= 3:
                now_f = time.monotonic()
                time_idle = now_f - self._last_new_msg_time if self._last_new_msg_time else 999.0
                if time_idle > 3.0:
                    logger.info(
                        "Frozen buffer detected: seq=%d unchanged for %d polls, "
                        "triggering rescan",
                        buf_max_seq, self._frozen_count,
                    )
                    self._frozen_count = 0
                    self._quick_rescan_for_newer_buffer()

        self._deliver_new_messages(content)

        # ---- SMART RESCAN: only when buffer is likely stale ----
        # Addon flushes every 1.5s creating a new Lua string.  Full heap scan
        # is expensive (3-5s for 20k+ regions) and blocks the reader.
        # Strategy: only do a FAST rescan (cached region + neighborhood) on the
        # normal timer.  Full heap scan only when fast rescan keeps failing.
        now = time.monotonic()
        time_since_new_msg = now - self._last_new_msg_time if self._last_new_msg_time else 999.0
        if (
            time_since_new_msg > 1.5
            and now - self._last_rescan >= self._rescan_interval
        ):
            self._last_rescan = now
            self._quick_rescan_for_newer_buffer()

    def _deliver_new_messages(self, content: str) -> None:
        """Parse buffer content and deliver messages with seq > last_seq."""
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            return

        # Detect seq reset: after /reload, addon restarts seq from 1
        max_seq_in_buf = 0
        for line in lines:
            parts = line.split("|", 1)
            if parts:
                try:
                    s = int(parts[0])
                    if s > max_seq_in_buf:
                        max_seq_in_buf = s
                except ValueError:
                    pass

        if max_seq_in_buf > 0 and max_seq_in_buf < self._last_seq:
            logger.info(
                "Seq reset detected (buf max=%d, last_seq=%d) — saving texts & resetting",
                max_seq_in_buf, self._last_seq,
            )
            # Use already-delivered payloads to avoid re-delivering after reset
            self._pre_reset_texts = set(self._delivered_payloads)
            self._pre_reset_expire = time.monotonic() + 60.0
            self._last_seq = 0

        new_count = 0
        for line in lines:
            parts = line.split("|", 2)
            if len(parts) < 3:
                continue

            try:
                seq = int(parts[0])
            except ValueError:
                continue

            kind = parts[1]
            payload = parts[2]

            # META lines carry metadata (e.g. player name), not chat messages
            if kind == "META":
                meta_parts = payload.split("|", 1)
                if meta_parts[0] == "PLAYER" and len(meta_parts) > 1:
                    name = meta_parts[1].strip()
                    if name and name != self._player_name:
                        self._player_name = name
                        logger.info("Player name from addon: %s", name)
                continue

            if seq <= self._last_seq:
                continue

            self._last_seq = seq

            # Seq reset guard: skip messages we already delivered before reset
            if self._pre_reset_texts and payload[:200] in self._pre_reset_texts:
                logger.debug("Seq reset dedup: skipping #%d (already delivered)", seq)
                continue

            new_count += 1
            # Track delivered payload for seq reset dedup
            self._delivered_payloads.add(payload[:200])
            if len(self._delivered_payloads) > 200:
                self._delivered_payloads.clear()

            # Sanitize: Lua strings may contain embedded \x00 bytes from
            # taint-corrupted GetMessageInfo() results.  Truncate at first
            # null byte and strip trailing non-printable characters.
            nul_pos = payload.find("\x00")
            if nul_pos != -1:
                payload = payload[:nul_pos]
            payload = payload.rstrip("\x00\x01\x02\x03\x04\x05\x06\x07\x08")
            if not payload.strip():
                continue

            if kind in ("RAW", "DICT"):
                # Parse payload fields:
                #   DICT: EVENT|author|original|translated
                #   RAW:  EVENT|author|text
                event = ""
                author = ""
                msg_text = payload
                dict_translated_text = ""

                if kind == "DICT":
                    # DICT payload: EVENT|author|original\ttranslated
                    # Tab separates original from translated (pipes may appear in WoW color codes)
                    sub_parts = payload.split("|", 2)
                    if len(sub_parts) >= 3:
                        event = sub_parts[0]
                        author = sub_parts[1]
                        text_and_translated = sub_parts[2]
                        if "\t" in text_and_translated:
                            msg_text, dict_translated_text = text_and_translated.split("\t", 1)
                        else:
                            msg_text = text_and_translated
                else:
                    sub_parts = payload.split("|", 2)
                    if len(sub_parts) >= 3:
                        event = sub_parts[0]
                        author = sub_parts[1]
                        msg_text = sub_parts[2]

                # Log ALL raw messages to file for debugging
                try:
                    with open(RAW_LOG_FILE, "a", encoding="utf-8") as f:
                        t = time.localtime()
                        ts = (
                            f"{t.tm_mon}/{t.tm_mday} "
                            f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}.000"
                        )
                        f.write(f"[{ts}] #{seq} [{kind}] {event}|{author}|{msg_text}\n")
                except OSError:
                    pass

                if _is_system_noise(msg_text):
                    logger.debug("Addon raw #%d: [skip system] %s", seq, msg_text[:120])
                    continue

                # Strip embedded WoW chat timestamp (HH:MM:SS)
                msg_text = re.sub(r"^\d{1,2}:\d{2}:\d{2}\s+", "", msg_text)

                # Build synthetic log line with channel and author
                if event and author:
                    log_line = self._make_synthetic_log_line(event, author, msg_text)
                    if not log_line:
                        t = time.localtime()
                        ts = f"{t.tm_mon}/{t.tm_mday} {t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}.000"
                        log_line = f"{ts}  {msg_text}"
                else:
                    t = time.localtime()
                    ts = f"{t.tm_mon}/{t.tm_mday} {t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}.000"
                    log_line = f"{ts}  {msg_text}"

                if kind == "DICT":
                    logger.info("Addon dict #%d: %s", seq, log_line[:200])
                    self._on_new_line(
                        log_line, dict_translated=True,
                        dict_text=dict_translated_text,
                    )
                else:
                    logger.info("Addon raw #%d: %s", seq, log_line[:200])
                    self._on_new_line(log_line)

        # Expire pre-reset dedup set
        if self._pre_reset_texts and time.monotonic() > self._pre_reset_expire:
            logger.debug("Pre-reset dedup set expired (%d entries)", len(self._pre_reset_texts))
            self._pre_reset_texts.clear()

        if new_count > 0:
            logger.info("Delivered %d new messages (last_seq=%d)", new_count, self._last_seq)
            # Reset rescan to fast mode when messages are flowing
            self._rescan_interval = _RESCAN_INTERVALS[0]
            self._same_addr_count = 0
            self._frozen_count = 0
            self._last_new_msg_time = time.monotonic()

    @staticmethod
    def _make_synthetic_log_line(channel: str, author: str, text: str) -> str | None:
        """Convert addon buffer entry to a WoW chat log line for parse_line()."""
        _ADDON_CHANNEL_TO_LOG = {
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
            "CHANNEL": "Say",  # global channels → treat as Say for parsing
            "EMOTE": "Say",  # emotes → treat as Say
            "BATTLEGROUND": "Instance",
            "BATTLEGROUND_LEADER": "Instance Leader",
        }
        t = time.localtime()
        ts = f"{t.tm_mon}/{t.tm_mday} {t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}.000"

        if channel in ("WHISPER", "BN_WHISPER"):
            return f"{ts}  [{author}] whispers: {text}"
        if channel == "WHISPER_INFORM":
            return f"{ts}  To [{author}]: {text}"

        log_channel = _ADDON_CHANNEL_TO_LOG.get(channel)
        if log_channel is None:
            return None

        return f"{ts}  [{log_channel}] {author}: {text}"


class MemoryChatWatcher:
    """High-level watcher: bridges WoWAddonBufReader to the pipeline."""

    def __init__(self, on_new_line: Callable[..., None]) -> None:
        self._on_new_line = on_new_line
        self._reader = WoWAddonBufReader(on_new_line=on_new_line)

    def start(self) -> None:
        self._reader.start()

    def stop(self) -> None:
        self._reader.stop()

    @property
    def is_attached(self) -> bool:
        return self._reader.is_attached

    @property
    def player_name(self) -> str:
        return self._reader.player_name
