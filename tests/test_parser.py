"""Tests for WoW Chat Log parser."""

import pytest

from app.parser import Channel, parse_addon_line, parse_line


class TestParseChannelMessages:
    """Test parsing standard channel messages."""

    def test_party_message(self):
        line = '2/15 21:30:45.123  [Party] Артас-Азурегос: Привет всем'
        msg = parse_line(line)
        assert msg is not None
        assert msg.channel == Channel.PARTY
        assert msg.author == "Артас"
        assert msg.server == "Азурегос"
        assert msg.text == "Привет всем"
        assert msg.timestamp == "2/15 21:30:45.123"

    def test_raid_leader_message(self):
        line = '2/15 21:30:45.123  [Raid Leader] Thrall-Sargeras: Pull in 5'
        msg = parse_line(line)
        assert msg is not None
        assert msg.channel == Channel.RAID_LEADER
        assert msg.author == "Thrall"
        assert msg.server == "Sargeras"
        assert msg.text == "Pull in 5"

    def test_guild_message(self):
        line = '2/15 21:30:45.123  [Guild] Sylvanas-Ravencrest: lfg m+'
        msg = parse_line(line)
        assert msg is not None
        assert msg.channel == Channel.GUILD
        assert msg.author == "Sylvanas"
        assert msg.text == "lfg m+"

    def test_say_message(self):
        line = '2/15 21:30:45.123  [Say] PlayerName-ServerName: Hello World'
        msg = parse_line(line)
        assert msg is not None
        assert msg.channel == Channel.SAY
        assert msg.text == "Hello World"

    def test_yell_message(self):
        line = '2/15 21:30:45.123  [Yell] Angry-Player: FOR THE HORDE!!!'
        msg = parse_line(line)
        assert msg is not None
        assert msg.channel == Channel.YELL
        assert msg.text == "FOR THE HORDE!!!"

    def test_raid_warning(self):
        line = '2/15 21:30:45.123  [Raid Warning] Leader-Server: Move away from fire!'
        msg = parse_line(line)
        assert msg is not None
        assert msg.channel == Channel.RAID_WARNING

    def test_no_server(self):
        line = '2/15 21:30:45.123  [Say] PlayerName: Hello'
        msg = parse_line(line)
        assert msg is not None
        assert msg.author == "PlayerName"
        assert msg.server == ""


class TestParseWhispers:
    """Test parsing whisper messages."""

    def test_whisper_from(self):
        line = '2/15 21:30:45.123  [Артас-Азурегос] whispers: тайное сообщение'
        msg = parse_line(line)
        assert msg is not None
        assert msg.channel == Channel.WHISPER_FROM
        assert msg.author == "Артас"
        assert msg.server == "Азурегос"
        assert msg.text == "тайное сообщение"

    def test_whisper_to(self):
        line = '2/15 21:30:45.123  To [Артас-Азурегос]: мой ответ'
        msg = parse_line(line)
        assert msg is not None
        assert msg.channel == Channel.WHISPER_TO
        assert msg.author == "Артас"
        assert msg.server == "Азурегос"
        assert msg.text == "мой ответ"

    def test_whisper_is_whisper(self):
        line = '2/15 21:30:45.123  [Player-Server] whispers: hi'
        msg = parse_line(line)
        assert msg is not None
        assert msg.is_whisper is True


class TestParseEdgeCases:
    """Test edge cases in parsing."""

    def test_unknown_channel_returns_none(self):
        line = '2/15 21:30:45.123  [Trade] Spammer-Server: WTS boost'
        msg = parse_line(line)
        assert msg is None

    def test_empty_line_returns_none(self):
        assert parse_line("") is None

    def test_garbage_returns_none(self):
        assert parse_line("this is not a valid log line") is None

    def test_system_message_filtered(self):
        line = '2/15 21:30:45.123  [Guild] Player-Server: has come online'
        msg = parse_line(line)
        assert msg is None

    def test_loot_message_filtered(self):
        line = '2/15 21:30:45.123  [Say] Player-Server: LOOT: something'
        msg = parse_line(line)
        assert msg is None

    def test_wow_item_link_filtered(self):
        line = (
            "2/15 21:30:45.123  [Party] Player-Server:"
            " |cFFFF8800|Hitem:12345|h[Sword of Truth]|h|r"
        )
        msg = parse_line(line)
        assert msg is None

    def test_message_with_colon_in_text(self):
        line = '2/15 21:30:45.123  [Party] Player-Server: boss at 50%: phase 2'
        msg = parse_line(line)
        assert msg is not None
        assert msg.text == "boss at 50%: phase 2"

    def test_cyrillic_author(self):
        line = '2/15 21:30:45.123  [Party] Кириллик-Сервер: текст сообщения'
        msg = parse_line(line)
        assert msg is not None
        assert msg.author == "Кириллик"
        assert msg.server == "Сервер"


