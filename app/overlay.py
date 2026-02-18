"""Smart overlay chat window styled as WoW native chat."""

from __future__ import annotations

import logging
from collections.abc import Callable

from PyQt6.QtCore import QPoint, QRunnable, Qt, QThreadPool, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QCursor, QFont, QPainter, QPen, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizeGrip,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.config import AppConfig
from app.i18n import tr
from app.parser import Channel
from app.pipeline import TranslatedMessage
from app.translator import TranslatorService

logger = logging.getLogger(__name__)

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

        _filter_keys = ["All", "Party", "Raid", "Guild", "Say", "Whisper", "Instance"]
        _filter_tr = {
            "All": "overlay.filter.all",
            "Party": "overlay.filter.party",
            "Raid": "overlay.filter.raid",
            "Guild": "overlay.filter.guild",
            "Say": "overlay.filter.say",
            "Whisper": "overlay.filter.whisper",
            "Instance": "overlay.filter.instance",
        }
        for name in _filter_keys:
            btn = QPushButton(tr(_filter_tr[name]))
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


# Mapping from filter tab name to channels
_FILTER_CHANNELS: dict[str, set[Channel]] = {
    "All": set(Channel),
    "Party": {Channel.PARTY, Channel.PARTY_LEADER},
    "Raid": {Channel.RAID, Channel.RAID_LEADER, Channel.RAID_WARNING},
    "Guild": {Channel.GUILD, Channel.OFFICER},
    "Say": {Channel.SAY, Channel.YELL},
    "Whisper": {Channel.WHISPER_FROM, Channel.WHISPER_TO},
    "Instance": {Channel.INSTANCE, Channel.INSTANCE_LEADER},
}


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


