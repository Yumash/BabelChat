"""Application configuration management."""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

if sys.platform == "win32":
    import winreg

logger = logging.getLogger(__name__)


def _get_config_path() -> str:
    """Return config path — user home dir when frozen (AppImage/exe), else CWD."""
    import pathlib

    if getattr(sys, "frozen", False):
        config_dir = pathlib.Path.home() / ".config" / "BabelChat"
        config_dir.mkdir(parents=True, exist_ok=True)
        return str(config_dir / "config.json")
    return "config.json"


CONFIG_FILE = _get_config_path()

# Standard WoW install locations (Windows)
_WOW_PATHS_WINDOWS = [
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

    # Translation providers, keyed by provider id: {"deepl": {"api_key": "..."}}.
    # Generic on purpose — a new provider needs no new config field, and the
    # settings UI renders whatever fields the provider declares.
    providers: dict[str, dict[str, str]] = field(default_factory=dict)
    # GigaChat first: free for individuals, no card, reachable from Russia
    # without a VPN. The others take over if it fails or runs out.
    translator_priority: str = "gigachat"

    # Paths
    wow_path: str = ""
    chatlog_path: str = ""

    # Languages
    ui_language: str = "RU"
    own_language: str = "RU"
    # What incoming chat is translated INTO, so it follows the language the user
    # reads. It defaulted to "ES" — inherited from the Spanish addon this forked
    # from — which meant the first-run summary told a Russian player their chat
    # would be translated into Spanish.
    target_language: str = "RU"

    # Overlay
    overlay_opacity: int = 180
    overlay_font_size: int = 10
    overlay_theme: str = "wow"  # preset id from overlay_theme.PRESETS, or "custom"
    overlay_bg_color: str = "#000000"
    overlay_text_color: str = "#FFFFFF"
    overlay_original_color: str = "#888888"
    overlay_translation_color: str = "#FFD200"
    overlay_timestamp_color: str = "#666666"
    overlay_tl_on_color: str = "#40FF40"
    overlay_tl_off_color: str = "#FF4040"
    overlay_close_color: str = "#FF4040"
    overlay_tool_color: str = "#CCCCCC"
    overlay_corner_radius: int = 8
    overlay_font_family: str = ""  # empty = system default
    overlay_channel_colors: dict = field(default_factory=dict)  # slot → "#RRGGBB"
    overlay_x: int = 100
    overlay_y: int = 100
    overlay_width: int = 450
    overlay_height: int = 300

    # Hotkeys
    hotkey_toggle_translate: str = "Ctrl+Shift+T"
    hotkey_clipboard_translate: str = "Ctrl+Shift+C"

    # Channels
    channels_party: bool = True
    channels_raid: bool = True
    channels_guild: bool = True
    channels_say: bool = True
    channels_whisper: bool = True
    channels_yell: bool = False
    channels_instance: bool = True
    channels_trade: bool = False
    channels_general: bool = False
    channels_services: bool = False
    channels_lfg: bool = False
    # Player-made channels. Off by default: they are usually private, and
    # sending them to a translation service is a decision, not a default.
    channels_custom: bool = True  # see _migrate_split_channels: you join these on purpose
    channels_emote: bool = False

    # Translation
    skip_own_messages: bool = True
    translation_enabled_default: bool = True

    # Debug
    show_debug_console: bool = False
    # Writes every captured chat line to babelchat_raw.log, in full. Useful when
    # capture misbehaves, and off by default because it puts other players'
    # whispers on disk.
    debug_capture_trace: bool = False

    def save(self, path: str = CONFIG_FILE) -> None:
        """Save config to JSON file atomically (write to temp, then rename)."""
        target = Path(path)
        content = json.dumps(asdict(self), indent=2, ensure_ascii=False)

        # Backup existing config
        if target.exists():
            bak = target.with_suffix(".json.bak")
            try:
                bak.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
            except OSError:
                logger.warning("Could not create config backup")

        # Atomic write: temp file in same directory, then rename
        # Use system temp dir — target.parent may be read-only (e.g. AppImage mount)
        fd, tmp_path = tempfile.mkstemp(dir=tempfile.gettempdir(), suffix=".tmp", prefix="config_")
        closed = False
        try:
            os.write(fd, content.encode("utf-8"))
            os.close(fd)
            closed = True
            shutil.move(tmp_path, str(target))
        except OSError:
            if not closed:
                os.close(fd)
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()
            raise

    @classmethod
    def load(cls, path: str = CONFIG_FILE) -> AppConfig:
        """Load config from JSON file, using defaults for missing fields."""
        for try_path in _config_candidates(path):
            try:
                data = json.loads(try_path.read_text(encoding="utf-8"))
                _migrate_provider_keys(data, try_path)
                _migrate_split_channels(data)
                _migrate_gigachat_credential(data)
                defaults = asdict(cls())
                # Ignore unknown keys (e.g. fields removed in newer versions)
                # instead of crashing cls(**...) with a TypeError.
                defaults.update({k: v for k, v in data.items() if k in defaults})
                return cls(**defaults)
            except FileNotFoundError:
                continue
            except json.JSONDecodeError:
                logger.warning("Corrupt config file: %s, trying backup", try_path)
                continue
        logger.warning("No valid config found, using defaults")
        return cls()


def _config_candidates(path: str = CONFIG_FILE) -> list[Path]:
    """Every file `AppConfig.load` will accept a saved config from, in order.

    Declared once so that asking "is there a saved config?" and answering
    "here is the saved config" cannot come to look at different files.
    """
    target = Path(path)
    return [target, target.with_suffix(".json.bak")]


def saved_config_exists(path: str = CONFIG_FILE) -> bool:
    """True when a config this build can actually read is on disk.

    Deliberately not `os.path.exists(CONFIG_FILE)`, which answers a different
    question and gets it wrong in both directions. `load` also reads
    `config.json.bak`, so an absent main file does not mean the user has no
    saved preferences — and it falls back to defaults on a corrupt one, so a
    present main file does not mean any were read. Anything deciding whether
    this is a first run has to ask about the same candidates `load` does.

    Parses rather than stats, for the corrupt case, but does not migrate: the
    migrations write backups of their own, and running them from a question is
    not what a question should do.
    """
    for candidate in _config_candidates(path):
        try:
            json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        return True
    return False


@dataclass(frozen=True, slots=True)
class ChannelToggle:
    """One switch in the settings window, and everything that depends on it.

    Four separate hand-written copies of this mapping used to exist — the two
    settings dialogs, the two entry points, and the overlay's filter tabs — and
    every one of them drifted. Yell had a row on Linux and none on Windows;
    Custom and Emote had rows on Windows and none on Linux; and once both got
    rows, Yell was still read by nobody, because Say quietly enabled it. A
    setting no screen offers cannot be reported. A setting a screen offers and
    the app ignores is worse: the user believes they changed something.
    """

    #: The AppConfig field the checkbox writes.
    field: str
    #: Key into the string table for the checkbox label.
    label: str
    #: Names of the parser channels this switch turns on.
    channels: tuple[str, ...]
    #: Filter tab in the overlay that shows them.
    tab: str


CHANNEL_TOGGLES: tuple[ChannelToggle, ...] = (
    ChannelToggle("channels_party", "settings.ch.party", ("PARTY", "PARTY_LEADER"), "Party"),
    ChannelToggle("channels_raid", "settings.ch.raid", ("RAID", "RAID_LEADER", "RAID_WARNING"), "Raid"),
    ChannelToggle("channels_guild", "settings.ch.guild", ("GUILD", "OFFICER"), "Guild"),
    ChannelToggle("channels_say", "settings.ch.say", ("SAY",), "Say"),
    ChannelToggle("channels_yell", "settings.ch.yell", ("YELL",), "Say"),
    ChannelToggle("channels_whisper", "settings.ch.whisper", ("WHISPER_FROM", "WHISPER_TO"), "Whisper"),
    ChannelToggle("channels_instance", "settings.ch.instance", ("INSTANCE", "INSTANCE_LEADER"), "Instance"),
    ChannelToggle("channels_trade", "settings.ch.trade", ("TRADE",), "Trade"),
    ChannelToggle("channels_general", "settings.ch.general", ("GENERAL",), "General"),
    ChannelToggle("channels_services", "settings.ch.services", ("SERVICES",), "Services"),
    ChannelToggle("channels_lfg", "settings.ch.lfg", ("LOOKING_FOR_GROUP",), "LookingForGroup"),
    ChannelToggle("channels_custom", "settings.ch.custom", ("CUSTOM",), "Custom"),
    ChannelToggle("channels_emote", "settings.ch.emote", ("EMOTE",), "Emote"),
)


#: Tabs whose string-table key is not simply the lower-cased name.
_FILTER_KEYS = {"LookingForGroup": "lfg"}

#: The overlay's filter tabs, in the order they are drawn, paired with the
#: string-table key for each label. Derived from CHANNEL_TOGGLES rather than
#: written out again: both overlays had their own hand-written copy, the Qt one
#: was missing Custom and Emote, and the GTK one showed the tab names in English
#: whatever language the interface was in.
FILTER_TABS: tuple[tuple[str, str], ...] = (
    ("All", "overlay.filter.all"),
    *dict.fromkeys(
        (toggle.tab, "overlay.filter." + _FILTER_KEYS.get(toggle.tab, toggle.tab.lower()))
        for toggle in CHANNEL_TOGGLES
    ),
)


def enabled_channels(config: AppConfig) -> set:
    """The parser channels the user's toggles add up to."""
    from app.parser import Channel

    enabled = set()
    for toggle in CHANNEL_TOGGLES:
        if getattr(config, toggle.field):
            enabled |= {Channel[name] for name in toggle.channels}
    return enabled


def enabled_filter_tabs(config: AppConfig) -> set[str]:
    """The overlay filter tabs the user's toggles add up to."""
    return {toggle.tab for toggle in CHANNEL_TOGGLES if getattr(config, toggle.field)}


def _migrate_gigachat_credential(data: dict) -> None:
    """Split a stored GigaChat authorization key back into its two halves.

    The key is base64 of `client_id:client_secret`, and asking a player for that
    form meant asking them to know what base64 is. The settings screen now shows
    the two values Sber's portal shows, so a config saved before that is decoded
    into them — nobody has to go and fetch their credentials again.

    A value that does not decode into a pair is left exactly where it is. It
    still works: the backend falls back to the stored key. Discarding a working
    credential because this function did not recognise it would be the worse
    failure by far.
    """
    from app.translators.gigachat_credential import split_authorization_key

    settings = (data.get("providers") or {}).get("gigachat")
    if not isinstance(settings, dict):
        return
    if settings.get("client_id") or settings.get("client_secret"):
        return

    client_id, client_secret = split_authorization_key(settings.get("authorization_key") or "")
    if not client_id:
        return
    settings["client_id"] = client_id
    settings["client_secret"] = client_secret
    settings.pop("authorization_key", None)


def _migrate_split_channels(data: dict) -> None:
    """Carry a setting across when one channel becomes two.

    Emotes used to be delivered as Say — the reader mapped EMOTE onto it — so
    anyone with Say on was having emotes translated without ever being asked.
    Giving emotes their own toggle is right, but shipping it off by default
    would take that away silently on upgrade: nothing breaks, a kind of message
    simply stops appearing, which is the hardest sort of change to notice or
    report.

    So a config that predates the toggle inherits whatever Say was set to. A
    config that has the key keeps its own answer, and a fresh install still gets
    the documented default.
    """
    if "channels_emote" not in data and "channels_say" in data:
        data["channels_emote"] = bool(data["channels_say"])
    # Yell was bundled into Say for the same reason and now has its own toggle,
    # so it inherits the same way. Its old default was off, but what the user
    # actually experienced was "Say is on, therefore yells are translated".
    if "channels_yell" not in data and "channels_say" in data:
        data["channels_yell"] = bool(data["channels_say"])
    # A player-made channel now has a switch of its own, and it is on. Trade and
    # General are off because you are in them whether you like it or not and
    # they are firehoses; a channel you typed /join for is the opposite — you
    # asked to be there, and it is usually the guild's alt channel or a group of
    # friends, which is exactly the chat worth translating.
    #
    # This deliberately does NOT inherit General, which is what it did first.
    # Inheriting was defensible — an unrecognised channel used to be reported as
    # General, so General's setting had been governing these messages — but the
    # result was that joining a channel and typing in it produced nothing at
    # all, with the reason buried in a debug log. Being wrong in the direction
    # of a translation nobody wanted beats being wrong in the direction of
    # silence.
    data.setdefault("channels_custom", True)


# Config written before providers became generic: one flat field per provider
# per credential. Mapped onto the new shape as {provider: {field: value}}.
_LEGACY_PROVIDER_KEYS = {
    "deepl_api_key": ("deepl", "api_key"),
    "microsoft_api_key": ("microsoft", "api_key"),
    "microsoft_region": ("microsoft", "region"),
}


def _migrate_provider_keys(data: dict, source: Path) -> None:
    """Fold pre-registry API-key fields into `providers`, in place.

    Runs before unknown keys are dropped — otherwise upgrading would silently
    discard the user's API keys and present them with an unconfigured app. A
    copy of the original file is kept alongside it the first time this happens,
    because the ordinary `.json.bak` gets overwritten by the very next save.
    """
    legacy = {k: v for k, v in data.items() if k in _LEGACY_PROVIDER_KEYS and str(v).strip()}
    if not legacy:
        return

    providers = data.setdefault("providers", {})
    if not isinstance(providers, dict):
        logger.warning("Ignoring malformed 'providers' section while migrating API keys")
        providers = {}
        data["providers"] = providers

    migrated = []
    for key, value in legacy.items():
        provider_id, field_name = _LEGACY_PROVIDER_KEYS[key]
        settings = providers.setdefault(provider_id, {})
        # A value already present in the new shape wins: it is the one the user
        # last edited, and re-running the migration must not undo that.
        if not settings.get(field_name):
            settings[field_name] = value
            migrated.append(f"{provider_id}.{field_name}")

    if not migrated:
        return

    backup = source.with_suffix(".json.pre-providers.bak")
    if not backup.exists():
        try:
            backup.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        except OSError:
            logger.warning("Could not write pre-migration config backup")
    logger.info("Migrated API keys to the provider registry: %s", ", ".join(migrated))


def detect_wow_path() -> str:
    """Try to find WoW installation path."""
    if sys.platform == "win32":
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

        for p in _WOW_PATHS_WINDOWS:
            if p.exists():
                return str(p)
    else:
        # On Linux, WoW can be installed anywhere (Steam library, NTFS drive, etc.)
        # Auto-detection is unreliable — return empty and let the user set it via GUI.
        return ""

    return ""


def resolve_chatlog_path(config: AppConfig) -> Path:
    """Resolve the WoW Chat Log file path from config."""
    if config.chatlog_path:
        return Path(config.chatlog_path)

    wow_path = config.wow_path or detect_wow_path()
    if wow_path:
        return Path(wow_path) / _CHATLOG_RELATIVE

    return Path("WoWChatLog.txt")
