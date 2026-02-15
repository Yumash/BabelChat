"""Parser for WoW Chat Log format."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Channel(Enum):
    SAY = "Say"
    YELL = "Yell"
    PARTY = "Party"
    PARTY_LEADER = "Party Leader"
    RAID = "Raid"
    RAID_LEADER = "Raid Leader"
    RAID_WARNING = "Raid Warning"
    GUILD = "Guild"
    OFFICER = "Officer"
    WHISPER_FROM = "Whisper From"
    WHISPER_TO = "Whisper To"
    INSTANCE = "Instance"
    INSTANCE_LEADER = "Instance Leader"


# Map raw log channel names to enum
_CHANNEL_MAP: dict[str, Channel] = {
    "Say": Channel.SAY,
    "Yell": Channel.YELL,
    "Party": Channel.PARTY,
    "Party Leader": Channel.PARTY_LEADER,
    "Raid": Channel.RAID,
    "Raid Leader": Channel.RAID_LEADER,
    "Raid Warning": Channel.RAID_WARNING,
    "Guild": Channel.GUILD,
    "Officer": Channel.OFFICER,
    "Instance": Channel.INSTANCE,
    "Instance Leader": Channel.INSTANCE_LEADER,
}


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """Parsed chat message."""

    timestamp: str
    channel: Channel
    author: str
    server: str
    text: str

    @property
    def is_whisper(self) -> bool:
        return self.channel in (Channel.WHISPER_FROM, Channel.WHISPER_TO)


# WoW Chat Log format examples:
# 2/15 21:30:45.123  [Party] Артас-Азурегос: Привет всем
# 2/15 21:30:45.123  [Raid Leader] Thrall-Sargeras: Pull in 5
# 2/15 21:30:45.123  [Guild] Sylvanas-Ravencrest: lfg m+
# 2/15 21:30:45.123  To [Артас-Азурегос]: whisper text
# 2/15 21:30:45.123  [Артас-Азурегос] whispers: incoming text

# Standard channel message: timestamp  [Channel] Author-Server: text
_RE_CHANNEL_MSG = re.compile(
    r"^(\d+/\d+\s+\d+:\d+:\d+\.\d+)\s+"  # timestamp
    r"\[([^\]]+)\]\s+"  # [Channel]
    r"([^-\s:]+)"  # Author
    r"(?:-(\S+))?"  # -Server (optional)
    r":\s+"  # : separator
    r"(.+)$"  # message text
)

# Whisper TO: timestamp  To [Author-Server]: text
_RE_WHISPER_TO = re.compile(
    r"^(\d+/\d+\s+\d+:\d+:\d+\.\d+)\s+"  # timestamp
    r"To\s+\[([^-\]]+)"  # To [Author
    r"(?:-([^\]]+))?\]"  # -Server]
    r":\s+"  # :
    r"(.+)$"  # text
)

# Whisper FROM: timestamp  [Author-Server] whispers: text
_RE_WHISPER_FROM = re.compile(
    r"^(\d+/\d+\s+\d+:\d+:\d+\.\d+)\s+"  # timestamp
    r"\[([^-\]]+)"  # [Author
    r"(?:-([^\]]+))?\]\s+"  # -Server]
    r"whispers:\s+"  # whispers:
    r"(.+)$"  # text
)

# System message patterns to filter out
_SYSTEM_PATTERNS = [
    re.compile(r"has joined|has left|has come online|has gone offline", re.IGNORECASE),
    re.compile(r"^\|c[0-9a-fA-F]{8}\|H"),  # WoW item/spell links
    re.compile(r"^LOOT:"),
    re.compile(r"^You (receive|create|gain|lose|die|earned)"),
]


def parse_line(line: str) -> ChatMessage | None:
    """Parse a single WoW Chat Log line into a ChatMessage.

    Returns None if the line is unparseable or a system message.
    """
    # Try whisper TO first (has distinctive "To [" prefix)
    m = _RE_WHISPER_TO.match(line)
    if m:
        text = m.group(4).strip()
        if _is_system_message(text):
            return None
        return ChatMessage(
            timestamp=m.group(1),
            channel=Channel.WHISPER_TO,
            author=m.group(2),
            server=m.group(3) or "",
            text=text,
        )

    # Try whisper FROM
    m = _RE_WHISPER_FROM.match(line)
    if m:
        text = m.group(4).strip()
        if _is_system_message(text):
            return None
        return ChatMessage(
            timestamp=m.group(1),
            channel=Channel.WHISPER_FROM,
            author=m.group(2),
            server=m.group(3) or "",
            text=text,
        )

    # Try standard channel message
    m = _RE_CHANNEL_MSG.match(line)
    if m:
        channel_name = m.group(2)
        channel = _CHANNEL_MAP.get(channel_name)
        if channel is None:
            return None  # Unknown channel (e.g., numbered channels, trade, etc.)

        text = m.group(5).strip()
        if _is_system_message(text):
            return None
        return ChatMessage(
            timestamp=m.group(1),
            channel=channel,
            author=m.group(3),
            server=m.group(4) or "",
            text=text,
        )

    return None


def _is_system_message(text: str) -> bool:
    """Check if the message text matches known system message patterns."""
    return any(p.search(text) for p in _SYSTEM_PATTERNS)
