"""Language detection for chat messages using lingua-py."""

from __future__ import annotations

import logging

from lingua import Language, LanguageDetectorBuilder

logger = logging.getLogger(__name__)

# Short gaming phrases that shouldn't trigger detection
# Gaming phrases that shouldn't trigger language detection.
# NOTE: abbreviations with translations (gg, ty, brb, afk, etc.) are handled
# by the phrasebook module — they are NOT listed here so they can reach the
# phrasebook lookup in the pipeline.
_SKIP_PHRASES = frozenset({
    "kk", "ok", "lol", "lmao", "rip", "ez",
    "pst", "+", "++", "+++",
    "1", "2", "3", "123", "pull", "cc", "aoe", "dps", "heal", "tank",
    "res", "rez", "buff", "nerf", "proc", "crit", "dodge", "miss",
})

MIN_TEXT_LENGTH = 3

# Short text uses a more lenient detection threshold
_SHORT_TEXT_THRESHOLD = 20

# Cyrillic fallback: if lingua can't decide but text is mostly Cyrillic,
# assume Russian (the dominant Cyrillic language in WoW).
_CYRILLIC_THRESHOLD = 0.5

# Cyrillic sibling languages: lingua often confuses short Russian text
# with Bulgarian or Ukrainian. On RU servers 99%+ Cyrillic is Russian.
_CYRILLIC_SIBLING_LANGUAGES = frozenset({Language.BULGARIAN, Language.UKRAINIAN})


def _cyrillic_ratio(text: str) -> float:
    """Return fraction of alphabetic characters that are Cyrillic."""
    alpha_count = 0
    cyrillic_count = 0
    for ch in text:
        if ch.isalpha():
            alpha_count += 1
            if "\u0400" <= ch <= "\u04ff":
                cyrillic_count += 1
    return cyrillic_count / alpha_count if alpha_count > 0 else 0.0


class ChatLanguageDetector:
    """Detects language of chat messages, skipping gaming jargon."""

    # Sentinel: lingua couldn't determine the language but text is not
    # a skip-phrase and is long enough — pipeline should try DeepL anyway.
    UNKNOWN = "UNKNOWN"

    def __init__(self, own_language: Language = Language.ENGLISH) -> None:
        self._own_language = own_language
        self._detector = (
            LanguageDetectorBuilder.from_all_languages()
            .with_minimum_relative_distance(0.25)
            .build()
        )
        # Lenient detector for short text — lower confidence threshold
        self._detector_lenient = (
            LanguageDetectorBuilder.from_all_languages()
            .with_minimum_relative_distance(0.1)
            .build()
        )

    @property
    def own_language(self) -> Language:
        return self._own_language

    @own_language.setter
    def own_language(self, lang: Language) -> None:
        self._own_language = lang

    def detect(self, text: str) -> Language | str | None:
        """Detect language of text.

        Returns:
        - Language enum if detected with confidence
        - UNKNOWN sentinel if lingua can't determine but text should be tried
        - None if text is too short, a skip-phrase, or matches own_language
        """
        cleaned = text.strip().lower()

        if len(cleaned) < MIN_TEXT_LENGTH:
            return None

        if cleaned in _SKIP_PHRASES:
            return None

        # Use lenient detector for short text
        if len(cleaned) <= _SHORT_TEXT_THRESHOLD:
            detected = self._detector_lenient.detect_language_of(text)
        else:
            detected = self._detector.detect_language_of(text)

        # Cyrillic fallback: if lingua can't decide but text is predominantly
        # Cyrillic, assume Russian. This helps with short slang like "мда",
        # "щяс" that lingua fails to classify.
        if detected is None:
            ratio = _cyrillic_ratio(text)
            if ratio >= _CYRILLIC_THRESHOLD:
                detected = Language.RUSSIAN
                logger.debug(
                    "Cyrillic fallback: %.0f%% → RUSSIAN for %r",
                    ratio * 100, text[:40],
                )

        if detected is None:
            # Lingua couldn't determine — let DeepL try
            logger.debug("Undetectable, will try DeepL: %r", text[:40])
            return self.UNKNOWN

        if detected == self._own_language:
            return None

        # Short Cyrillic text often misdetected as BG/UK — treat as own lang
        if (
            detected in _CYRILLIC_SIBLING_LANGUAGES
            and self._own_language == Language.RUSSIAN
            and _cyrillic_ratio(text) >= _CYRILLIC_THRESHOLD
        ):
            logger.debug(
                "Cyrillic sibling %s -> treating as RU: %r",
                detected, text[:40],
            )
            return None

        return detected

    def needs_translation(self, text: str) -> bool:
        """Check if text needs translation (detected as foreign language)."""
        return self.detect(text) is not None