class TestParserRobustness:
    """Robustness tests for edge cases, malformed input, and Unicode."""

    def test_wow_color_codes_in_message(self):
        line = '2/15 21:30:45.123  [Party] Player-Server: |cff00ff00Green text|r normal'
        msg = parse_line(line)
        assert msg is not None
        assert "|cff00ff00" in msg.text or "Green text" in msg.text

    def test_message_with_pipe_chars(self):
        line = '2/15 21:30:45.123  [Party] Player-Server: result: 5|10 score'
        msg = parse_line(line)
        assert msg is not None
        assert "5|10" in msg.text

    def test_truncated_line_no_text(self):
        line = '2/15 21:30:45.123  [Party] Player-Server:'
        msg = parse_line(line)
        # Should return None or empty text, not crash
        assert msg is None or msg.text == ""

    def test_empty_author(self):
        line = '2/15 21:30:45.123  [Party] : some text'
        msg = parse_line(line)
        # Should handle gracefully
        assert msg is None or msg.author == ""

    def test_unicode_chinese(self):
        line = '2/15 21:30:45.123  [Party] 玩家-服务器: 大家好世界'
        msg = parse_line(line)
        assert msg is not None
        assert msg.text == "大家好世界"

    def test_unicode_korean(self):
        line = '2/15 21:30:45.123  [Say] 플레이어-서버: 안녕하세요'
        msg = parse_line(line)
        assert msg is not None
        assert msg.text == "안녕하세요"

    def test_unicode_emoji(self):
        line = '2/15 21:30:45.123  [Party] Player-Server: nice pull 🎉🔥'
        msg = parse_line(line)
        assert msg is not None
        assert "🎉" in msg.text

    def test_very_long_message(self):
        long_text = "a" * 1500
        line = f'2/15 21:30:45.123  [Party] Player-Server: {long_text}'
        msg = parse_line(line)
        assert msg is not None
        assert len(msg.text) >= 1000

    def test_null_bytes_in_line(self):
        line = '2/15 21:30:45.123  [Party] Player-Server: hello\x00world'
        # Should not crash
        try:
            parse_line(line)
        except Exception:
            pytest.fail("parse_line raised on null bytes")

    def test_only_whitespace_text(self):
        line = '2/15 21:30:45.123  [Party] Player-Server:    '
        msg = parse_line(line)
        assert msg is None or msg.text.strip() == ""

    def test_multiple_colons(self):
        line = '2/15 21:30:45.123  [Raid] Leader-Server: time: 12:30: pull now: go'
        msg = parse_line(line)
        assert msg is not None
        assert "12:30" in msg.text
        assert "pull now" in msg.text

    def test_special_chars_in_text(self):
        line = '2/15 21:30:45.123  [Guild] Player-Server: <AFK> [Away] {brb} (5min)'
        msg = parse_line(line)
        assert msg is not None
        assert "<AFK>" in msg.text

    def test_tab_in_message(self):
        line = '2/15 21:30:45.123  [Party] Player-Server: col1\tcol2\tcol3'
        msg = parse_line(line)
        assert msg is not None

    def test_mixed_cyrillic_latin(self):
        line = '2/15 21:30:45.123  [Party] Player-Server: привет hello мир world'
        msg = parse_line(line)
        assert msg is not None
        assert "привет" in msg.text
        assert "hello" in msg.text

    def test_completely_invalid_timestamp(self):
        line = 'NOT-A-TIMESTAMP  [Party] Player-Server: hello'
        msg = parse_line(line)
        assert msg is None

    def test_missing_brackets(self):
        line = '2/15 21:30:45.123  Party Player-Server: hello'
        msg = parse_line(line)
        assert msg is None


class TestParseAddonLine:
    """Tests for parse_addon_line (v2.1 and legacy formats)."""

    def test_raw_v21_format(self):
        line = "42|RAW|SAY|Thrall-Sargeras|Hello world"
        msg, seq = parse_addon_line(line)
        assert seq == 42
        assert msg is not None
        assert msg.channel == Channel.SAY
        assert msg.author == "Thrall"
        assert msg.text == "Hello world"

    def test_dict_v21_format(self):
        line = "5|DICT|GUILD|Player-Server|some text with terms"
        msg, seq = parse_addon_line(line)
        assert seq == 5
        assert msg is not None
        assert msg.channel == Channel.GUILD

    def test_invalid_seq(self):
        line = "abc|RAW|SAY|Player|hello"
        msg, seq = parse_addon_line(line)
        assert msg is None
        assert seq == 0

    def test_too_few_parts(self):
        line = "1|RAW"
        msg, seq = parse_addon_line(line)
        assert msg is None
