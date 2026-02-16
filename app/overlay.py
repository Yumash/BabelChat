"""Smart overlay chat window styled as WoW native chat."""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import json
import logging
from pathlib import Path

from PyQt6.QtCore import QPoint, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.parser import Channel
from app.pipeline import TranslatedMessage

logger = logging.getLogger(__name__)

# Win32 constants
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

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
}

TRANSLATION_COLOR = "#FFD200"  # Gold for translated text

SETTINGS_FILE = "overlay_settings.json"


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

        filters = ["All", "Party", "Raid", "Guild", "Say", "Whisper"]
        for name in filters:
            btn = QPushButton(name)
            btn.setFixedHeight(20)
            btn.setCheckable(True)
            btn.setChecked(name == "All")
            btn.clicked.connect(lambda checked, n=name: self._on_click(n))
            btn.setStyleSheet(self._button_style(name == "All"))
            layout.addWidget(btn)
            self._buttons[name] = btn

        layout.addStretch()

    def _on_click(self, name: str) -> None:
        self._active = name
        for btn_name, btn in self._buttons.items():
            btn.setChecked(btn_name == name)
            btn.setStyleSheet(self._button_style(btn_name == name))
        self.filter_changed.emit(name)

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


# Mapping from filter tab name to channels
_FILTER_CHANNELS: dict[str, set[Channel]] = {
    "All": set(Channel),
    "Party": {Channel.PARTY, Channel.PARTY_LEADER},
    "Raid": {Channel.RAID, Channel.RAID_LEADER, Channel.RAID_WARNING},
    "Guild": {Channel.GUILD, Channel.OFFICER},
    "Say": {Channel.SAY, Channel.YELL},
    "Whisper": {Channel.WHISPER_FROM, Channel.WHISPER_TO},
}


