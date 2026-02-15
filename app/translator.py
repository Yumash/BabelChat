"""Translation service with DeepL API."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import deepl

logger = logging.getLogger(__name__)

# DeepL language codes
DEEPL_LANGUAGES = {
    "BG", "CS", "DA", "DE", "EL", "EN", "ES", "ET", "FI", "FR",
    "HU", "ID", "IT", "JA", "KO", "LT", "LV", "NB", "NL", "PL",
    "PT", "RO", "RU", "SK", "SL", "SV", "TR", "UK", "ZH",
}

# EN target requires EN-US or EN-GB
_EN_TARGET_DEFAULT = "EN-US"
_PT_TARGET_DEFAULT = "PT-BR"


@dataclass(frozen=True, slots=True)
class TranslationResult:
    """Result of a translation attempt."""

    original: str
    translated: str
    source_lang: str
    target_lang: str
    success: bool
    error: str | None = None


class TranslatorService:
    """Bidirectional translation via DeepL API.

    Usage:
        translator = TranslatorService(api_key="your-key")
        result = translator.translate("Привет", target_lang="EN")
    """

    def __init__(
        self,
        api_key: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        self._client = deepl.Translator(api_key)
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: str | None = None,
    ) -> TranslationResult:
        """Translate text to target language.

        Args:
            text: Text to translate.
            target_lang: Target language code (e.g. "EN", "RU", "DE").
            source_lang: Source language code. None for auto-detect.

        Returns:
            TranslationResult with translated text or original on error.
        """
        if not text.strip():
            return TranslationResult(
                original=text, translated=text,
                source_lang=source_lang or "", target_lang=target_lang,
                success=True,
            )

        # DeepL requires EN-US/EN-GB for target, not just EN
        effective_target = self._normalize_target_lang(target_lang)

        for attempt in range(self._max_retries):
            try:
                result = self._client.translate_text(
                    text,
                    target_lang=effective_target,
                    source_lang=source_lang,
                )
                return TranslationResult(
                    original=text,
                    translated=result.text,
                    source_lang=result.detected_source_lang,
                    target_lang=target_lang,
                    success=True,
                )
            except deepl.QuotaExceededException:
                logger.error("DeepL quota exceeded")
                return TranslationResult(
                    original=text, translated=text,
                    source_lang=source_lang or "", target_lang=target_lang,
                    success=False, error="quota_exceeded",
                )
            except deepl.DeepLException as e:
                logger.warning(
                    "DeepL error (attempt %d/%d): %s",
                    attempt + 1, self._max_retries, e,
                )
                if attempt < self._max_retries - 1:
                    delay = self._retry_delay * (2 ** attempt)
                    time.sleep(delay)

        return TranslationResult(
            original=text, translated=text,
            source_lang=source_lang or "", target_lang=target_lang,
            success=False, error="max_retries_exceeded",
        )

    def get_usage(self) -> deepl.Usage:
        """Get current API usage stats."""
        return self._client.get_usage()

    @staticmethod
    def _normalize_target_lang(lang: str) -> str:
        """Normalize target language code for DeepL API."""
        upper = lang.upper()
        if upper == "EN":
            return _EN_TARGET_DEFAULT
        if upper == "PT":
            return _PT_TARGET_DEFAULT
        return upper
