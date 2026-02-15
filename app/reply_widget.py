"""Reply input widget with live translation preview."""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QKeyEvent
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from app.translator import TranslatorService

logger = logging.getLogger(__name__)

DEBOUNCE_MS = 300


class ReplyWidget(QWidget):
    """Reply input with live translation preview.

    When visible (interactive mode), user types a message, sees a live
    translation preview, presses Enter to copy to clipboard.
    """

    reply_sent = pyqtSignal(str)  # emits translated text
    cancelled = pyqtSignal()

    def __init__(
        self,
        translator: TranslatorService | None = None,
        target_lang: str = "EN",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._translator = translator
        self._target_lang = target_lang
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(DEBOUNCE_MS)
        self._debounce_timer.timeout.connect(self._do_translate)

        self._setup_ui()
        self.hide()

    @property
    def target_lang(self) -> str:
        return self._target_lang

    @target_lang.setter
    def target_lang(self, lang: str) -> None:
        self._target_lang = lang

    def set_translator(self, translator: TranslatorService) -> None:
        self._translator = translator

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Preview label
        self._preview = QLabel("")
        self._preview.setStyleSheet(
            "color: #FFD200; font-size: 10px; padding: 2px; "
            "background: rgba(40, 40, 0, 150); border-radius: 2px;"
        )
        self._preview.setWordWrap(True)
        self._preview.setMinimumHeight(20)
        layout.addWidget(self._preview)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(4)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Type message... (Enter=send, Esc=cancel)")
        self._input.setStyleSheet(
            "QLineEdit { background: rgba(0,0,0,200); color: #FFFFFF; "
            "border: 1px solid #555; border-radius: 3px; padding: 4px; "
            "font-size: 11px; }"
        )
        self._input.setFont(QFont("Consolas", 10))
        self._input.textChanged.connect(self._on_text_changed)
        self._input.returnPressed.connect(self._on_enter)
        input_row.addWidget(self._input)

        # Target language label
        self._lang_label = QLabel(self._target_lang)
        self._lang_label.setStyleSheet(
            "color: #999; font-size: 10px; padding: 2px;"
        )
        input_row.addWidget(self._lang_label)

        layout.addLayout(input_row)

    def activate(self) -> None:
        """Show and focus the reply widget."""
        self._input.clear()
        self._preview.setText("")
        self._lang_label.setText(self._target_lang)
        self.show()
        self._input.setFocus()

    def deactivate(self) -> None:
        """Hide the reply widget."""
        self._input.clear()
        self._preview.setText("")
        self.hide()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.deactivate()
            self.cancelled.emit()
        else:
            super().keyPressEvent(event)

    def _on_text_changed(self, text: str) -> None:
        if text.strip():
            self._debounce_timer.start()
        else:
            self._preview.setText("")

    def _do_translate(self) -> None:
        text = self._input.text().strip()
        if not text or not self._translator:
            return

        result = self._translator.translate(text, target_lang=self._target_lang)
        if result.success:
            self._preview.setText(f"→ {result.translated}")
        else:
            self._preview.setText("(translation failed)")

    def _on_enter(self) -> None:
        text = self._input.text().strip()
        if not text:
            return

        # Get translated text from preview, or translate now
        if self._translator:
            result = self._translator.translate(text, target_lang=self._target_lang)
            translated = result.translated if result.success else text
        else:
            translated = text

        # Copy to clipboard
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(translated)

        self.reply_sent.emit(translated)
        self.deactivate()
