"""Tests for WoW Chat Log parser."""


from app.parser import Channel, parse_line


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
