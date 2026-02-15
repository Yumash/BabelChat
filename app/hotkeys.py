"""Global hotkey support using Win32 API."""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import threading

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

# Win32 constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312

# Key name to virtual key code
_VK_MAP: dict[str, int] = {
    "A": 0x41, "B": 0x42, "C": 0x43, "D": 0x44, "E": 0x45,
    "F": 0x46, "G": 0x47, "H": 0x48, "I": 0x49, "J": 0x4A,
    "K": 0x4B, "L": 0x4C, "M": 0x4D, "N": 0x4E, "O": 0x4F,
    "P": 0x50, "Q": 0x51, "R": 0x52, "S": 0x53, "T": 0x54,
    "U": 0x55, "V": 0x56, "W": 0x57, "X": 0x58, "Y": 0x59,
    "Z": 0x5A,
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
}


def parse_hotkey(hotkey_str: str) -> tuple[int, int]:
    """Parse a hotkey string like 'Ctrl+Shift+T' into (modifiers, vk).

    Returns (0, 0) if invalid.
    """
    parts = [p.strip() for p in hotkey_str.split("+")]
    modifiers = MOD_NOREPEAT
    vk = 0

    for part in parts:
        upper = part.upper()
        if upper in ("CTRL", "CONTROL"):
            modifiers |= MOD_CONTROL
        elif upper == "SHIFT":
            modifiers |= MOD_SHIFT
        elif upper == "ALT":
            modifiers |= MOD_ALT
        elif upper in _VK_MAP:
            vk = _VK_MAP[upper]
        else:
            logger.warning("Unknown key: %s", part)
            return 0, 0

    return modifiers, vk


class GlobalHotkeyManager(QObject):
    """Manages global hotkeys using Win32 RegisterHotKey.

    Runs a message loop in a separate thread to catch WM_HOTKEY messages.
    Emits Qt signals when hotkeys are pressed.
    """

    hotkey_pressed = pyqtSignal(int)  # emits hotkey_id

    def __init__(self) -> None:
        super().__init__()
        self._hotkeys: dict[int, tuple[int, int]] = {}
        self._thread: threading.Thread | None = None
        self._running = False
        self._next_id = 1

    def register(self, hotkey_str: str) -> int:
        """Register a global hotkey. Returns hotkey_id (0 on failure)."""
        modifiers, vk = parse_hotkey(hotkey_str)
        if vk == 0:
            return 0

        hotkey_id = self._next_id
        self._next_id += 1
        self._hotkeys[hotkey_id] = (modifiers, vk)
        return hotkey_id

    def start(self) -> None:
        """Start listening for global hotkeys."""
        self._running = True
        self._thread = threading.Thread(target=self._message_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop listening."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _message_loop(self) -> None:
        """Win32 message loop for hotkey events."""
        user32 = ctypes.windll.user32

        # Register all hotkeys in this thread (required by Win32)
        for hk_id, (modifiers, vk) in self._hotkeys.items():
            success = user32.RegisterHotKey(None, hk_id, modifiers, vk)
            if not success:
                logger.warning("Failed to register hotkey %d", hk_id)

        msg = ctypes.wintypes.MSG()
        while self._running:
            result = user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1)
            if result:
                if msg.message == WM_HOTKEY:
                    self.hotkey_pressed.emit(msg.wParam)
            else:
                import time
                time.sleep(0.05)

        # Unregister
        for hk_id in self._hotkeys:
            user32.UnregisterHotKey(None, hk_id)
