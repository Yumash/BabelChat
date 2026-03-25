"""Translation pipeline: watcher -> parser -> detector -> cache -> translator -> output."""

from __future__ import annotations

import itertools
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from lingua import Language

from app.cache import TranslationCache
from app.dedup import DeduplicationBuffer
from app.detector import ChatLanguageDetector
from app.glossary import expand_wow_terms
from app.parser import Channel, ChatMessage, parse_line
from app.phrasebook import lookup as phrasebook_lookup
from app.phrasebook import lookup_abbreviation as phrasebook_abbrev
from app.slang import expand_slang
from app.text_utils import (
    clean_message_text,
    restore_tokens,
    strip_for_translation,
)
from app.translator import TranslationResult, TranslatorService
from app.watcher import ChatLogWatcher

# Memory reader is optional — requires pymem and admin privileges
try:
    from app.memory_reader import MemoryChatWatcher
    HAS_MEMORY_READER = True
except ImportError:
    HAS_MEMORY_READER = False

logger = logging.getLogger(__name__)

# Max characters to show in log preview messages
_LOG_PREVIEW = 60

# Context string sent to DeepL for domain-aware translation
_DEEPL_CONTEXT = "World of Warcraft multiplayer game raid group chat"

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
    msg_id: int = 0       # unique ID for streaming updates
    is_update: bool = False  # True when this replaces a previous msg_id


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
    skip_own_messages: bool = True
    translation_enabled: bool = True
    db_path: str = "translations.db"
    use_memory_reader: bool = True  # Reads addon buffer from WoW process memory


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

        self._cache = TranslationCache(db_path=config.db_path)
        self._cache.cleanup()  # remove expired entries on startup
        self._detector = ChatLanguageDetector(own_language=config.own_language)
        self._translator = TranslatorService(api_key=config.deepl_api_key)
        self._watcher = ChatLogWatcher(config.chatlog_path, self._on_new_line)

        # Deduplication: track recent (author, text) to avoid double-delivery
        # when both memory reader and file watcher deliver the same message
        self._dedup = DeduplicationBuffer()

        # Streaming: monotonic message ID for progressive rendering
        # itertools.count is thread-safe in CPython (atomic C-level next())
        self._msg_id_counter = itertools.count(1)

        # Memory reader (optional, real-time delivery)
        self._memory_watcher = None
        if config.use_memory_reader and HAS_MEMORY_READER:
            self._memory_watcher = MemoryChatWatcher(self._on_new_line)
            logger.info("Memory reader available, will try real-time mode")

    @property
    def translation_enabled(self) -> bool:
        return self._config.translation_enabled

    @translation_enabled.setter
    def translation_enabled(self, value: bool) -> None:
        self._config.translation_enabled = value
        logger.info("Translation %s", "enabled" if value else "disabled")

    def update_config(self, config: PipelineConfig) -> None:
        """Hot-update pipeline settings without restart.

        Updates detector language, target language, enabled channels, etc.
        Called from the main thread when user saves settings.
        """
        old_own = self._config.own_language
        old_target = self._config.target_lang
        self._config = config
        self._detector.own_language = config.own_language
        if old_own != config.own_language:
            logger.info("Own language changed: %s -> %s", old_own, config.own_language)
        if old_target != config.target_lang:
            logger.info("Target language changed: %s -> %s", old_target, config.target_lang)

    def load_history(self, max_lines: int = 50) -> list[TranslatedMessage]:
        """Read last N lines from the log and parse them (no translation)."""
        lines = self._watcher.read_tail(max_lines)
        messages = []
        for line in lines:
            msg = parse_line(line)
            if msg is None:
                continue
            if msg.channel not in self._config.enabled_channels:
                continue
            messages.append(TranslatedMessage(original=msg, translation=None))
        return messages

    def start(self) -> None:
        """Start watching the chat log and translating.

        Tries memory reader first for real-time delivery.
        File watcher only starts as fallback when memory reader is unavailable.
        Running both causes duplicate messages (WoW buffers chatlog writes
        for minutes, then flushes a huge batch that bypasses dedup TTL).
        """
        # Try memory reader first (real-time, preferred)
        if self._memory_watcher:
            try:
                self._memory_watcher.start()
                logger.info("Pipeline started (memory reader only)")
                return
            except (RuntimeError, OSError) as e:
                logger.warning("Memory reader failed to start: %s", e)

        # Fallback: file watcher only
        self._watcher.start()
        logger.info("Pipeline started (file watcher only)")

    def stop(self) -> None:
        """Stop the pipeline."""
        if self._memory_watcher:
            self._memory_watcher.stop()
        self._watcher.stop()  # safe even if not started
        self._cache.close()
        logger.info("Pipeline stopped")

    def _on_new_line(
        self, line: str, *,
        dict_translated: bool = False,
        **_kwargs: object,
    ) -> None:
        """Process a new line from the chat log or memory reader.

        Args:
            line: WoW chat log format line.
            dict_translated: If True, the addon's dictionary already translated
                this message inline in chat.
        """
        logger.debug("New line: %s", line[:120])
        msg = parse_line(line)
        if msg is None:
            logger.info("Parse returned None for: %s", line[:150])
            return

        logger.info(
            "Parsed: [%s] %s: %s (dict=%s)",
            msg.channel.value, msg.author, msg.text[:_LOG_PREVIEW], dict_translated,
        )

        # Snapshot config for consistent reads within this method.
        # Reference assignment is atomic under CPython's GIL, so this is safe
        # even when update_config() replaces self._config from another thread.
        cfg = self._config

        # Deduplicate: both memory reader and file watcher may deliver same message
        if self._dedup.is_duplicate((msg.author, msg.text)):
            logger.debug("Duplicate message from %s, skipping", msg.author)
            return

        # Filter by channel
        if msg.channel not in cfg.enabled_channels:
            logger.debug("Channel %s not enabled", msg.channel)
            return

        # NPC filter: NPC names contain spaces (e.g. "High King Anduin"),
        # player names never do. Only applies to Say/Yell channels.
        if msg.channel in (Channel.SAY, Channel.YELL) and " " in msg.author:
            logger.debug("NPC message filtered: %s", msg.author[:40])
            return

        # Own messages — show in overlay but skip translation when configured
        own_char = cfg.own_character
        if not own_char and self._memory_watcher:
            own_char = self._memory_watcher.player_name
        if (
            cfg.skip_own_messages
            and own_char
            and msg.author == own_char
        ):
            logger.info("Skip own message (no translate): %s", msg.text[:_LOG_PREVIEW])
            self._on_message(TranslatedMessage(original=msg, translation=None))
            return

        # Translation disabled — still emit message without translation
        if not cfg.translation_enabled:
            self._on_message(TranslatedMessage(original=msg, translation=None))
            return

        # Dictionary-translated by addon — ignore addon dict, use DeepL instead.
        # Addon dict adds inline translations like "speed(Скорость)" which are
        # redundant when companion app does full DeepL translation.
        if dict_translated:
            logger.info("Dict message ignored, using DeepL: %s", msg.text[:_LOG_PREVIEW])

        # Clean and validate text
        cleaned_text = clean_message_text(msg.text)
        if not cleaned_text.strip():
            return

        target_lang = cfg.target_lang

        # Check abbreviations before language detection (catches short gg/ty/bb
        # that would fail MIN_TEXT_LENGTH in the detector)
        abbrev_hit = phrasebook_abbrev(cleaned_text, target_lang)
        if abbrev_hit is not None:
            result = TranslationResult(
                original=cleaned_text, translated=abbrev_hit,
                source_lang="", target_lang=target_lang,
                success=True,
            )
            self._on_message(TranslatedMessage(
                original=msg, translation=result,
            ))
            return

        # Detect language
        detected = self._detector.detect(cleaned_text)
        if detected is None:
            # Own language or skip-phrase — emit without translation
            logger.info("Skip (own lang / skip-phrase): %r", cleaned_text[:_LOG_PREVIEW])
            self._on_message(TranslatedMessage(original=msg, translation=None))
            return

        # UNKNOWN = lingua couldn't determine, let DeepL auto-detect
        if detected == ChatLanguageDetector.UNKNOWN:
            source_lang = ""
            logger.info("Translating (auto-detect)→%s: %r", target_lang, cleaned_text[:_LOG_PREVIEW])
        else:
            source_lang = _LINGUA_TO_DEEPL.get(detected, "")
            if not source_lang:
                # Lingua detected a language not in DeepL map — let DeepL
                # auto-detect instead of skipping.
                logger.info(
                    "Translating (auto-detect, lingua=%s)→%s: %r",
                    detected, target_lang, cleaned_text[:_LOG_PREVIEW],
                )
            else:
                logger.info(
                    "Translating %s→%s: %r",
                    source_lang, target_lang, cleaned_text[:_LOG_PREVIEW],
                )

        # Check phrasebook (instant, no API call)
        phrasebook_hit = phrasebook_lookup(cleaned_text, source_lang, target_lang)
        if phrasebook_hit is not None:
            result = TranslationResult(
                original=cleaned_text, translated=phrasebook_hit,
                source_lang=source_lang, target_lang=target_lang,
                success=True,
            )
            self._on_message(TranslatedMessage(
                original=msg, translation=result, source_lang=source_lang,
            ))
            return

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

        # Expand gaming slang to plain English so DeepL can understand
        expanded = expand_slang(text_to_translate)
        if expanded != text_to_translate:
            logger.info("Slang expanded: %r → %r", text_to_translate[:_LOG_PREVIEW], expanded[:_LOG_PREVIEW])
            text_to_translate = expanded

        # Expand WoW-specific terms (context-gated: 2+ gaming terms required)
        wow_expanded = expand_wow_terms(text_to_translate)
        if wow_expanded != text_to_translate:
            logger.info("WoW terms expanded: %r → %r", text_to_translate[:_LOG_PREVIEW], wow_expanded[:_LOG_PREVIEW])
            text_to_translate = wow_expanded

        # --- STREAMING: emit original immediately, then update with translation ---
        msg_id = next(self._msg_id_counter)
        self._on_message(TranslatedMessage(
            original=msg, translation=None,
            source_lang=source_lang, msg_id=msg_id,
        ))

        # Translate via API (this blocks — called from watchdog thread)
        src_display = source_lang or "auto"
        logger.info("Calling DeepL: %s→%s %r", src_display, target_lang, text_to_translate[:_LOG_PREVIEW])
        result = self._translator.translate(
            text_to_translate, target_lang=target_lang,
            source_lang=source_lang or None,
            context=_DEEPL_CONTEXT,
        )
        translated_preview = result.translated[:_LOG_PREVIEW] if result.translated else ""
        logger.info("DeepL result: success=%s, translated=%r", result.success, translated_preview)

        # If DeepL auto-detected own language, skip (e.g. "zerg" detected as RU)
        own_deepl = _LINGUA_TO_DEEPL.get(cfg.own_language, "")
        if result.success and not source_lang and result.source_lang == own_deepl:
            logger.info("DeepL detected own lang (%s), skipping: %r", own_deepl, cleaned_text[:_LOG_PREVIEW])
            return  # original already emitted above

        # Restore preserved tokens in translated text
        if result.success and replacements:
            restored = restore_tokens(result.translated, replacements)
            result = TranslationResult(
                original=cleaned_text, translated=restored,
                source_lang=result.source_lang, target_lang=result.target_lang,
                success=True,
            )

        # Cache successful translations (use DeepL-detected source if auto)
        if result.success:
            cache_src = source_lang or result.source_lang
            self._cache.put(cleaned_text, cache_src, target_lang, result.translated)

        # --- STREAMING: emit translation update ---
        self._on_message(TranslatedMessage(
            original=msg, translation=result, source_lang=source_lang,
            msg_id=msg_id, is_update=True,
        ))
