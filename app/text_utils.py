"""Text utilities for handling WoW chat edge cases."""

from __future__ import annotations

import re

# WoW raid target markers: {rt1} through {rt8}, {star}, {circle}, {diamond}, {triangle},
# {moon}, {square}, {cross}, {skull}
_RE_WOW_MARKERS = re.compile(
    r"\{(?:rt[1-8]|star|circle|diamond|triangle|moon|square|cross|skull)\}",
    re.IGNORECASE,
)

# URLs
_RE_URL = re.compile(
    r"https?://[^\s<>\"]+|www\.[^\s<>\"]+",
    re.IGNORECASE,
)

# WoW item/spell links: |cFFFFFFFF|Hitem:12345|h[Item Name]|h|r
_RE_WOW_LINK = re.compile(
    r"\|c[0-9a-fA-F]{8}\|H[^|]+\|h\[[^\]]*\]\|h\|r"
)


def strip_for_translation(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Strip non-translatable tokens from text, returning cleaned text and replacements.

    Returns:
        (cleaned_text, replacements) where replacements is a list of (placeholder, original).
    """
    replacements: list[tuple[str, str]] = []
    counter = 0

    def replace_token(match: re.Match[str]) -> str:
        nonlocal counter
        placeholder = f"__WCT{counter}__"
        counter += 1
        replacements.append((placeholder, match.group(0)))
        return placeholder

    result = text
    # Order matters: WoW links first (they contain special chars), then URLs, then markers
    result = _RE_WOW_LINK.sub(replace_token, result)
    result = _RE_URL.sub(replace_token, result)
    result = _RE_WOW_MARKERS.sub(replace_token, result)

    return result, replacements


def restore_tokens(text: str, replacements: list[tuple[str, str]]) -> str:
    """Restore original tokens after translation."""
    result = text
    for placeholder, original in replacements:
        result = result.replace(placeholder, original)
    return result


def is_empty_or_whitespace(text: str) -> bool:
    """Check if text is empty or whitespace-only."""
    return not text or not text.strip()


def clean_message_text(text: str) -> str:
    """Clean message text of control characters but preserve emoji and unicode."""
    # Remove WoW color codes that leak into chat log
    cleaned = re.sub(r"\|c[0-9a-fA-F]{8}", "", text)
    cleaned = re.sub(r"\|r", "", cleaned)
    return cleaned.strip()
