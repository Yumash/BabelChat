"""Parser for WoW Chat Log format."""

from __future__ import annotations

import re
import time
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


# Map raw log channel names to enum (English + Russian client)
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
    # Russian client channel names
    "Сказать": Channel.SAY,
    "Крик": Channel.YELL,
    "Группа": Channel.PARTY,
    "Лидер группы": Channel.PARTY_LEADER,
    "Рейд": Channel.RAID,
    "Лидер рейда": Channel.RAID_LEADER,
    "Объявление рейда": Channel.RAID_WARNING,
    "Объявление рейду": Channel.RAID_WARNING,
    "Гильдия": Channel.GUILD,
    "Офицер": Channel.OFFICER,
    "Подземелье": Channel.INSTANCE,
    "Лидер подземелья": Channel.INSTANCE_LEADER,
}

# Map |Hchannel:XXX| hyperlink IDs to enum (used by non-EN clients)
_HCHANNEL_MAP: dict[str, Channel] = {
    "SAY": Channel.SAY,
    "YELL": Channel.YELL,
    "PARTY": Channel.PARTY,
    "PARTY_LEADER": Channel.PARTY_LEADER,
    "RAID": Channel.RAID,
    "RAID_LEADER": Channel.RAID_LEADER,
    "RAID_WARNING": Channel.RAID_WARNING,
    "GUILD": Channel.GUILD,
    "OFFICER": Channel.OFFICER,
    "INSTANCE_CHAT": Channel.INSTANCE,
    "INSTANCE_CHAT_LEADER": Channel.INSTANCE_LEADER,
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
# Also supports [Channel] [Author-Server]: text (RU client AddMessage format)
_RE_CHANNEL_MSG = re.compile(
    r"^(\d+/\d+\s+\d+:\d+:\d+\.\d+)\s+"  # timestamp
    r"\[([^\]]+)\]\s+"  # [Channel]
    r"\[?([^-\s:\]]+)"  # Author (optional [ bracket)
    r"(?:-([^\s:\]]+))?\]?"  # -Server (optional, optional ] bracket)
    r":\s+"  # : separator
    r"(.+)$"  # message text
)

# Non-EN client format: timestamp  |Hchannel:TYPE|h[LocalizedName]|h Author-Server: text
# Author may be wrapped in |Hplayer:...|h[Author-Server]|h from AddMessage hook
_RE_HCHANNEL_MSG = re.compile(
    r"^(\d+/\d+\s+\d+:\d+:\d+\.\d+)\s+"  # timestamp
    r"\|Hchannel:(\w+)\|h\[[^\]]*\]\|h\s+"  # |Hchannel:TYPE|h[Name]|h
    r"(?:\|Hplayer:[^|]*\|h)?"  # optional |Hplayer:...|h wrapper
    r"\[?([^-\s:\]|]+)"  # Author (allow optional [ bracket, stop at |)
    r"(?:-([^\s:\]|]+))?"  # -Server (optional)
    r"\]?(?:\|h)?"  # optional ] and |h close
    r":\s+"  # : separator
    r"(.+)$"  # message text
)

# Bracket channel + player hyperlink format (RU scrollback):
# timestamp  [Объявление рейду] |Hplayer:Name-Server:flags:TYPE:|h[Name-Server]|h: text
# This format appears in ChatFrame scrollback for channels like Raid Warning
# where the channel name is localized in brackets, not as |Hchannel:...|h.
_RE_BRACKET_HPLAYER_MSG = re.compile(
    r"^(\d+/\d+\s+\d+:\d+:\d+\.\d+)\s+"  # timestamp
    r"\[([^\]]+)\]\s+"  # [Channel Name]
    r"\|Hplayer:[^|]*\|h"  # |Hplayer:...|h wrapper
    r"\[([^-\]|]+)"  # [Author
    r"(?:-([^\]|]+))?\]"  # -Server]
    r"\|h"  # closing |h
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
# Also handles |Hplayer:...|h[Author]|h wrapper from AddMessage
_RE_WHISPER_FROM = re.compile(
    r"^(\d+/\d+\s+\d+:\d+:\d+\.\d+)\s+"  # timestamp
    r"(?:\|Hplayer:[^|]*\|h)?"  # optional |Hplayer:...|h
    r"\[([^-\]|]+)"  # [Author (stop at - ] or |)
    r"(?:-([^\]|]+))?\]"  # -Server]
    r"(?:\|h)?\s+"  # optional |h close
    r"(?:whispers|шепчет):\s+"  # whispers: / шепчет:
    r"(.+)$"  # text
)

# Whisper TO (Russian): timestamp  Кому [Author-Server]: text
_RE_WHISPER_TO_RU = re.compile(
    r"^(\d+/\d+\s+\d+:\d+:\d+\.\d+)\s+"  # timestamp
    r"Кому\s+\[([^-\]]+)"  # Кому [Author
    r"(?:-([^\]]+))?\]"  # -Server]
    r":\s+"  # :
    r"(.+)$"  # text
)

# Say/Yell from AddMessage hook (no [Channel] prefix, uses verb):
# Player: |Hplayer:Name-Server:flags|h[Name-Server]|h говорит: text
# NPC:    NPC Name говорит: text  (no hyperlink, name may have spaces)
_SAY_YELL_VERB_MAP: dict[str, Channel] = {
    "says": Channel.SAY,
    "yells": Channel.YELL,
    "говорит": Channel.SAY,
    "кричит": Channel.YELL,
}
# Player format: |Hplayer:...|h[Name-Server]|h verb: text
_RE_SAY_YELL_PLAYER = re.compile(
    r"^(\d+/\d+\s+\d+:\d+:\d+\.\d+)\s+"  # timestamp
    r"\|Hplayer:[^|]*\|h"  # |Hplayer:...|h
    r"\[([^-\]|]+)"  # [Author
    r"(?:-([^\]|]+))?\]"  # -Server]
    r"\|h\s+"  # |h + space
    r"(says|yells|говорит|кричит):\s+"  # verb
    r"(.+)$"  # text
)
# NPC/plain format: Name verb: text (name = everything before verb)
_RE_SAY_YELL_PLAIN = re.compile(
    r"^(\d+/\d+\s+\d+:\d+:\d+\.\d+)\s+"  # timestamp
    r"(.+?)\s+"  # Author (non-greedy, may have spaces)
    r"(says|yells|говорит|кричит):\s+"  # verb
    r"(.+)$"  # text
)

# Whisper TO (RU AddMessage): "Вы шепчете [Name]: text"
# Also handles |3-2(|Kj4|k) BattleNet format
_RE_WHISPER_TO_ADDMSG = re.compile(
    r"^(\d+/\d+\s+\d+:\d+:\d+\.\d+)\s+"  # timestamp
    r"(?:Вы шепчете|You whisper)\s+"  # RU/EN prefix
    r"(?:\|Hplayer:[^|]*\|h)?"  # optional |Hplayer:...|h
    r"\[?([^-\]|:]+)"  # Author (flexible)
    r"(?:-([^\]|:]+))?\]?"  # -Server (optional)
    r"(?:\|h)?:\s+"  # optional |h, then : separator
    r"(.+)$"  # text
)

# Whisper FROM (RU AddMessage): "[Fury] шепчет: text"
# Also: |Hplayer:...|h[Name]|h шепчет: text
_RE_WHISPER_FROM_ADDMSG = re.compile(
    r"^(\d+/\d+\s+\d+:\d+:\d+\.\d+)\s+"  # timestamp
    r"(?:\|Hplayer:[^|]*\|h)?"  # optional |Hplayer:...|h
    r"\[([^-\]|]+)"  # [Author
    r"(?:-([^\]|]+))?\]"  # -Server]
    r"(?:\|h)?\s+"  # optional |h
    r"(?:whispers|шепчет):\s+"  # verb
    r"(.+)$"  # text
)

# System message patterns to filter out
_SYSTEM_PATTERNS = [
    re.compile(r"has joined|has left|has come online|has gone offline", re.IGNORECASE),
    re.compile(r"присоединился|покинул|входит в игру|выходит из игры"),
    re.compile(r"^\|c[0-9a-fA-F]{8}\|H"),  # WoW item/spell links
    re.compile(r"^LOOT:"),
    re.compile(r"^You (receive|create|gain|lose|die|earned)"),
    re.compile(r"заслужил[аи]?\s+достижение"),  # RU achievements
    re.compile(r"получает добычу|получает предмет"),  # RU loot
]


def _strip_wow_markup(text: str) -> str:
    """Remove WoW hyperlink markup from text (|cXXXX|Hxxx|hText|h|r)."""
    return re.sub(r"\|c[0-9a-fA-F]{8}|\|r|\|H[^|]*\|h|\|h", "", text)


# Full WoW hyperlink pattern: |cXXXXXXXX|Htype:data|h[Display Name]|h|r
_RE_WOW_LINK = re.compile(r"\|c[0-9a-fA-F]{8}\|H[^|]+\|h\[[^\]]*\]\|h\|r")


def _is_item_link_only(raw_text: str) -> bool:
    """Return True if raw text consists entirely of WoW item/spell links (no real words)."""
    stripped = _RE_WOW_LINK.sub("", raw_text).strip()
    return len(stripped) == 0 and _RE_WOW_LINK.search(raw_text) is not None


def _clean_text(raw_text: str) -> str | None:
    """Strip WoW markup and filter out item-link-only / system messages. Returns None to skip."""
    raw = raw_text.strip()
    if _is_item_link_only(raw):
        return None
    text = _strip_wow_markup(raw)
    if _is_system_message(text):
        return None
    return text


_RE_COLOR_CODES = re.compile(r"\|c[0-9a-fA-F]{8}|\|r")


def parse_line(line: str) -> ChatMessage | None:
    """Parse a single WoW Chat Log line into a ChatMessage.

    Supports both English and non-English (hyperlink-style) WoW clients.
    Returns None if the line is unparseable or a system message.
    """
    # Strip inline color codes (|cXXXXXXXX and |r) but keep hyperlinks
    # (|Hchannel:...|h, |Hplayer:...|h).  Addon may send raw markup with
    # color-coded player names like [|cff3fc7ebName-Server|r].
    line = _RE_COLOR_CODES.sub("", line)

    # Try whisper TO (English: "To [Author]", Russian: "Кому [Author]")
    for regex in (_RE_WHISPER_TO, _RE_WHISPER_TO_RU):
        m = regex.match(line)
        if m:
            text = _clean_text(m.group(4))
            if text is None:
                return None
            return ChatMessage(
                timestamp=m.group(1),
                channel=Channel.WHISPER_TO,
                author=m.group(2),
                server=m.group(3) or "",
                text=text,
            )

    # Try whisper FROM (English: "whispers:", Russian: "шепчет:")
    m = _RE_WHISPER_FROM.match(line)
    if m:
        text = _clean_text(m.group(4))
        if text is None:
            return None
        return ChatMessage(
            timestamp=m.group(1),
            channel=Channel.WHISPER_FROM,
            author=m.group(2),
            server=m.group(3) or "",
            text=text,
        )

    # Try non-EN hyperlink format: |Hchannel:TYPE|h[Name]|h Author: text
    m = _RE_HCHANNEL_MSG.match(line)
    if m:
        channel_id = m.group(2)
        channel = _HCHANNEL_MAP.get(channel_id)
        if channel is None:
            return None

        text = _clean_text(m.group(5))
        if text is None:
            return None
        return ChatMessage(
            timestamp=m.group(1),
            channel=channel,
            author=m.group(3),
            server=m.group(4) or "",
            text=text,
        )

    # Try bracket channel + player hyperlink: [Channel] |Hplayer:...|h[Name]|h: text
    m = _RE_BRACKET_HPLAYER_MSG.match(line)
    if m:
        channel_name = m.group(2)
        channel = _CHANNEL_MAP.get(channel_name)
        if channel is not None:
            text = _clean_text(m.group(5))
            if text is not None:
                return ChatMessage(
                    timestamp=m.group(1),
                    channel=channel,
                    author=m.group(3),
                    server=m.group(4) or "",
                    text=text,
                )

    # Try standard EN channel message: [Channel] Author: text
    m = _RE_CHANNEL_MSG.match(line)
    if m:
        channel_name = m.group(2)
        channel = _CHANNEL_MAP.get(channel_name)
        if channel is None:
            return None  # Unknown channel (e.g., numbered channels, trade, etc.)

        text = _clean_text(m.group(5))
        if text is None:
            return None
        return ChatMessage(
            timestamp=m.group(1),
            channel=channel,
            author=m.group(3),
            server=m.group(4) or "",
            text=text,
        )

    # Try AddMessage whisper formats (Вы шепчете / You whisper)
    m = _RE_WHISPER_TO_ADDMSG.match(line)
    if m:
        text = _clean_text(m.group(4))
        if text is None:
            return None
        return ChatMessage(
            timestamp=m.group(1),
            channel=Channel.WHISPER_TO,
            author=m.group(2),
            server=m.group(3) or "",
            text=text,
        )

    m = _RE_WHISPER_FROM_ADDMSG.match(line)
    if m:
        text = _clean_text(m.group(4))
        if text is None:
            return None
        return ChatMessage(
            timestamp=m.group(1),
            channel=Channel.WHISPER_FROM,
            author=m.group(2),
            server=m.group(3) or "",
            text=text,
        )

    # Try Say/Yell player format: |Hplayer:...|h[Name]|h говорит: text
    m = _RE_SAY_YELL_PLAYER.match(line)
    if m:
        verb = m.group(4).lower()
        channel = _SAY_YELL_VERB_MAP.get(verb)
        if channel:
            text = _clean_text(m.group(5))
            if text is not None:
                return ChatMessage(
                    timestamp=m.group(1),
                    channel=channel,
                    author=m.group(2),
                    server=m.group(3) or "",
                    text=text,
                )

    # Try Say/Yell plain format: NPC Name говорит: text
    m = _RE_SAY_YELL_PLAIN.match(line)
    if m:
        verb = m.group(3).lower()
        channel = _SAY_YELL_VERB_MAP.get(verb)
        if channel:
            text = _clean_text(m.group(4))
            if text is not None:
                # Author may have spaces (NPC names); no server
                return ChatMessage(
                    timestamp=m.group(1),
                    channel=channel,
                    author=m.group(2).strip(),
                    server="",
                    text=text,
                )

    return None


def _is_system_message(text: str) -> bool:
    """Check if the message text matches known system message patterns."""
    return any(p.search(text) for p in _SYSTEM_PATTERNS)


# Map addon CHAT_MSG_* event channel names to Channel enum
_ADDON_CHANNEL_MAP: dict[str, Channel] = {
    "SAY": Channel.SAY,
    "YELL": Channel.YELL,
    "PARTY": Channel.PARTY,
    "PARTY_LEADER": Channel.PARTY_LEADER,
    "RAID": Channel.RAID,
    "RAID_LEADER": Channel.RAID_LEADER,
    "RAID_WARNING": Channel.RAID_WARNING,
    "GUILD": Channel.GUILD,
    "OFFICER": Channel.OFFICER,
    "WHISPER": Channel.WHISPER_FROM,
    "WHISPER_INFORM": Channel.WHISPER_TO,
    "INSTANCE_CHAT": Channel.INSTANCE,
    "INSTANCE_CHAT_LEADER": Channel.INSTANCE_LEADER,
}


def parse_addon_line(line: str) -> tuple[ChatMessage | None, int]:
    """Parse a line from the addon's memory buffer.

    Format: SEQ|CHANNEL|Author-Server|MessageText

    Returns (ChatMessage or None, sequence_number).
    """
    parts = line.split("|", 3)
    if len(parts) < 4:
        return None, 0

    seq_str, channel_str, author_full, text = parts

    try:
        seq = int(seq_str)
    except ValueError:
        return None, 0

    channel = _ADDON_CHANNEL_MAP.get(channel_str)
    if channel is None:
        return None, seq

    # Split author into name and server
    if "-" in author_full:
        author, server = author_full.split("-", 1)
    else:
        author, server = author_full, ""

    text = _clean_text(text)
    if text is None:
        return None, seq

    t = time.localtime()
    timestamp = f"{t.tm_mon}/{t.tm_mday} {t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}.000"

    return ChatMessage(
        timestamp=timestamp,
        channel=channel,
        author=author,
        server=server,
        text=text,
    ), seq
