"""Smart overlay chat window styled as WoW native chat."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable

from PyQt6.QtCore import QPoint, Qt, QThreadPool, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
)

from app import overlay_chrome
from app.config import AppConfig
from app.i18n import tr
from app.overlay_frameless import _MIN_HEIGHT, _MIN_WIDTH, FramelessDragResizeMixin
from app.overlay_reply import ReplyDialog, ReplyPanelMixin
from app.overlay_widgets import (
    _FILTER_CHANNELS,
    CHANNEL_COLORS,
    CHANNEL_PREFIXES,
    TRANSLATION_COLOR,
)
from app.parser import Channel
from app.pipeline import TranslatedMessage
from app.translator import TranslatorService
from app.translators.base import FAILURE

logger = logging.getLogger(__name__)

# --- Overlay layout constants ---
_MAX_MESSAGES = 500  # Max messages kept in memory (prevents unbounded growth)
_MINIMIZE_WIDTH = 180  # Width when overlay is minimized to title bar
_MINIMIZE_HEIGHT = 32  # Height when overlay is minimized to title bar
_WOW_STATUS_INTERVAL = 2000  # WoW connection status poll interval (ms)
_COPIED_FLASH_MS = 2000  # Duration of "Copied!" flash label (ms)



def _on_screen_y(widget: QWidget, wanted: int) -> int:
    """`wanted`, unless that would put the window off the screen.

    Growing back upwards from the bottom edge can ask for a negative y when the
    overlay was collapsed near the top, and a window with its title bar above
    the screen cannot be dragged back.
    """
    screen = widget.screen() or QApplication.primaryScreen()
    if screen is None:
        return max(0, wanted)
    available = screen.availableGeometry()
    lowest = available.bottom() - widget.height()
    return max(available.top(), min(wanted, lowest))


class ChatOverlay(ReplyPanelMixin, FramelessDragResizeMixin, QWidget):
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
        self._max_messages = _MAX_MESSAGES
        self._minimized = False
        self._restored_size: tuple[int, int] | None = None
        # On Linux, use a separate window for the reply panel to get keyboard input
        self._reply_dialog: ReplyDialog | None = None
        if sys.platform != "win32":
            self._reply_dialog = ReplyDialog()

        self._setup_window()
        self._setup_ui()
        self.move(config.overlay_x, config.overlay_y)
        self.resize(config.overlay_width, config.overlay_height)
        self._opacity_slider.setValue(config.overlay_opacity)
        self._on_opacity_changed(config.overlay_opacity)

        self.message_received.connect(self._on_message)

    def _setup_window(self) -> None:
        """Configure window flags for overlay behavior."""
        if sys.platform == "win32":
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
            )
        else:
            # X11BypassWindowManagerHint routes through XWayland, giving us
            # true always-on-top and free move() positioning on KDE/Wayland.
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.X11BypassWindowManagerHint
                | Qt.WindowType.WindowStaysOnTopHint
            )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(_MIN_WIDTH, _MIN_HEIGHT)
        self.resize(450, 300)

    def _setup_ui(self) -> None:
        """Build the overlay UI — see app/overlay_chrome.py."""
        overlay_chrome.build(self)

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
        self._chat_area.verticalScrollBar().setValue(self._chat_area.verticalScrollBar().maximum())

    def add_message(self, msg: TranslatedMessage) -> None:
        """Thread-safe way to add a message (emits signal)."""
        self.message_received.emit(msg)

    @pyqtSlot(object)
    def _on_message(self, msg: TranslatedMessage) -> None:
        """Handle a new translated message on the GUI thread.

        Supports streaming updates: if msg.is_update is True, replaces the
        matching msg_id in _messages and re-renders the last message.
        """
        if msg.is_update and msg.msg_id:
            # Find and replace the original message by msg_id
            for i in range(len(self._messages) - 1, -1, -1):
                if self._messages[i].msg_id == msg.msg_id:
                    self._messages[i] = msg
                    break
            # Re-render: update the last line in chat area
            filter_channels = _FILTER_CHANNELS.get(self._active_filter, set(Channel))
            if msg.original.channel in filter_channels:
                self._update_last_message(msg)
            return

        self._messages.append(msg)
        # Trim old messages to prevent unbounded growth
        if len(self._messages) > self._max_messages:
            self._messages = self._messages[-self._max_messages :]
            self._rerender_chat()
            return
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

            # When every provider declined, say so in three words rather than
            # leaving the line looking like an ordinary untranslated one. The
            # alternative was worse: GigaChat's refusal is a paragraph about
            # itself, and passing it through put that paragraph where the
            # translation goes.
            if self._translation_enabled and msg.translation and msg.translation.error == FAILURE.REFUSED:
                note_fmt = QTextCharFormat()
                note_fmt.setForeground(QColor("#888888"))
                cursor.setCharFormat(note_fmt)
                cursor.insertText(f" — {tr('overlay.refused')}")

        # Auto-scroll to bottom
        self._chat_area.verticalScrollBar().setValue(self._chat_area.verticalScrollBar().maximum())

    def _update_last_message(self, msg: TranslatedMessage) -> None:
        """Update the last rendered message with translation (streaming).

        Removes the last line from the chat area and re-renders it with
        the translation attached.
        """
        cursor = self._chat_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        # Select from the last newline to the end
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, QTextCursor.MoveMode.KeepAnchor)
        # Also select the preceding newline
        cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        # Re-render the message (now with translation)
        self._render_message(msg)

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

    def translate_clipboard(self) -> None:
        """Translate whatever is on the clipboard, from the global hotkey.

        Delegates to the reply dialog, which owns the translator and the target
        language the user picked. The dialog is created lazily, so this creates
        it if the user has never opened it — pressing the key is the request.
        """
        if self._reply_dialog is None:
            self._reply_dialog = ReplyDialog()
            if self._translator is not None:
                self._reply_dialog.set_translator(self._translator, self._target_lang)
        self._reply_dialog.translate_clipboard()

    def _toggle_translation(self) -> None:
        self._translation_enabled = not self._translation_enabled
        if self._translation_enabled:
            self._toggle_btn.setText(tr("overlay.badge.on"))
            self._toggle_btn.setStyleSheet(
                "QPushButton { background: rgba(0,100,0,200); color: #40FF40; "
                "border: 1px solid #40FF40; border-radius: 3px; font-size: 10px; }"
            )
        else:
            self._toggle_btn.setText(tr("overlay.badge.off"))
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
            if self._reply_dialog is not None:
                self._reply_dialog.hide()
            self._resize_grip.hide()
            self._toggle_btn.hide()
            self._minimize_btn.setText("+")
            # Shrink to title bar only, keeping the BOTTOM edge where it is.
            #
            # Qt shrinks a window towards its top-left, so an overlay parked
            # along the bottom of the screen used to jump into the middle of it
            # when collapsed — which defeats collapsing it. Anchoring the bottom
            # instead means it tucks against the edge and stays there.
            bottom = self.y() + self.height()
            self.setMinimumSize(0, 0)
            self.resize(_MINIMIZE_WIDTH, _MINIMIZE_HEIGHT)
            # The height it actually became, not the one asked for: the title
            # bar's own layout will not go below about sixty pixels, and
            # anchoring to the wish rather than the fact left the window thirty
            # pixels below where it started.
            self.move(self.x(), _on_screen_y(self, bottom - self.height()))
        else:
            # Restore — measure the collapsed bottom edge FIRST.
            #
            # Showing the widgets back and lifting the minimum size both make
            # the window taller straight away, so a measurement taken after
            # them is of a window that has already grown, and the restored one
            # lands a hundred pixels too low.
            bottom = self.y() + self.height()
            self._toolbar.show()
            self._filter_bar.show()
            self._chat_area.show()
            self._reply_panel.show()
            if self._reply_dialog is not None:
                self._position_reply_dialog()
                self._reply_dialog.show()
            self._resize_grip.show()
            self._toggle_btn.show()
            self._minimize_btn.setText("─")
            self.setMinimumSize(_MIN_WIDTH, _MIN_HEIGHT)
            if self._restored_size:
                # Grow back upwards, from the same edge it shrank to.
                self.resize(*self._restored_size)
                self.move(self.x(), _on_screen_y(self, bottom - self.height()))

    def _on_opacity_changed(self, value: int) -> None:
        self._bg_opacity = value
        self._container.setStyleSheet(f"background: rgba(0, 0, 0, {value}); border-radius: 4px;")

    # -- Reply translator --

    def set_wow_status_checker(
        self,
        checker: Callable[[], str],
    ) -> None:
        """Set a callable that returns WoW connection status string.

        Called every 2 seconds to update the status indicator.
        Expected return values: "attached", "searching", "offline".
        """
        self._wow_checker = checker
        self._wow_timer = QTimer(self)
        self._wow_timer.timeout.connect(self._update_wow_status)
        self._wow_timer.start(_WOW_STATUS_INTERVAL)
        # Initial update
        self._update_wow_status()

    #: Status to (label, colour, explanation key). A named problem gets a
    #: colour of its own and a tooltip saying what to do about it \u2014 the whole
    #: failure this replaces was an indicator that looked healthy while nothing
    #: was arriving.
    _WOW_STATES = {
        "attached": ("WoW: \u2714", "#40FF40", ""),
        "searching": ("WoW: ...", "#FFD200", "overlay.wow.searching"),
        "offline": ("WoW: \u2716", "#888", "overlay.wow.offline"),
        "process_gone": ("WoW: \u2716", "#888", "overlay.wow.offline"),
        "access_denied": ("WoW: \U0001f512", "#FF6B6B", "overlay.wow.access_denied"),
        "no_buffer": ("WoW: ?", "#FF9F40", "overlay.wow.no_buffer"),
        "chat_locked": ("WoW: \U0001f512", "#FFD200", "overlay.wow.chat_locked"),
    }

    def _update_wow_status(self) -> None:
        """Update WoW connection status label."""
        if not hasattr(self, "_wow_checker"):
            return
        status = self._wow_checker()
        label, colour, explanation = self._WOW_STATES.get(status, ("WoW: \u2716", "#FF6B6B", "overlay.wow.unknown"))
        self._wow_status.setText(label)
        self._wow_status.setStyleSheet(f"color: {colour}; font-size: 9px; padding: 0 4px;")
        self._wow_status.setToolTip(tr(explanation, e=status) if explanation else "")

    def showEvent(self, event: object) -> None:
        super().showEvent(event)  # type: ignore[misc]
        if self._reply_dialog is not None and not self._minimized:
            self._position_reply_dialog()
            self._reply_dialog.show()

    def hideEvent(self, event: object) -> None:
        super().hideEvent(event)  # type: ignore[misc]
        if self._reply_dialog is not None:
            self._reply_dialog.hide()

    def moveEvent(self, event: object) -> None:
        super().moveEvent(event)  # type: ignore[misc]
        self._position_reply_dialog()

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)  # type: ignore[misc]
        self._position_reply_dialog()

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

    def apply_language(self) -> None:
        """Relabel everything built when the window was, after a language change.

        A Qt widget keeps the string it was constructed with, so setting the
        language alone changes nothing that is already on screen — the setting
        appeared to do nothing until the next launch, which reads as broken.

        Only the persistent chrome belongs here. The reply panel's status line
        is written afresh on every action, so it arrives in the new language by
        itself, and relabelling it here would overwrite whatever it is saying.
        """
        self._toggle_btn.setText(
            tr("overlay.badge.on") if self._translation_enabled else tr("overlay.badge.off")
        )
        self._settings_btn.setText(tr("overlay.settings"))
        self._opacity_label.setText(tr("overlay.opacity"))
        self._reply_input.setPlaceholderText(tr("overlay.reply.input_hint"))
        self._reply_copy_btn.setText(tr("overlay.reply.copy"))
        self._filter_bar.apply_language()
        # The clipboard dialog is created on demand and then kept, so it
        # outlives the setting that was changed after it.
        if self._reply_dialog is not None:
            self._reply_dialog.apply_language()
