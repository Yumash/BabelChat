"""Translation pipeline: watcher -> parser -> detector -> cache -> translator -> output."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from lingua import Language

from app.cache import TranslationCache
from app.detector import ChatLanguageDetector
from app.parser import Channel, ChatMessage, parse_line
from app.text_utils import (
    clean_message_text,
    is_empty_or_whitespace,
    restore_tokens,
    strip_for_translation,
)
from app.translator import TranslationResult, TranslatorService
from app.watcher import ChatLogWatcher

logger = logging.getLogger(__name__)

# Lingua Language -> DeepL language code mapping
_LINGUA_TO_DEEPL: dict[Language, str] = {
    Language.ENGLISH: "EN",
    Language.RUSSIAN: "RU",
    Language.GERMAN: "DE",
    Language.FRENCH: "FR",
    Language.SPANISH: "ES",
    Language.ITALIAN: "IT",
    Language.PORTUGUESE: "PT",
    Language.POLISH: "PL",
    Language.DUTCH: "NL",
    Language.SWEDISH: "SV",
    Language.DANISH: "DA",
    Language.FINNISH: "FI",
    Language.CZECH: "CS",
    Language.ROMANIAN: "RO",
    Language.HUNGARIAN: "HU",
    Language.BULGARIAN: "BG",
    Language.GREEK: "EL",
    Language.TURKISH: "TR",
    Language.UKRAINIAN: "UK",
    Language.JAPANESE: "JA",
    Language.KOREAN: "KO",
    Language.CHINESE: "ZH",
    Language.ESTONIAN: "ET",
    Language.LATVIAN: "LV",
    Language.LITHUANIAN: "LT",
    Language.SLOVENE: "SL",
    Language.SLOVAK: "SK",
    Language.INDONESIAN: "ID",
    Language.BOKMAL: "NB",
}


@dataclass
class TranslatedMessage:
    """A chat message with its translation."""

    original: ChatMessage
    translation: TranslationResult | None
    source_lang: str = ""


@dataclass
class PipelineConfig:
    """Pipeline configuration."""

    chatlog_path: Path = Path("WoWChatLog.txt")
    deepl_api_key: str = ""
    target_lang: str = "EN"
    own_language: Language = Language.ENGLISH
    own_character: str = ""
    enabled_channels: set[Channel] = field(default_factory=lambda: {
        Channel.SAY, Channel.YELL, Channel.PARTY, Channel.PARTY_LEADER,
        Channel.RAID, Channel.RAID_LEADER, Channel.GUILD,
        Channel.WHISPER_FROM, Channel.WHISPER_TO,
        Channel.INSTANCE, Channel.INSTANCE_LEADER,
    })
    translation_enabled: bool = True
    db_path: str = "translations.db"


class TranslationPipeline:
    """Orchestrates the full translation pipeline.

    Flow: file watcher -> line parser -> language detector -> cache lookup
    -> API translation -> output callback.
    """

    def __init__(
        self,
        config: PipelineConfig,
        on_message: Callable[[TranslatedMessage], None],
    ) -> None:
        self._config = config
        self._on_message = on_message
        self._lock = threading.Lock()

        self._cache = TranslationCache(db_path=config.db_path)
        self._detector = ChatLanguageDetector(own_language=config.own_language)
        self._translator = TranslatorService(api_key=config.deepl_api_key)
        self._watcher = ChatLogWatcher(config.chatlog_path, self._on_new_line)

    @property
    def translation_enabled(self) -> bool:
        return self._config.translation_enabled

    @translation_enabled.setter
    def translation_enabled(self, value: bool) -> None:
        self._config.translation_enabled = value
        logger.info("Translation %s", "enabled" if value else "disabled")

    def start(self) -> None:
        """Start watching the chat log and translating."""
        self._watcher.start()
        logger.info("Pipeline started")

    def stop(self) -> None:
        """Stop the pipeline."""
        self._watcher.stop()
        self._cache.close()
        logger.info("Pipeline stopped")

    def _on_new_line(self, line: str) -> None:
        """Process a new line from the chat log."""
        msg = parse_line(line)
        if msg is None:
            return

        # Filter by channel
        if msg.channel not in self._config.enabled_channels:
            return

        # Filter own messages
        if self._config.own_character and msg.author == self._config.own_character:
            return

        # Translation disabled — still emit message without translation
        if not self._config.translation_enabled:
            self._on_message(TranslatedMessage(original=msg, translation=None))
            return

        # Clean and validate text
        cleaned_text = clean_message_text(msg.text)
        if is_empty_or_whitespace(cleaned_text):
            return

        # Detect language
        detected = self._detector.detect(cleaned_text)
        if detected is None:
            # Own language or undetectable — emit without translation
            self._on_message(TranslatedMessage(original=msg, translation=None))
            return

        source_lang = _LINGUA_TO_DEEPL.get(detected, "")
        if not source_lang:
            self._on_message(TranslatedMessage(original=msg, translation=None))
            return

        target_lang = self._config.target_lang

        # Check cache
        cached = self._cache.get(cleaned_text, source_lang, target_lang)
        if cached is not None:
            result = TranslationResult(
                original=cleaned_text, translated=cached,
                source_lang=source_lang, target_lang=target_lang,
                success=True,
            )
            self._on_message(TranslatedMessage(
                original=msg, translation=result, source_lang=source_lang,
            ))
            return

        # Strip URLs, WoW markers before translation
        text_to_translate, replacements = strip_for_translation(cleaned_text)

        # Translate via API (this blocks — called from watchdog thread)
        result = self._translator.translate(
            text_to_translate, target_lang=target_lang, source_lang=source_lang,
        )

        # Restore preserved tokens in translated text
        if result.success and replacements:
            restored = restore_tokens(result.translated, replacements)
            result = TranslationResult(
                original=cleaned_text, translated=restored,
                source_lang=result.source_lang, target_lang=result.target_lang,
                success=True,
            )

        # Cache successful translations
        if result.success:
            self._cache.put(cleaned_text, source_lang, target_lang, result.translated)

        self._on_message(TranslatedMessage(
            original=msg, translation=result, source_lang=source_lang,
        ))