class ChatOverlay(QWidget):
    """WoW-styled smart overlay chat window.

    Features:
    - Click-through by default (passes clicks to WoW)
    - Hotkey toggles interactive mode
    - WoW-native styling with channel colors
    - Channel filter tabs
    - Auto-scroll with scrollback in interactive mode
    """

    message_received = pyqtSignal(object)  # TranslatedMessage
    settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._click_through = False
        self._active_filter = "All"
        self._translation_enabled = True
        self._drag_pos: QPoint | None = None
        self._bg_opacity = 180

        self._setup_window()
        self._setup_ui()
        self._load_settings()

        self.message_received.connect(self._on_message)

    def _setup_window(self) -> None:
        """Configure window flags for overlay behavior."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(350, 200)
        self.resize(450, 300)

    def _setup_ui(self) -> None:
        """Build the overlay UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Main container with WoW-dark background
        self._container = QWidget()
        self._container.setStyleSheet(
            "background: rgba(0, 0, 0, 180); border-radius: 4px;"
        )
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(4, 4, 4, 4)
        container_layout.setSpacing(2)

        # Title bar
        title_bar = QHBoxLayout()
        title_label = QLabel("WoWTranslator")
        title_label.setStyleSheet(
            "color: #FFD200; font-size: 11px; font-weight: bold; padding: 2px;"
        )
        title_bar.addWidget(title_label)
        title_bar.addStretch()

        # Translation toggle
        self._toggle_btn = QPushButton("TR: ON")
        self._toggle_btn.setFixedSize(50, 20)
        self._toggle_btn.clicked.connect(self._toggle_translation)
        self._toggle_btn.setStyleSheet(
            "QPushButton { background: rgba(0,100,0,200); color: #40FF40; "
            "border: 1px solid #40FF40; border-radius: 3px; font-size: 10px; }"
        )
        title_bar.addWidget(self._toggle_btn)

        # Mode indicator
        self._mode_label = QLabel("UNLOCKED")
        self._mode_label.setStyleSheet(
            "color: #40FF40; font-size: 9px; padding: 2px;"
        )
        title_bar.addWidget(self._mode_label)

        container_layout.addLayout(title_bar)

        # Toolbar (visible only in interactive/unlocked mode)
        self._toolbar = QWidget()
        tb_layout = QHBoxLayout(self._toolbar)
        tb_layout.setContentsMargins(2, 0, 2, 0)
        tb_layout.setSpacing(4)

        _TB_BTN = (
            "QPushButton { background: rgba(60,60,60,200); color: #ccc; "
            "border: 1px solid #555; border-radius: 3px; padding: 2px 8px; font-size: 10px; }"
            "QPushButton:hover { color: #FFD200; border-color: #FFD200; }"
        )

        settings_btn = QPushButton("\u2699 Settings")
        settings_btn.setFixedHeight(20)
        settings_btn.setStyleSheet(_TB_BTN)
        settings_btn.clicked.connect(self.settings_requested.emit)
        tb_layout.addWidget(settings_btn)

        opacity_label = QLabel("Opacity:")
        opacity_label.setStyleSheet("color: #999; font-size: 10px;")
        tb_layout.addWidget(opacity_label)

        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(30, 255)
        self._opacity_slider.setValue(self._bg_opacity)
        self._opacity_slider.setFixedWidth(80)
        self._opacity_slider.setFixedHeight(16)
        self._opacity_slider.setStyleSheet(
            "QSlider::groove:horizontal { height: 4px; background: #333; border-radius: 2px; }"
            "QSlider::handle:horizontal { background: #FFD200; width: 10px; height: 10px; "
            "margin: -3px 0; border-radius: 5px; }"
            "QSlider::sub-page:horizontal { background: #997d00; border-radius: 2px; }"
        )
        self._opacity_slider.valueChanged.connect(self._on_opacity_changed)
        tb_layout.addWidget(self._opacity_slider)

        lock_btn = QPushButton("\U0001F512 Lock")
        lock_btn.setFixedHeight(20)
        lock_btn.setStyleSheet(_TB_BTN)
        lock_btn.clicked.connect(self.toggle_interactive)
        tb_layout.addWidget(lock_btn)

        quit_btn = QPushButton("\u2716 Quit")
        quit_btn.setFixedHeight(20)
        quit_btn.setStyleSheet(
            "QPushButton { background: rgba(100,0,0,200); color: #FF4040; "
            "border: 1px solid #FF4040; border-radius: 3px; padding: 2px 8px; font-size: 10px; }"
            "QPushButton:hover { background: rgba(150,0,0,200); }"
        )
        quit_btn.clicked.connect(self.quit_requested.emit)
        tb_layout.addWidget(quit_btn)

        tb_layout.addStretch()
        self._toolbar.show()
        container_layout.addWidget(self._toolbar)

        # Channel filter tabs
        self._filter_bar = ChannelFilterBar()
        self._filter_bar.filter_changed.connect(self._on_filter_changed)
        container_layout.addWidget(self._filter_bar)

        # Chat message area
        self._chat_area = QTextEdit()
        self._chat_area.setReadOnly(True)
        self._chat_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._chat_area.setStyleSheet(
            "QTextEdit { background: transparent; border: none; color: #FFFFFF; }"
        )
        font = QFont("Consolas", 10)
        self._chat_area.setFont(font)
        container_layout.addWidget(self._chat_area)

        layout.addWidget(self._container)

    def showEvent(self, event: object) -> None:
        """Apply click-through after window is shown."""
        super().showEvent(event)  # type: ignore[arg-type]
        if self._click_through:
            self._set_click_through(True)

    def add_message(self, msg: TranslatedMessage) -> None:
        """Thread-safe way to add a message (emits signal)."""
        self.message_received.emit(msg)

    @pyqtSlot(object)
    def _on_message(self, msg: TranslatedMessage) -> None:
        """Handle a new translated message on the GUI thread."""
        channel = msg.original.channel

        # Filter check
        filter_channels = _FILTER_CHANNELS.get(self._active_filter, set(Channel))
        if channel not in filter_channels:
            return

        cursor = self._chat_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # Channel prefix
        color = CHANNEL_COLORS.get(channel, "#FFFFFF")
        prefix = CHANNEL_PREFIXES.get(channel, "")

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))

        cursor.insertText("\n")
        cursor.setCharFormat(fmt)
        cursor.insertText(f"{prefix} {msg.original.author}: ")

        # Message text
        cursor.insertText(msg.original.text)

        # Translation (if present and enabled)
        if (
            self._translation_enabled
            and msg.translation
            and msg.translation.success
            and msg.translation.translated != msg.original.text
        ):
                tr_fmt = QTextCharFormat()
                tr_fmt.setForeground(QColor(TRANSLATION_COLOR))
                cursor.setCharFormat(tr_fmt)
                cursor.insertText(f" → {msg.translation.translated}")

        # Auto-scroll to bottom
        self._chat_area.verticalScrollBar().setValue(
            self._chat_area.verticalScrollBar().maximum()
        )

    def _on_filter_changed(self, filter_name: str) -> None:
        self._active_filter = filter_name

    def _toggle_translation(self) -> None:
        self._translation_enabled = not self._translation_enabled
        if self._translation_enabled:
            self._toggle_btn.setText("TR: ON")
            self._toggle_btn.setStyleSheet(
                "QPushButton { background: rgba(0,100,0,200); color: #40FF40; "
                "border: 1px solid #40FF40; border-radius: 3px; font-size: 10px; }"
            )
        else:
            self._toggle_btn.setText("TR: OFF")
            self._toggle_btn.setStyleSheet(
                "QPushButton { background: rgba(100,0,0,200); color: #FF4040; "
                "border: 1px solid #FF4040; border-radius: 3px; font-size: 10px; }"
            )

    def _on_opacity_changed(self, value: int) -> None:
        self._bg_opacity = value
        self._container.setStyleSheet(
            f"background: rgba(0, 0, 0, {value}); border-radius: 4px;"
        )

    def toggle_interactive(self) -> None:
        """Toggle between click-through and interactive mode."""
        self._click_through = not self._click_through
        self._set_click_through(self._click_through)
        if self._click_through:
            self._mode_label.setText("LOCKED")
            self._mode_label.setStyleSheet("color: #666; font-size: 9px; padding: 2px;")
            self._toolbar.hide()
        else:
            self._mode_label.setText("UNLOCKED")
            self._mode_label.setStyleSheet("color: #40FF40; font-size: 9px; padding: 2px;")
            self._toolbar.show()

    def _set_click_through(self, enabled: bool) -> None:
        """Set or unset click-through mode using Win32 API."""
        try:
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if enabled:
                style |= WS_EX_TRANSPARENT | WS_EX_LAYERED
            else:
                style &= ~WS_EX_TRANSPARENT
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except Exception:
            logger.warning("Failed to set click-through mode", exc_info=True)

    # -- Drag support (in interactive mode) --

    def mousePressEvent(self, event: object) -> None:
        if (
            not self._click_through
            and hasattr(event, 'button')
            and event.button() == Qt.MouseButton.LeftButton  # type: ignore[union-attr]
        ):
            self._drag_pos = event.globalPosition().toPoint() - self.pos()  # type: ignore[union-attr]

    def mouseMoveEvent(self, event: object) -> None:
        if (
            self._drag_pos is not None
            and not self._click_through
            and hasattr(event, 'buttons')
            and event.buttons() & Qt.MouseButton.LeftButton  # type: ignore[union-attr]
        ):
            self.move(event.globalPosition().toPoint() - self._drag_pos)  # type: ignore[union-attr]

    def mouseReleaseEvent(self, event: object) -> None:
        self._drag_pos = None
        self._save_settings()

    # -- Settings persistence --

    def _save_settings(self) -> None:
        data = {
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height(),
            "opacity": self._bg_opacity,
        }
        import contextlib
        with contextlib.suppress(OSError):
            Path(SETTINGS_FILE).write_text(json.dumps(data), encoding="utf-8")

    def _load_settings(self) -> None:
        try:
            data = json.loads(Path(SETTINGS_FILE).read_text(encoding="utf-8"))
            self.move(data.get("x", 100), data.get("y", 100))
            self.resize(data.get("width", 450), data.get("height", 300))
            opacity = data.get("opacity", 180)
            self._bg_opacity = opacity
            self._opacity_slider.setValue(opacity)
            self._on_opacity_changed(opacity)
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            self.move(100, 100)
