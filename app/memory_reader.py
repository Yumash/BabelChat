"""Read WoW chat messages directly from process memory via ReadProcessMemory.

Bypasses the WoW chat log file buffering problem (4KB C runtime buffer)
by reading the in-memory chat ring buffer directly.

Approach:
1. Attach to Wow.exe process via pymem
2. Search for known chat text in memory to locate the ring buffer
3. Determine slot stride and field offsets by analyzing the structure
4. Poll the ring buffer for new messages (buffer position counter changes)
5. Deliver messages to callback in real-time (<100ms latency)

Safety: Read-only memory access. Warden does not flag external ReadProcessMemory.

Chat buffer structure (64-bit retail TWW 12.0.x):
- Ring buffer with 60 slots, each 0xCB8 bytes (3256 bytes)
- Slot layout:
  +0x0000  posterGuid    (8 bytes, uint64)
  +0x0034  posterName    (~50 bytes, null-terminated UTF-8)
  +0x0065  channelName   (~129 bytes, null-terminated UTF-8)
  +0x00E6  message       (~2800 bytes, null-terminated UTF-8)
  +0x0CA0  messageType   (4 bytes, int32 — ChatMsg enum)
  +0x0CA4  channelNumber (4 bytes, int32)
  +0x0CA8  sequenceIndex (4 bytes, uint32 — global monotonic counter)
  +0x0CB0  timestamp     (8 bytes, uint64 — time_t)

Sources: OwnedCore, TrinityCore SharedDefines.h (ChatMsg enum for build 12.0.1.65893)
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import struct
import threading
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Chat buffer constants (WoW Retail TWW 12.0.x)
CHAT_BUFFER_SIZE = 60  # Ring buffer holds 60 messages
SLOT_STRIDE = 0xCB8  # 3256 bytes per slot (known from reverse engineering)
POLL_INTERVAL = 0.1  # 100ms polling for near-real-time delivery

# Known slot field offsets (64-bit retail, stable across recent builds)
OFFSET_POSTER_GUID = 0x0000
OFFSET_POSTER_NAME = 0x0034
OFFSET_CHANNEL_NAME = 0x0065
OFFSET_MESSAGE_TEXT = 0x00E6
OFFSET_MESSAGE_TYPE = 0x0CA0
OFFSET_CHANNEL_NUMBER = 0x0CA4
OFFSET_SEQUENCE_INDEX = 0x0CA8
OFFSET_TIMESTAMP = 0x0CB0

# Process names to try
WOW_PROCESS_NAMES = ["Wow.exe", "WowT.exe", "WowB.exe"]


@dataclass(frozen=True, slots=True)
class MemoryChatMessage:
    """A chat message read from WoW process memory."""

    sender: str
    text: str
    channel_type: int  # ChatMsg enum value
    channel_name: str  # Resolved channel name
    sequence: int  # Global monotonic sequence number
    timestamp: float  # When we read it


# ChatMsg enum values (from TrinityCore master, targeting TWW 12.0.1.65893)
# Only include channels we care about for translation
_CHANNEL_TYPE_MAP: dict[int, str] = {
    0x00: "System",
    0x01: "Say",
    0x02: "Party",
    0x03: "Raid",
    0x04: "Guild",
    0x05: "Officer",
    0x06: "Yell",
    0x07: "Whisper",          # incoming
    0x08: "Whisper Foreign",
    0x09: "Whisper Inform",   # outgoing (you whispered)
    0x0A: "Emote",
    0x0B: "Text Emote",
    0x11: "Channel",          # custom/numbered channels (General, Trade, etc.)
    0x27: "Raid Leader",
    0x28: "Raid Warning",
    0x31: "Party Leader",
    0x3E: "Instance",         # instance chat
    0x3F: "Instance Leader",
}


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


class WoWMemoryReader:
    """Reads chat messages from WoW's process memory.

    Usage:
        reader = WoWMemoryReader(on_message=handle_msg)
        reader.start()   # starts polling thread
        reader.stop()    # stops polling
    """

    def __init__(self, on_message: Callable[[MemoryChatMessage], None]) -> None:
        self._on_message = on_message
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._pm = None  # pymem.Pymem instance
        self._base_address: int = 0
        self._attached = False
        # Chat buffer location
        self._chat_buffer_base: int = 0
        self._slot_stride: int = SLOT_STRIDE
        self._text_offset: int = OFFSET_MESSAGE_TEXT
        self._name_offset: int = OFFSET_POSTER_NAME
        self._type_offset: int = OFFSET_MESSAGE_TYPE
        self._seq_offset: int = OFFSET_SEQUENCE_INDEX
        # Tracking
        self._last_sequence: int = 0
        self._initial_scan_done = False

    @property
    def is_attached(self) -> bool:
        return self._attached

    def start(self) -> None:
        """Start the memory reader polling thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Memory reader thread started")

    def stop(self) -> None:
        """Stop the memory reader."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._detach()
        logger.info("Memory reader stopped")

    def _run_loop(self) -> None:
        """Main loop: attach → poll → handle errors → retry."""
        while not self._stop_event.is_set():
            if not self._attached:
                try:
                    self._attach()
                except Exception as e:
                    logger.debug("Cannot attach to WoW: %s", e)
                    self._stop_event.wait(3.0)
                    continue

            try:
                self._poll_messages()
            except Exception as e:
                logger.warning("Memory read error: %s", e)
                self._detach()
                self._stop_event.wait(3.0)
                continue

            self._stop_event.wait(POLL_INTERVAL)

    def _attach(self) -> None:
        """Attach to WoW process and find chat buffer."""
        import pymem
        import pymem.process

        for proc_name in WOW_PROCESS_NAMES:
            try:
                self._pm = pymem.Pymem(proc_name)
                self._base_address = self._pm.base_address
                logger.info(
                    "Attached to %s (PID %d, base 0x%X)",
                    proc_name,
                    self._pm.process_id,
                    self._base_address,
                )
                break
            except pymem.exception.ProcessNotFound:
                continue
        else:
            raise RuntimeError("WoW process not found")

        # Find chat buffer by searching for known chat text in memory
        found = self._find_chat_buffer()
        if not found:
            self._detach()
            raise RuntimeError("Could not locate WoW chat buffer in memory")

        self._attached = True

    def _detach(self) -> None:
        """Detach from WoW process."""
        if self._pm:
            try:
                self._pm.close_process()
            except Exception:
                pass
        self._pm = None
        self._attached = False
        self._chat_buffer_base = 0
        self._last_sequence = 0
        self._initial_scan_done = False

    def _find_chat_buffer(self) -> bool:
        """Find the chat ring buffer by searching for known chat text in WoW's memory.

        Strategy:
        1. Read WoWChatLog.txt to get recent message texts
        2. Search process memory for those strings (they exist in the ring buffer)
        3. Verify the structure by checking sender names at expected offsets
        4. Determine exact buffer base and validate stride
        """
        if not self._pm:
            return False

        recent_texts = self._get_recent_chat_texts()
        if not recent_texts:
            logger.warning("No recent chat texts available for memory scanning")
            return False

        logger.info("Scanning WoW memory for %d known chat texts...", len(recent_texts))

        # Search for each text in memory
        found_addresses: list[tuple[str, int]] = []
        for text in recent_texts[:8]:
            addrs = self._search_memory_for_string(text)
            for addr in addrs:
                # Verify this looks like a chat slot by checking for sender name
                if self._verify_chat_slot(addr, text):
                    found_addresses.append((text, addr))
                    logger.info("Verified chat text at 0x%X: '%s'", addr, text[:40])

            if len(found_addresses) >= 3:
                break  # Enough to determine structure

        if len(found_addresses) < 1:
            logger.warning("No chat text found in WoW memory")
            return False

        # If we have at least one verified address, we know the offsets
        # and can calculate the buffer base
        first_text_addr = found_addresses[0][1]
        slot_start = first_text_addr - self._text_offset

        # Validate: check if adjacent slots also contain valid data
        if len(found_addresses) >= 2:
            success = self._validate_stride(found_addresses)
            if not success:
                logger.warning("Could not validate stride, using default 0xCB8")

        self._chat_buffer_base = self._find_slot_zero(slot_start)
        logger.info(
            "Chat buffer base: 0x%X (stride=0x%X, text_offset=0x%X)",
            self._chat_buffer_base, self._slot_stride, self._text_offset,
        )

        # Set initial sequence to max of all current slots (skip existing messages)
        self._skip_existing_messages()

        return True

    def _verify_chat_slot(self, text_addr: int, expected_text: str) -> bool:
        """Verify that an address is inside a real chat buffer slot.

        Checks that at the expected sender name offset there's a valid string.
        """
        if not self._pm:
            return False

        # Try the known text offset (0xE6). The sender name should be at 0x34.
        for text_off in [OFFSET_MESSAGE_TEXT]:
            slot_start = text_addr - text_off
            name_addr = slot_start + OFFSET_POSTER_NAME

            try:
                name = self._read_string(name_addr, 48)
            except Exception:
                continue

            if not name or len(name) < 2:
                continue

            # WoW character names: 2-12 chars, first letter uppercase,
            # can contain Cyrillic/Latin, no spaces
            if name[0].isupper() or name[0].isalpha():
                # Additional check: message type should be a valid ChatMsg value
                type_addr = slot_start + OFFSET_MESSAGE_TYPE
                try:
                    type_data = self._pm.read_bytes(type_addr, 4)
                    msg_type = struct.unpack("<i", type_data)[0]
                    if -1 <= msg_type <= 0x43:  # Valid ChatMsg range
                        self._text_offset = text_off
                        logger.debug(
                            "Verified slot: sender='%s', type=%d at 0x%X",
                            name, msg_type, slot_start,
                        )
                        return True
                except Exception:
                    continue

        return False

    def _validate_stride(self, found_addresses: list[tuple[str, int]]) -> bool:
        """Check if found addresses confirm the expected stride."""
        sorted_addrs = sorted(found_addresses, key=lambda x: x[1])

        for i in range(len(sorted_addrs) - 1):
            diff = sorted_addrs[i + 1][1] - sorted_addrs[i][1]
            if diff > 0 and diff % SLOT_STRIDE == 0:
                n_slots = diff // SLOT_STRIDE
                if 1 <= n_slots <= CHAT_BUFFER_SIZE:
                    logger.info(
                        "Stride validated: %d slots apart, stride=0x%X",
                        n_slots, SLOT_STRIDE,
                    )
                    return True

        # Try to find a different stride if 0xCB8 doesn't match
        strides: list[int] = []
        for i in range(len(sorted_addrs)):
            for j in range(i + 1, len(sorted_addrs)):
                diff = sorted_addrs[j][1] - sorted_addrs[i][1]
                if 0x400 <= diff <= 0x4000:
                    strides.append(diff)
                elif diff > 0x4000:
                    # Check if it's a multiple of a reasonable stride
                    for s in [0xCB8, 0xCC0, 0xCD0, 0xCE0, 0xD00]:
                        if diff % s == 0 and diff // s <= CHAT_BUFFER_SIZE:
                            strides.append(s)

        if strides:
            best = Counter(strides).most_common(1)[0][0]
            if best != SLOT_STRIDE:
                logger.info("Detected different stride: 0x%X (was 0x%X)", best, SLOT_STRIDE)
                self._slot_stride = best
                # Recalculate type and sequence offsets relative to stride
                self._type_offset = best - 0x18
                self._seq_offset = best - 0x10
            return True

        return False

    def _find_slot_zero(self, known_slot_start: int) -> int:
        """Walk backwards from a known slot to find slot 0 (buffer base).

        Reads backwards checking if previous slots also contain valid data.
        """
        if not self._pm:
            return known_slot_start

        base = known_slot_start
        # Try walking back up to 60 slots
        for _ in range(CHAT_BUFFER_SIZE):
            prev_slot = base - self._slot_stride
            # Check if previous slot has a valid sender name
            try:
                name = self._read_string(prev_slot + self._name_offset, 48)
                if name and len(name) >= 2:
                    base = prev_slot
                    continue
            except Exception:
                pass
            break  # Previous slot invalid, current base is slot 0 (or close)

        return base

    def _skip_existing_messages(self) -> None:
        """Find the highest sequence number currently in the buffer.

        This ensures we only deliver NEW messages, not replay existing ones.
        """
        max_seq = 0
        for slot_idx in range(CHAT_BUFFER_SIZE):
            slot_base = self._chat_buffer_base + (slot_idx * self._slot_stride)
            try:
                seq_data = self._pm.read_bytes(slot_base + self._seq_offset, 4)
                seq = struct.unpack("<I", seq_data)[0]
                if seq > max_seq:
                    max_seq = seq
            except Exception:
                continue

        self._last_sequence = max_seq
        self._initial_scan_done = True
        logger.info("Skipped existing messages (max sequence: %d)", max_seq)

    def _get_recent_chat_texts(self) -> list[str]:
        """Get recent chat message texts from WoWChatLog.txt for memory searching."""
        from app.config import AppConfig, resolve_chatlog_path
        from app.parser import parse_line

        try:
            config = AppConfig.load()
            chatlog = resolve_chatlog_path(config)
            with open(chatlog, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except (FileNotFoundError, OSError):
            return []

        texts = []
        for line in lines[-30:]:
            stripped = line.strip()
            if not stripped:
                continue
            msg = parse_line(stripped)
            # Need at least 6 chars for reliable memory search
            if msg and len(msg.text) >= 6:
                texts.append(msg.text)

        # Prefer longer/unique texts for more reliable matching
        texts.sort(key=len, reverse=True)
        return texts

    def _search_memory_for_string(self, text: str, max_results: int = 5) -> list[int]:
        """Search WoW process memory for a UTF-8 string."""
        if not self._pm:
            return []

        needle = text.encode("utf-8")
        results: list[int] = []

        try:
            regions = self._get_memory_regions()
        except Exception as e:
            logger.debug("Cannot enumerate memory regions: %s", e)
            return []

        for base, size in regions:
            try:
                data = self._pm.read_bytes(base, size)
                offset = 0
                while True:
                    idx = data.find(needle, offset)
                    if idx == -1:
                        break
                    results.append(base + idx)
                    if len(results) >= max_results:
                        return results
                    offset = idx + 1
            except Exception:
                continue

        return results

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

    def _poll_messages(self) -> None:
        """Poll the chat buffer for new messages by checking sequence numbers."""
        if not self._pm or self._chat_buffer_base == 0:
            return

        # Scan all 60 slots for sequence numbers > last_sequence
        new_messages: list[tuple[int, int, int]] = []  # (seq, slot_idx, slot_base)

        for slot_idx in range(CHAT_BUFFER_SIZE):
            slot_base = self._chat_buffer_base + (slot_idx * self._slot_stride)

            try:
                seq_data = self._pm.read_bytes(slot_base + self._seq_offset, 4)
                seq = struct.unpack("<I", seq_data)[0]
            except Exception:
                continue

            if seq > self._last_sequence:
                new_messages.append((seq, slot_idx, slot_base))

        # Sort by sequence number and deliver in order
        new_messages.sort(key=lambda x: x[0])

        for seq, slot_idx, slot_base in new_messages:
            try:
                msg = self._read_slot(slot_base, seq)
                if msg:
                    self._last_sequence = seq
                    self._on_message(msg)
            except Exception as e:
                logger.debug("Error reading slot %d: %s", slot_idx, e)

    def _read_slot(self, slot_base: int, sequence: int) -> MemoryChatMessage | None:
        """Read a single chat message slot from memory."""
        if not self._pm:
            return None

        sender = self._read_string(slot_base + self._name_offset, 48)
        if not sender:
            return None

        text = self._read_string(slot_base + self._text_offset, 512)
        if not text:
            return None

        try:
            ch_data = self._pm.read_bytes(slot_base + self._type_offset, 4)
            channel_type = struct.unpack("<i", ch_data)[0]
        except Exception:
            channel_type = 0

        channel_name = _CHANNEL_TYPE_MAP.get(channel_type, f"Unknown({channel_type})")

        return MemoryChatMessage(
            sender=sender,
            text=text,
            channel_type=channel_type,
            channel_name=channel_name,
            sequence=sequence,
            timestamp=time.time(),
        )

    def _read_string(self, address: int, max_len: int = 256) -> str:
        """Read a null-terminated UTF-8 string from process memory."""
        if not self._pm:
            return ""

        try:
            data = self._pm.read_bytes(address, max_len)
        except Exception:
            return ""

        null_idx = data.find(b"\x00")
        if null_idx == -1:
            raw = data
        elif null_idx == 0:
            return ""
        else:
            raw = data[:null_idx]

        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return ""


class MemoryChatWatcher:
    """High-level watcher that bridges MemoryReader to the pipeline.

    Converts MemoryChatMessages to synthetic WoW chat log lines,
    making it a drop-in replacement for the file-based watcher.
    """

    def __init__(self, on_new_line: Callable[[str], None]) -> None:
        self._on_new_line = on_new_line
        self._reader = WoWMemoryReader(on_message=self._on_memory_message)
        self._seen_sequences: set[int] = set()

    def start(self) -> None:
        """Start reading WoW chat from memory."""
        self._reader.start()

    def stop(self) -> None:
        """Stop reading."""
        self._reader.stop()

    @property
    def is_attached(self) -> bool:
        return self._reader.is_attached

    def _on_memory_message(self, msg: MemoryChatMessage) -> None:
        """Convert memory message to a synthetic WoW chat log line for the parser."""
        if msg.sequence in self._seen_sequences:
            return
        self._seen_sequences.add(msg.sequence)

        # Limit memory usage
        if len(self._seen_sequences) > 200:
            cutoff = max(self._seen_sequences) - 150
            self._seen_sequences = {s for s in self._seen_sequences if s > cutoff}

        # Map ChatMsg enum to log channel name
        channel_log_name = _MEMORY_CHANNEL_TO_LOG.get(msg.channel_type)
        if channel_log_name is None:
            return  # Skip system/loot/emote/etc.

        # Construct synthetic log line matching WoW chat log format
        ts = time.strftime("%m/%d %H:%M:%S", time.localtime(msg.timestamp))
        ms = int((msg.timestamp % 1) * 1000)

        if msg.channel_type == 0x07:  # CHAT_MSG_WHISPER (incoming)
            line = f"{ts}.{ms:03d}  [{msg.sender}] whispers: {msg.text}"
        elif msg.channel_type == 0x09:  # CHAT_MSG_WHISPER_INFORM (outgoing)
            line = f"{ts}.{ms:03d}  To [{msg.sender}]: {msg.text}"
        else:
            line = f"{ts}.{ms:03d}  [{channel_log_name}] {msg.sender}: {msg.text}"

        logger.info("Memory: [%s] %s: %s", channel_log_name, msg.sender, msg.text[:60])
        self._on_new_line(line)


# Map ChatMsg enum values to WoW chat log channel names for parser compatibility
# Values from TrinityCore master (TWW 12.0.1.65893)
_MEMORY_CHANNEL_TO_LOG: dict[int, str] = {
    0x01: "Say",             # CHAT_MSG_SAY
    0x02: "Party",           # CHAT_MSG_PARTY
    0x03: "Raid",            # CHAT_MSG_RAID
    0x04: "Guild",           # CHAT_MSG_GUILD
    0x05: "Officer",         # CHAT_MSG_OFFICER
    0x06: "Yell",            # CHAT_MSG_YELL
    0x07: "Whisper",         # CHAT_MSG_WHISPER (special format)
    0x09: "Whisper",         # CHAT_MSG_WHISPER_INFORM (special format)
    0x27: "Raid Leader",     # CHAT_MSG_RAID_LEADER
    0x28: "Raid Warning",    # CHAT_MSG_RAID_WARNING
    0x31: "Party Leader",    # CHAT_MSG_PARTY_LEADER
    0x3E: "Instance",        # CHAT_MSG_INSTANCE_CHAT
    0x3F: "Instance Leader", # CHAT_MSG_INSTANCE_CHAT_LEADER
}
