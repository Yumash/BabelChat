"""Language selector dropdown for reply target language."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox, QWidget

# Languages available for reply translation
REPLY_LANGUAGES: list[tuple[str, str]] = [
    ("Auto", "Auto"),
    ("EN", "English"),
    ("RU", "Russian"),
    ("DE", "German"),
    ("FR", "French"),
    ("ES", "Spanish"),
    ("PT", "Portuguese"),
    ("IT", "Italian"),
    ("KO", "Korean"),
    ("ZH", "Chinese"),
    ("JA", "Japanese"),
    ("PL", "Polish"),
    ("UK", "Ukrainian"),
    ("TR", "Turkish"),
]


class LangSelector(QComboBox):
    """Dropdown for selecting reply target language.

    Supports "Auto" mode which uses the language of the last received message.
    Remembers last selected language per channel.
    """

    language_changed = pyqtSignal(str)  # emits language code

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._channel_langs: dict[str, str] = {}
        self._last_detected_lang: str = "EN"

        for code, name in REPLY_LANGUAGES:
            self.addItem(f"{name}" if code == "Auto" else f"{name} ({code})", code)

        self.setFixedWidth(120)
        self.setFixedHeight(22)
        self.setStyleSheet(
            "QComboBox { background: rgba(40,40,40,200); color: #FFFFFF; "
            "border: 1px solid #555; border-radius: 3px; padding: 2px 4px; "
            "font-size: 10px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background: rgba(30,30,30,240); "
            "color: #FFFFFF; selection-background-color: rgba(80,80,80,200); }"
        )

        self.currentIndexChanged.connect(self._on_changed)

    def _on_changed(self, _index: int) -> None:
        lang = self.effective_language
        self.language_changed.emit(lang)

    @property
    def effective_language(self) -> str:
        """Return the effective language (resolves Auto)."""
        code = self.currentData()
        if code == "Auto":
            return self._last_detected_lang
        return code

    def set_auto_language(self, lang: str) -> None:
        """Set the auto-detected language (from last message source)."""
        self._last_detected_lang = lang
        if self.currentData() == "Auto":
            self.language_changed.emit(lang)

    def remember_for_channel(self, channel: str, lang: str) -> None:
        """Remember language selection for a channel."""
        self._channel_langs[channel] = lang

    def restore_for_channel(self, channel: str) -> None:
        """Restore language selection for a channel."""
        lang = self._channel_langs.get(channel)
        if lang:
            idx = self.findData(lang)
            if idx >= 0:
                self.setCurrentIndex(idx)