class ChatOverlay(QWidget):
    """WoW-styled smart overlay chat window.

    Features:
    - Always interactive (draggable, resizable, clickable)
    - WoW-native styling with channel colors
    - Channel filter tabs
    - Auto-scroll with scrollback
    - Built-in mini-translator for outgoing messages
    """

    message_received = pyqtSignal(object)  # TranslatedMessage
    settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._active_filter = "All"
        self._translation_enabled = True
        self._drag_pos: QPoint | None = None
        self._bg_opacity = config.overlay_opacity
        self._resize_edge: str | None = None
        self._translator: TranslatorService | None = None
        self._target_lang = "EN"
        self._thread_pool = QThreadPool()
        self._messages: list[TranslatedMessage] = []
        self._minimized = False
        self._restored_size: tuple[int, int] | None = None

        self._setup_window()
        self._setup_ui()
        self.move(config.overlay_x, config.overlay_y)
        self.resize(config.overlay_width, config.overlay_height)
        self._opacity_slider.setValue(config.overlay_opacity)
        self._on_opacity_changed(config.overlay_opacity)

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
        # Outer margins create transparent grip area for resize
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)
        self.setMouseTracking(True)

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

        # WoW connection status
        self._wow_status = QLabel("WoW: ?")
        self._wow_status.setFixedHeight(20)
        self._wow_status.setStyleSheet(
            "color: #888; font-size: 9px; padding: 0 4px;"
        )
        title_bar.addWidget(self._wow_status)

        # Translation toggle
        self._toggle_btn = QPushButton("TR: ON")
        self._toggle_btn.setFixedSize(50, 20)
        self._toggle_btn.clicked.connect(self._toggle_translation)
        self._toggle_btn.setStyleSheet(
            "QPushButton { background: rgba(0,100,0,200); color: #40FF40; "
            "border: 1px solid #40FF40; border-radius: 3px; font-size: 10px; }"
        )
        title_bar.addWidget(self._toggle_btn)

        # Minimize button
        self._minimize_btn = QPushButton("─")
        self._minimize_btn.setFixedSize(20, 20)
        self._minimize_btn.setStyleSheet(
            "QPushButton { background: rgba(60,60,60,200); color: #FFD200; "
            "border: 1px solid #FFD200; border-radius: 3px; font-size: 12px; font-weight: bold; }"
            "QPushButton:hover { background: rgba(100,100,0,200); }"
        )
        self._minimize_btn.clicked.connect(self._toggle_minimize)
        title_bar.addWidget(self._minimize_btn)

        # Quit button (in title bar, away from other controls)
        quit_btn = QPushButton("✕")
        quit_btn.setFixedSize(20, 20)
        quit_btn.setStyleSheet(
            "QPushButton { background: rgba(100,0,0,200); color: #FF4040; "
            "border: 1px solid #FF4040; border-radius: 3px; font-size: 12px; font-weight: bold; }"
            "QPushButton:hover { background: rgba(150,0,0,200); }"
        )
        quit_btn.clicked.connect(self.quit_requested.emit)
        title_bar.addWidget(quit_btn)

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

        settings_btn = QPushButton(tr("overlay.settings"))
        settings_btn.setFixedHeight(20)
        settings_btn.setStyleSheet(_TB_BTN)
        settings_btn.clicked.connect(self.settings_requested.emit)
        tb_layout.addWidget(settings_btn)

        opacity_label = QLabel(tr("overlay.opacity"))
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

        # ── Reply translator panel (always visible) ──
        self._reply_panel = QWidget()
        self._reply_panel.setStyleSheet(
            "background: rgba(20, 20, 20, 220); border-top: 1px solid #444;"
        )
        reply_layout = QVBoxLayout(self._reply_panel)
        reply_layout.setContentsMargins(4, 4, 4, 4)
        reply_layout.setSpacing(3)

        # Input row: text field + Enter hint + target lang combobox
        input_row = QHBoxLayout()
        input_row.setSpacing(4)
        self._reply_input = QLineEdit()
        self._reply_input.setPlaceholderText(tr("overlay.reply.input_hint"))
        self._reply_input.setMaxLength(255)
        self._reply_input.setStyleSheet(
            "QLineEdit { background: #111; color: #e0e0e0; border: 1px solid #555; "
            "border-radius: 3px; padding: 4px 6px; font-size: 11px; }"
            "QLineEdit:focus { border-color: #FFD200; }"
        )
        self._reply_input.returnPressed.connect(self._do_reply_translate)
        input_row.addWidget(self._reply_input)

        # Enter hint
        enter_hint = QLabel("\u23CE")
        enter_hint.setFixedSize(20, 24)
        enter_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        enter_hint.setStyleSheet("color: #555; font-size: 14px; background: transparent;")
        enter_hint.setToolTip("Enter")
        input_row.addWidget(enter_hint)

        # Language selector combobox
        self._reply_lang_combo = QComboBox()
        _reply_langs = [
            ("EN", "EN"),
            ("RU", "RU"),
            ("DE", "DE"),
            ("FR", "FR"),
            ("ES", "ES"),
            ("IT", "IT"),
            ("PT", "PT"),
            ("PL", "PL"),
            ("UK", "UK"),
            ("TR", "TR"),
            ("ZH", "ZH"),
            ("JA", "JA"),
            ("KO", "KO"),
            ("NL", "NL"),
            ("CS", "CS"),
            ("SV", "SV"),
        ]
        for code, label in _reply_langs:
            self._reply_lang_combo.addItem(f"\u2192 {label}", code)
        self._reply_lang_combo.setStyleSheet(
            "QComboBox { background: #222; color: #FFD200; border: 1px solid #555; "
            "border-radius: 3px; padding: 2px 4px; font-size: 10px; font-weight: bold; "
            "min-width: 60px; }"
            "QComboBox:focus { border-color: #FFD200; }"
            "QComboBox::drop-down { border: none; background: #333; width: 16px; }"
            "QComboBox QAbstractItemView { background: #1a1a1a; color: #e0e0e0; "
            "selection-background-color: #FFD200; selection-color: #000; "
            "border: 1px solid #555; }"
        )
        self._reply_lang_combo.setFixedHeight(24)
        self._reply_lang_combo.currentIndexChanged.connect(self._on_reply_lang_changed)
        input_row.addWidget(self._reply_lang_combo)
        reply_layout.addLayout(input_row)

        # Result row: output field + copy button
        result_row = QHBoxLayout()
        result_row.setSpacing(4)
        self._reply_output = QLineEdit()
        self._reply_output.setReadOnly(True)
        self._reply_output.setStyleSheet(
            "QLineEdit { background: #0a0a0a; color: #FFD200; border: 1px solid #444; "
            "border-radius: 3px; padding: 4px 6px; font-size: 11px; }"
        )
        result_row.addWidget(self._reply_output)

        self._reply_copy_btn = QPushButton(tr("overlay.reply.copy"))
        self._reply_copy_btn.setFixedHeight(24)
        self._reply_copy_btn.setStyleSheet(
            "QPushButton { background: rgba(60,60,60,200); color: #ccc; "
            "border: 1px solid #555; border-radius: 3px; font-size: 10px; }"
            "QPushButton:hover { color: #FFD200; border-color: #FFD200; }"
        )
        self._reply_copy_btn.clicked.connect(self._copy_reply)
        result_row.addWidget(self._reply_copy_btn)
        reply_layout.addLayout(result_row)

        # "Copied!" flash label
        self._reply_status = QLabel("")
        self._reply_status.setStyleSheet(
            "color: #40FF40; font-size: 10px; font-weight: bold;"
        )
        self._reply_status.setAlignment(Qt.AlignmentFlag.AlignRight)
        reply_layout.addWidget(self._reply_status)

        container_layout.addWidget(self._reply_panel)

        # Resize grip in bottom-right corner
        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 0, 0)
        grip_row.addStretch()
        self._resize_grip = QLabel("\u2921")
        self._resize_grip.setFixedSize(16, 16)
        self._resize_grip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._resize_grip.setStyleSheet(
            "color: #555; font-size: 12px; background: transparent;"
        )
        self._resize_grip.setToolTip(tr("overlay.resize_hint") if "overlay.resize_hint" in dir(tr) else "Resize")
        grip_row.addWidget(self._resize_grip)
        container_layout.addLayout(grip_row)

        layout.addWidget(self._container)

    def load_history(self, messages: list[TranslatedMessage]) -> None:
        """Load historical messages and add a separator after them."""
        for msg in messages:
            self._messages.append(msg)
            self._render_message(msg)
        if messages:
            self._render_separator()

    def _render_separator(self) -> None:
        """Render a visual separator line in the chat area."""
        cursor = self._chat_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        sep_fmt = QTextCharFormat()
        sep_fmt.setForeground(QColor("#555555"))
        cursor.insertText("\n")
        cursor.setCharFormat(sep_fmt)
        cursor.insertText("── " + tr("overlay.session_start") + " ──")
        self._chat_area.verticalScrollBar().setValue(
            self._chat_area.verticalScrollBar().maximum()
        )

    def add_message(self, msg: TranslatedMessage) -> None:
        """Thread-safe way to add a message (emits signal)."""
        self.message_received.emit(msg)

    @pyqtSlot(object)
    def _on_message(self, msg: TranslatedMessage) -> None:
        """Handle a new translated message on the GUI thread."""
        self._messages.append(msg)
        # Only render if it passes the current filter
        filter_channels = _FILTER_CHANNELS.get(self._active_filter, set(Channel))
        if msg.original.channel in filter_channels:
            self._render_message(msg)

    def _render_message(self, msg: TranslatedMessage) -> None:
        """Render a single message into the chat area."""
        channel = msg.original.channel

        has_translation = (
            self._translation_enabled
            and msg.translation
            and msg.translation.success
            and msg.translation.translated != msg.original.text
        )

        cursor = self._chat_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # Channel color and prefix
        color = CHANNEL_COLORS.get(channel, "#FFFFFF")
        prefix = CHANNEL_PREFIXES.get(channel, "")

        # Format timestamp (e.g., "2/15 21:30:45.123" → "21:30")
        ts = msg.original.timestamp
        time_part = ts.split(" ", 1)[-1] if " " in ts else ts  # "21:30:45.123"
        short_time = ":".join(time_part.split(":")[:2])  # "21:30"

        # Timestamp in dim gray
        ts_fmt = QTextCharFormat()
        ts_fmt.setForeground(QColor("#666666"))
        cursor.insertText("\n")
        cursor.setCharFormat(ts_fmt)
        cursor.insertText(f"{short_time} ")

        # Channel prefix + author in channel color
        chan_fmt = QTextCharFormat()
        chan_fmt.setForeground(QColor(color))
        cursor.setCharFormat(chan_fmt)
        cursor.insertText(f"{prefix} {msg.original.author}: ")

        if has_translation:
            # Original text in gray (subdued)
            orig_fmt = QTextCharFormat()
            orig_fmt.setForeground(QColor("#888888"))
            cursor.setCharFormat(orig_fmt)
            cursor.insertText(msg.original.text)

            # Translation in gold
            tr_fmt = QTextCharFormat()
            tr_fmt.setForeground(QColor(TRANSLATION_COLOR))
            cursor.setCharFormat(tr_fmt)
            cursor.insertText(f" → {msg.translation.translated}")
        else:
            # No translation — show text in channel color
            cursor.setCharFormat(chan_fmt)
            cursor.insertText(msg.original.text)

        # Auto-scroll to bottom
        self._chat_area.verticalScrollBar().setValue(
            self._chat_area.verticalScrollBar().maximum()
        )

    def _rerender_chat(self) -> None:
        """Clear and re-render all messages matching the current filter."""
        self._chat_area.clear()
        filter_channels = _FILTER_CHANNELS.get(self._active_filter, set(Channel))
        for msg in self._messages:
            if msg.original.channel in filter_channels:
                self._render_message(msg)

    def update_channel_filters(self, enabled: set[str]) -> None:
        """Update which filter tabs are visible based on config channel settings."""
        self._filter_bar.update_enabled_filters(enabled)

    def _on_filter_changed(self, filter_name: str) -> None:
        self._active_filter = filter_name
        self._rerender_chat()

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

    def _toggle_minimize(self) -> None:
        """Toggle between full overlay and collapsed title-button."""
        self._minimized = not self._minimized
        if self._minimized:
            # Save current size, collapse
            self._restored_size = (self.width(), self.height())
            self._toolbar.hide()
            self._filter_bar.hide()
            self._chat_area.hide()
            self._reply_panel.hide()
            self._resize_grip.hide()
            self._toggle_btn.hide()
            self._minimize_btn.setText("+")
            # Shrink to title bar only
            self.setMinimumSize(0, 0)
            self.resize(180, 32)
        else:
            # Restore
            self._toolbar.show()
            self._filter_bar.show()
            self._chat_area.show()
            self._reply_panel.show()
            self._resize_grip.show()
            self._toggle_btn.show()
            self._minimize_btn.setText("─")
            self.setMinimumSize(350, 200)
            if self._restored_size:
                self.resize(*self._restored_size)

    def _on_opacity_changed(self, value: int) -> None:
        self._bg_opacity = value
        self._container.setStyleSheet(
            f"background: rgba(0, 0, 0, {value}); border-radius: 4px;"
        )

    # -- Reply translator --

    def set_wow_status_checker(
        self, checker: Callable[[], str],
    ) -> None:
        """Set a callable that returns WoW connection status string.

        Called every 2 seconds to update the status indicator.
        Expected return values: "attached", "searching", "offline".
        """
        self._wow_checker = checker
        self._wow_timer = QTimer(self)
        self._wow_timer.timeout.connect(self._update_wow_status)
        self._wow_timer.start(2000)
        # Initial update
        self._update_wow_status()

    def _update_wow_status(self) -> None:
        """Update WoW connection status label."""
        if not hasattr(self, "_wow_checker"):
            return
        status = self._wow_checker()
        if status == "attached":
            self._wow_status.setText("WoW: \u2714")
            self._wow_status.setStyleSheet(
                "color: #40FF40; font-size: 9px; padding: 0 4px;"
            )
        elif status == "searching":
            self._wow_status.setText("WoW: ...")
            self._wow_status.setStyleSheet(
                "color: #FFD200; font-size: 9px; padding: 0 4px;"
            )
        else:
            self._wow_status.setText("WoW: \u2716")
            self._wow_status.setStyleSheet(
                "color: #888; font-size: 9px; padding: 0 4px;"
            )

    def set_translator(self, translator: TranslatorService, target_lang: str) -> None:
        """Provide the translator service and target language for reply translation."""
        self._translator = translator
        self._target_lang = target_lang
        idx = self._reply_lang_combo.findData(target_lang)
        if idx >= 0:
            self._reply_lang_combo.setCurrentIndex(idx)

    def _on_reply_lang_changed(self, index: int) -> None:
        code = self._reply_lang_combo.currentData()
        if code:
            self._target_lang = code

    def _do_reply_translate(self) -> None:
        text = self._reply_input.text().strip()
        if not text or self._translator is None:
            return
        self._reply_output.setText(tr("overlay.reply.translating"))
        self._reply_input.setEnabled(False)
        worker = ReplyTranslateWorker(self._translator, text, self._target_lang)
        worker.signals.finished.connect(self._on_reply_translated)
        self._thread_pool.start(worker)

    @pyqtSlot(str, bool)
    def _on_reply_translated(self, translated: str, success: bool) -> None:
        self._reply_input.setEnabled(True)
        if success:
            self._reply_output.setText(translated)
            # Auto-copy to clipboard
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(translated)
            self._reply_status.setText(tr("overlay.reply.copied"))
            QTimer.singleShot(2000, lambda: self._reply_status.setText(""))
        else:
            self._reply_output.setText(tr("overlay.reply.error"))

    def _copy_reply(self) -> None:
        text = self._reply_output.text()
        if text and text != tr("overlay.reply.translating") and text != tr("overlay.reply.error"):
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(text)
            self._reply_status.setText(tr("overlay.reply.copied"))
            QTimer.singleShot(2000, lambda: self._reply_status.setText(""))

    # -- Drag & resize support --

    _EDGE_MARGIN = 8  # px from border to trigger resize

    _EDGE_CURSORS: dict[str, Qt.CursorShape] = {
        "br": Qt.CursorShape.SizeFDiagCursor,
        "bl": Qt.CursorShape.SizeBDiagCursor,
        "tr": Qt.CursorShape.SizeBDiagCursor,
        "tl": Qt.CursorShape.SizeFDiagCursor,
        "b": Qt.CursorShape.SizeVerCursor,
        "t": Qt.CursorShape.SizeVerCursor,
        "r": Qt.CursorShape.SizeHorCursor,
        "l": Qt.CursorShape.SizeHorCursor,
    }

    def _hit_edge(self, pos: QPoint) -> str | None:
        """Return resize edge name if mouse is near a border, else None."""
        r = self.rect()
        m = self._EDGE_MARGIN
        on_left = pos.x() < m
        on_right = pos.x() > r.width() - m
        on_top = pos.y() < m
        on_bottom = pos.y() > r.height() - m
        if on_bottom and on_right:
            return "br"
        if on_bottom and on_left:
            return "bl"
        if on_top and on_right:
            return "tr"
        if on_top and on_left:
            return "tl"
        if on_bottom:
            return "b"
        if on_right:
            return "r"
        if on_left:
            return "l"
        if on_top:
            return "t"
        return None

    def mousePressEvent(self, event: object) -> None:
        if (
            hasattr(event, 'button')
            and event.button() == Qt.MouseButton.LeftButton  # type: ignore[union-attr]
        ):
            pos = event.position().toPoint()  # type: ignore[union-attr]
            edge = self._hit_edge(pos)
            if edge:
                self._resize_edge = edge
                self._drag_pos = event.globalPosition().toPoint()  # type: ignore[union-attr]
            else:
                self._resize_edge = None
                self._drag_pos = event.globalPosition().toPoint() - self.pos()  # type: ignore[union-attr]

    def mouseMoveEvent(self, event: object) -> None:
        pos = event.position().toPoint()  # type: ignore[union-attr]

        # Update cursor when hovering (no button pressed)
        if not (
            hasattr(event, 'buttons')
            and event.buttons() & Qt.MouseButton.LeftButton  # type: ignore[union-attr]
        ):
            edge = self._hit_edge(pos)
            if edge:
                self.setCursor(QCursor(self._EDGE_CURSORS[edge]))
            else:
                self.unsetCursor()
            return
        if self._drag_pos is None:
            return
        gpos = event.globalPosition().toPoint()  # type: ignore[union-attr]
        if self._resize_edge:
            self._do_resize(gpos)
        else:
            self.move(gpos - self._drag_pos)  # type: ignore[union-attr]

    def _do_resize(self, gpos: QPoint) -> None:
        """Resize the overlay based on which edge is being dragged."""
        dx = gpos.x() - self._drag_pos.x()  # type: ignore[union-attr]
        dy = gpos.y() - self._drag_pos.y()  # type: ignore[union-attr]
        geo = self.geometry()
        e = self._resize_edge
        min_w, min_h = self.minimumWidth(), self.minimumHeight()
        if "r" in e:  # type: ignore[operator]
            geo.setWidth(max(min_w, geo.width() + dx))
        if "b" in e:  # type: ignore[operator]
            geo.setHeight(max(min_h, geo.height() + dy))
        if "l" in e:  # type: ignore[operator]
            new_w = max(min_w, geo.width() - dx)
            geo.setLeft(geo.right() - new_w)
        if "t" in e:  # type: ignore[operator]
            new_h = max(min_h, geo.height() - dy)
            geo.setTop(geo.bottom() - new_h)
        self.setGeometry(geo)
        self._drag_pos = gpos  # type: ignore[assignment]

    def mouseReleaseEvent(self, event: object) -> None:
        self._drag_pos = None
        self._resize_edge = None
        self._save_overlay_state()

    # -- Settings persistence --

    def _save_overlay_state(self) -> None:
        """Save overlay position, size, and opacity to AppConfig."""
        self._config.overlay_x = self.x()
        self._config.overlay_y = self.y()
        self._config.overlay_width = self.width()
        self._config.overlay_height = self.height()
        self._config.overlay_opacity = self._bg_opacity
        self._config.save()

    def apply_settings(self, config: AppConfig) -> None:
        """Apply settings from an updated AppConfig (e.g. after settings dialog)."""
        self._config = config
        self._bg_opacity = config.overlay_opacity
        self._opacity_slider.setValue(config.overlay_opacity)
        self._on_opacity_changed(config.overlay_opacity)
