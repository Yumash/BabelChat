"""Language detection for chat messages using lingua-py."""

from __future__ import annotations

import logging

from lingua import Language, LanguageDetectorBuilder

logger = logging.getLogger(__name__)

# Short gaming phrases that shouldn't trigger detection
_SKIP_PHRASES = frozenset({
    "gg", "wp", "gl", "hf", "kk", "ok", "ty", "np", "lol", "lmao",
    "brb", "afk", "oom", "lfg", "lfm", "inv", "rdy", "rip", "ez",
    "gj", "mb", "omw", "inc", "wts", "wtb", "pst", "+", "++", "+++",
    "1", "2", "3", "go", "pull", "cc", "aoe", "dps", "heal", "tank",
    "res", "rez", "buff", "nerf", "proc", "crit", "dodge", "miss",
})

MIN_TEXT_LENGTH = 3


class ChatLanguageDetector:
    """Detects language of chat messages, skipping gaming jargon."""

    def __init__(self, own_language: Language = Language.ENGLISH) -> None:
        self._own_language = own_language
        self._detector = (
            LanguageDetectorBuilder.from_all_languages()
            .with_minimum_relative_distance(0.25)
            .build()
        )

    @property
    def own_language(self) -> Language:
        return self._own_language

    @own_language.setter
    def own_language(self, lang: Language) -> None:
        self._own_language = lang

    def detect(self, text: str) -> Language | None:
        """Detect language of text.

        Returns None if:
        - text is too short
        - text is a known gaming phrase
        - confidence is too low
        - detected language matches own_language
        """
        cleaned = text.strip().lower()

        if len(cleaned) < MIN_TEXT_LENGTH:
            return None

        if cleaned in _SKIP_PHRASES:
            return None

        detected = self._detector.detect_language_of(text)
        if detected is None:
            return None

        if detected == self._own_language:
            return None

        return detected

    def needs_translation(self, text: str) -> bool:
        """Check if text needs translation (detected as foreign language)."""
        return self.detect(text) is not None
