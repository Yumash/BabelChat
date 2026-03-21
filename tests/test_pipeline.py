"""Integration tests for the translation pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from lingua import Language

from app.parser import Channel
from app.pipeline import PipelineConfig, TranslatedMessage, TranslationPipeline
from app.translator import TranslationResult


@pytest.fixture
def mock_translator():
    """Create a mock TranslatorService that returns predictable translations."""
    translator = MagicMock()

    def fake_translate(text, target_lang, source_lang=None, context=None):
        translations = {
            ("hello everyone", "RU"): "привет всем",
            ("pull in 5 seconds", "RU"): "пулл через 5 секунд",
            ("looking for more players", "RU"): "ищу ещё игроков",
        }
        key = (text.lower().strip(), target_lang)
        if key in translations:
            return TranslationResult(
                original=text, translated=translations[key],
                source_lang=source_lang or "EN", target_lang=target_lang,
                success=True,
            )
        return TranslationResult(
            original=text, translated=f"[translated]{text}",
            source_lang=source_lang or "EN", target_lang=target_lang,
            success=True,
        )

    translator.translate.side_effect = fake_translate
    return translator


@pytest.fixture
def pipeline_config(tmp_path):
    """Create a pipeline config with temp DB."""
    return PipelineConfig(
        chatlog_path=tmp_path / "WoWChatLog.txt",
        deepl_api_key="fake-key",
        target_lang="RU",
        own_language=Language.RUSSIAN,
        own_character="MyChar-MyServer",
        db_path=str(tmp_path / "test_cache.db"),
        use_memory_reader=False,
    )


def _make_log_line(channel: str, author: str, text: str) -> str:
    """Create a WoW chat log line."""
    return f"2/15 21:30:45.123  [{channel}] {author}: {text}"


class TestPipelinePhrasebook:
    """Test that phrasebook hits skip API calls."""

    def test_abbreviation_gg(self, pipeline_config, mock_translator):
        received: list[TranslatedMessage] = []

        with patch("app.pipeline.TranslatorService", return_value=mock_translator):
            pipeline = TranslationPipeline(pipeline_config, received.append)
            line = _make_log_line("Party", "Thrall-Sargeras", "gg")
            pipeline._on_new_line(line)

        assert len(received) == 1
        msg = received[0]
        assert msg.translation is not None
        assert msg.translation.success is True
        # Should NOT call DeepL for "gg"
        mock_translator.translate.assert_not_called()

    def test_abbreviation_ty(self, pipeline_config, mock_translator):
        received: list[TranslatedMessage] = []

        with patch("app.pipeline.TranslatorService", return_value=mock_translator):
            pipeline = TranslationPipeline(pipeline_config, received.append)
            line = _make_log_line("Raid", "Player-Server", "ty")
            pipeline._on_new_line(line)

        assert len(received) == 1
        assert received[0].translation is not None
        mock_translator.translate.assert_not_called()


class TestPipelineDeepL:
    """Test DeepL translation path."""

    def test_english_to_russian(self, pipeline_config, mock_translator):
        received: list[TranslatedMessage] = []

        with patch("app.pipeline.TranslatorService", return_value=mock_translator):
            pipeline = TranslationPipeline(pipeline_config, received.append)
            line = _make_log_line("Party", "Thrall-Sargeras", "Hello everyone")
            pipeline._on_new_line(line)

        # Streaming: 2 messages — original (no translation) + update (with translation)
        assert len(received) == 2
        assert received[0].translation is None  # original shown immediately
        assert received[0].is_update is False
        assert received[1].translation is not None  # translation update
        assert received[1].translation.success is True
        assert received[1].is_update is True
        assert received[0].msg_id == received[1].msg_id  # same message
        mock_translator.translate.assert_called_once()


class TestPipelineCacheHit:
    """Test that second identical message uses cache."""

    def test_cache_hit_skips_api(self, pipeline_config, mock_translator):
        received: list[TranslatedMessage] = []

        with patch("app.pipeline.TranslatorService", return_value=mock_translator):
            pipeline = TranslationPipeline(pipeline_config, received.append)

            # First call: API (streaming: 2 messages)
            line1 = _make_log_line("Party", "Thrall-Sargeras", "Pull in 5 seconds")
            pipeline._on_new_line(line1)
            assert mock_translator.translate.call_count == 1

            # Second call: different author, same text — cache hit (1 message, no streaming)
            line2 = _make_log_line("Party", "Jaina-Sargeras", "Pull in 5 seconds")
            pipeline._on_new_line(line2)

            # Cache hit skips API
            assert mock_translator.translate.call_count == 1
            # 2 from streaming (original+update) + 1 from cache hit = 3
            assert len(received) == 3
            assert received[2].translation is not None
            assert received[2].translation.success is True


class TestPipelineOwnMessage:
    """Test own-language message passthrough."""

    def test_own_message_no_translation(self, pipeline_config, mock_translator):
        """Own character messages pass through without translation."""
        received: list[TranslatedMessage] = []
        pipeline_config.own_character = "MyChar"

        with patch("app.pipeline.TranslatorService", return_value=mock_translator):
            pipeline = TranslationPipeline(pipeline_config, received.append)
            line = _make_log_line("Party", "MyChar-MyServer", "Привет всем")
            pipeline._on_new_line(line)

        assert len(received) == 1
        assert received[0].translation is None
        mock_translator.translate.assert_not_called()


class TestPipelineFiltering:
    """Test channel and message filtering."""

    def test_disabled_channel_filtered(self, pipeline_config, mock_translator):
        received: list[TranslatedMessage] = []
        pipeline_config.enabled_channels = {Channel.PARTY}

        with patch("app.pipeline.TranslatorService", return_value=mock_translator):
            pipeline = TranslationPipeline(pipeline_config, received.append)
            line = _make_log_line("Guild", "Player-Server", "hello")
            pipeline._on_new_line(line)

        assert len(received) == 0

    def test_dedup_filters_duplicate(self, pipeline_config, mock_translator):
        received: list[TranslatedMessage] = []

        with patch("app.pipeline.TranslatorService", return_value=mock_translator):
            pipeline = TranslationPipeline(pipeline_config, received.append)
            line = _make_log_line("Party", "Player-Server", "hello team")
            pipeline._on_new_line(line)
            pipeline._on_new_line(line)  # duplicate — filtered by dedup

        # Streaming: 2 messages (original + update), duplicate blocked
        assert len(received) == 2
        assert received[0].is_update is False
        assert received[1].is_update is True

    def test_translation_disabled_passthrough(self, pipeline_config, mock_translator):
        received: list[TranslatedMessage] = []
        pipeline_config.translation_enabled = False

        with patch("app.pipeline.TranslatorService", return_value=mock_translator):
            pipeline = TranslationPipeline(pipeline_config, received.append)
            line = _make_log_line("Party", "Player-Server", "hello team")
            pipeline._on_new_line(line)

        assert len(received) == 1
        assert received[0].translation is None
        mock_translator.translate.assert_not_called()
