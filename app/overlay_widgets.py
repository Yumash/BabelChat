"""Pieces of the overlay that stand on their own.

The resize grip, the channel filter bar and the worker that translates a
reply off the UI thread. None of them knows about the overlay; keeping them
here is what lets overlay.py be about the window rather than about the
parts it is assembled from.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QRunnable, Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from app.config import CHANNEL_TOGGLES, FILTER_TABS
from app.i18n import tr
from app.parser import Channel
from app.translator import TranslatorService

if TYPE_CHECKING:  # annotation only; importing it at runtime buys nothing
    from PyQt6.QtCore import QPoint


class _ResizeGrip(QLabel):
    """Draggable resize grip for bottom-right corner of overlay."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__("\u2921", parent)
        self._overlay = parent
        self._drag_pos: QPoint | None = None
        self.setFixedSize(20, 20)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("color: #555; font-size: 14px; background: transparent;")
        self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
        self.setToolTip(tr("overlay.resize_hint"))

    def mousePressEvent(self, event: object) -> None:
        if hasattr(event, "button") and event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: object) -> None:
        if self._drag_pos is None:
            return
        gpos = event.globalPosition().toPoint()
        dx = gpos.x() - self._drag_pos.x()
        dy = gpos.y() - self._drag_pos.y()
        geo = self._overlay.geometry()
        min_w = self._overlay.minimumWidth()
        min_h = self._overlay.minimumHeight()
        geo.setWidth(max(min_w, geo.width() + dx))
        geo.setHeight(max(min_h, geo.height() + dy))
        self._overlay.setGeometry(geo)
        self._drag_pos = gpos

    def mouseReleaseEvent(self, event: object) -> None:
        self._drag_pos = None
        if hasattr(self._overlay, "_save_overlay_state"):
            self._overlay._save_overlay_state()


# WoW channel colors
CHANNEL_COLORS: dict[Channel, str] = {
    Channel.SAY: "#FFFFFF",
    Channel.YELL: "#FF4040",
    Channel.PARTY: "#AAAAFF",
    Channel.PARTY_LEADER: "#AAAAFF",
    Channel.RAID: "#FF7F00",
    Channel.RAID_LEADER: "#FF7F00",
    Channel.RAID_WARNING: "#FF4809",
    Channel.GUILD: "#40FF40",
    Channel.OFFICER: "#40C040",
    Channel.WHISPER_FROM: "#FF80FF",
    Channel.WHISPER_TO: "#FF80FF",
    Channel.INSTANCE: "#FF7F00",
    Channel.INSTANCE_LEADER: "#FF7F00",
    Channel.TRADE: "#FFC0C0",
    Channel.GENERAL: "#FFC0C0",
    Channel.SERVICES: "#FFC0C0",
    Channel.LOOKING_FOR_GROUP: "#FFC0C0",
    # A player-made channel and an emote are not speech, and rendering either in
    # Say's white left them indistinguishable from it.
    Channel.CUSTOM: "#C0E0FF",
    Channel.EMOTE: "#FF7F00",
}

CHANNEL_PREFIXES: dict[Channel, str] = {
    Channel.SAY: "[Say]",
    Channel.YELL: "[Yell]",
    Channel.PARTY: "[P]",
    Channel.PARTY_LEADER: "[PL]",
    Channel.RAID: "[R]",
    Channel.RAID_LEADER: "[RL]",
    Channel.RAID_WARNING: "[RW]",
    Channel.GUILD: "[G]",
    Channel.OFFICER: "[O]",
    Channel.WHISPER_FROM: "[W From]",
    Channel.WHISPER_TO: "[W To]",
    Channel.INSTANCE: "[I]",
    Channel.INSTANCE_LEADER: "[IL]",
    Channel.TRADE: "[Trade]",
    Channel.GENERAL: "[Gen]",
    Channel.SERVICES: "[Svc]",
    Channel.LOOKING_FOR_GROUP: "[LFG]",
    Channel.CUSTOM: "[Ch]",
    Channel.EMOTE: "[Emote]",
}

TRANSLATION_COLOR = "#FFD200"  # Gold for translated text


class ChannelFilterBar(QWidget):
    """Tab-like filter bar for chat channels."""

    filter_changed = pyqtSignal(str)  # emits filter name

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._buttons: dict[str, QPushButton] = {}
        self._active = "All"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # From the shared declaration: the hand-written list here never grew
        # Custom or Emote, so a message from either had no tab of its own.
        for name, label_key in FILTER_TABS:
            btn = QPushButton(tr(label_key))
            btn.setFixedHeight(20)
            btn.setCheckable(True)
            btn.setChecked(name == "All")
            btn.clicked.connect(lambda checked, n=name: self._on_click(n))
            btn.setStyleSheet(self._button_style(name == "All"))
            layout.addWidget(btn)
            self._buttons[name] = btn

        layout.addStretch()

    def apply_language(self) -> None:
        """Relabel the tabs after the interface language changed.

        From the same shared declaration they were built from, so a tab added
        there is relabelled here without this method being touched.
        """
        for name, label_key in FILTER_TABS:
            button = self._buttons.get(name)
            if button is not None:
                button.setText(tr(label_key))

    def _on_click(self, name: str) -> None:
        self._active = name
        for btn_name, btn in self._buttons.items():
            btn.setChecked(btn_name == name)
            btn.setStyleSheet(self._button_style(btn_name == name))
        self.filter_changed.emit(name)

    def update_enabled_filters(self, enabled: set[str]) -> None:
        """Show/hide filter buttons based on enabled channel groups.

        Args:
            enabled: set of filter names like {"Party", "Instance"}.
                     "All" is always visible.
        """
        for name, btn in self._buttons.items():
            if name == "All":
                btn.show()
            else:
                btn.setVisible(name in enabled)
        # If active filter was hidden, reset to All
        if self._active not in enabled and self._active != "All":
            self._on_click("All")

    @staticmethod
    def _button_style(active: bool) -> str:
        if active:
            return (
                "QPushButton { background: rgba(80,80,80,200); color: #FFD200; "
                "border: 1px solid #FFD200; border-radius: 3px; padding: 2px 6px; "
                "font-size: 11px; }"
            )
        return (
            "QPushButton { background: rgba(40,40,40,150); color: #999; "
            "border: 1px solid #555; border-radius: 3px; padding: 2px 6px; "
            "font-size: 11px; }"
            "QPushButton:hover { color: #CCC; border-color: #888; }"
        )


# Filter tab -> the channels it shows, built from the one declaration the
# settings checkboxes also come from. Written by hand, it went stale twice.
_FILTER_CHANNELS: dict[str, set[Channel]] = {"All": set(Channel)}
for _toggle in CHANNEL_TOGGLES:
    _FILTER_CHANNELS.setdefault(_toggle.tab, set()).update(Channel[_name] for _name in _toggle.channels)


class _TranslateSignals(QWidget):
    """Signals for ReplyTranslateWorker (QRunnable can't have signals)."""

    finished = pyqtSignal(str, bool)  # (translated_text, success)


class ReplyTranslateWorker(QRunnable):
    """Runs a single translation in the thread pool."""

    def __init__(self, translator: TranslatorService, text: str, target_lang: str) -> None:
        super().__init__()
        self.signals = _TranslateSignals()
        self._translator = translator
        self._text = text
        self._target_lang = target_lang

    def run(self) -> None:
        result = self._translator.translate(self._text, target_lang=self._target_lang)
        self.signals.finished.emit(result.translated, result.success)
