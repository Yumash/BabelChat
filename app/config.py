"""Application configuration management."""

from __future__ import annotations

import json
import logging
import winreg
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"

# Standard WoW install locations
_WOW_PATHS = [
    Path("C:/Program Files (x86)/World of Warcraft"),
    Path("C:/Program Files/World of Warcraft"),
    Path("D:/World of Warcraft"),
    Path("D:/Games/World of Warcraft"),
]

# WoW Chat Log relative path inside WoW install
_CHATLOG_RELATIVE = "_retail_/Logs/WoWChatLog.txt"


@dataclass
class AppConfig:
    """Application settings."""

    # API
    deepl_api_key: str = ""

    # Paths
    wow_path: str = ""
    chatlog_path: str = ""

    # Languages
    ui_language: str = "RU"
    own_language: str = "RU"
    target_language: str = "EN"

    # Overlay
    overlay_opacity: int = 180
    overlay_font_size: int = 10
    overlay_x: int = 100
    overlay_y: int = 100
    overlay_width: int = 450
    overlay_height: int = 300

    # Hotkeys
    hotkey_toggle_translate: str = "Ctrl+Shift+T"
    hotkey_toggle_interactive: str = "Ctrl+Shift+I"
    hotkey_clipboard_translate: str = "Ctrl+Shift+C"

    # Channels
    channels_party: bool = True
    channels_raid: bool = True
    channels_guild: bool = True
    channels_say: bool = True
    channels_whisper: bool = True
    channels_yell: bool = False
    channels_instance: bool = True

    # Translation
    translation_enabled_default: bool = True

    def save(self, path: str = CONFIG_FILE) -> None:
        """Save config to JSON file."""
        Path(path).write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str = CONFIG_FILE) -> AppConfig:
        """Load config from JSON file, using defaults for missing fields."""
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            defaults = asdict(cls())
            defaults.update(data)
            return cls(**defaults)
        except (FileNotFoundError, json.JSONDecodeError):
            return cls()


def detect_wow_path() -> str:
    """Try to find WoW installation path."""
    # Try registry first (Battle.net launcher)
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Blizzard Entertainment\World of Warcraft",
        )
        install_path, _ = winreg.QueryValueEx(key, "InstallPath")
        winreg.CloseKey(key)
        if Path(install_path).exists():
            return str(install_path)
    except (FileNotFoundError, OSError):
        pass

    # Try standard paths
    for p in _WOW_PATHS:
        if p.exists():
            return str(p)

    return ""


def resolve_chatlog_path(config: AppConfig) -> Path:
    """Resolve the WoW Chat Log file path from config."""
    if config.chatlog_path:
        return Path(config.chatlog_path)

    wow_path = config.wow_path or detect_wow_path()
    if wow_path:
        return Path(wow_path) / _CHATLOG_RELATIVE

    return Path("WoWChatLog.txt")
