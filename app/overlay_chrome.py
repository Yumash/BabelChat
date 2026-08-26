"""Building the overlay's furniture: title bar, toolbar, chat area, reply row.

Two hundred and forty lines of widget construction with no decisions in it.
Kept out of overlay.py so that file is about how the window behaves rather
than about how it is assembled — the same reason the stylesheet lives in
qt_theme.py.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.about_dialog import VERSION
from app.i18n import tr
from app.overlay_widgets import ChannelFilterBar, _ResizeGrip

#: Transparent margin around the container that the resize edges live in.
_EDGE_MARGIN = 8
#: Ceiling on the chat document's blocks, which bounds the DOM Qt keeps.
_MAX_DOC_BLOCKS = 1500

if TYPE_CHECKING:
    from app.overlay import ChatOverlay


def build(overlay: ChatOverlay) -> None:
    """Populate `overlay` with its widgets, leaving them on it by name."""
    layout = QVBoxLayout(overlay)
    # Outer margins create transparent grip area matching _EDGE_MARGIN
    layout.setContentsMargins(
        _EDGE_MARGIN,
        _EDGE_MARGIN,
        _EDGE_MARGIN,
        _EDGE_MARGIN,
    )
    layout.setSpacing(0)
    overlay.setMouseTracking(True)

    # Main container with WoW-dark background
    overlay._container = QWidget()
    overlay._container.setMouseTracking(True)
    overlay._container.setStyleSheet("background: rgba(0, 0, 0, 180); border-radius: 4px;")
    container_layout = QVBoxLayout(overlay._container)
    container_layout.setContentsMargins(4, 4, 4, 4)
    container_layout.setSpacing(2)

    # Title bar
    title_bar = QHBoxLayout()
    title_label = QLabel(f"BabelChat {VERSION}")
    title_label.setStyleSheet("color: #FFD200; font-size: 11px; font-weight: bold; padding: 2px;")
    title_bar.addWidget(title_label)
    title_bar.addStretch()

    # WoW connection status
    overlay._wow_status = QLabel("WoW: ?")
    overlay._wow_status.setFixedHeight(20)
    overlay._wow_status.setStyleSheet("color: #888; font-size: 9px; padding: 0 4px;")
    title_bar.addWidget(overlay._wow_status)

    # Translation toggle
    overlay._toggle_btn = QPushButton(tr("overlay.badge.on"))
    overlay._toggle_btn.setFixedSize(50, 20)
    overlay._toggle_btn.clicked.connect(overlay._toggle_translation)
    overlay._toggle_btn.setStyleSheet(
        "QPushButton { background: rgba(0,100,0,200); color: #40FF40; "
        "border: 1px solid #40FF40; border-radius: 3px; font-size: 10px; }"
    )
    title_bar.addWidget(overlay._toggle_btn)

    # Minimize button
    overlay._minimize_btn = QPushButton("─")
    overlay._minimize_btn.setFixedSize(20, 20)
    overlay._minimize_btn.setStyleSheet(
        "QPushButton { background: rgba(60,60,60,200); color: #FFD200; "
        "border: 1px solid #FFD200; border-radius: 3px; font-size: 12px; font-weight: bold; }"
        "QPushButton:hover { background: rgba(100,100,0,200); }"
    )
    overlay._minimize_btn.clicked.connect(overlay._toggle_minimize)
    title_bar.addWidget(overlay._minimize_btn)

    # Quit button (in title bar, away from other controls)
    quit_btn = QPushButton("✕")
    quit_btn.setFixedSize(20, 20)
    quit_btn.setStyleSheet(
        "QPushButton { background: rgba(100,0,0,200); color: #FF4040; "
        "border: 1px solid #FF4040; border-radius: 3px; font-size: 12px; font-weight: bold; }"
        "QPushButton:hover { background: rgba(150,0,0,200); }"
    )
    quit_btn.clicked.connect(overlay.quit_requested.emit)
    title_bar.addWidget(quit_btn)

    container_layout.addLayout(title_bar)

    # Toolbar (visible only in interactive/unlocked mode)
    overlay._toolbar = QWidget()
    tb_layout = QHBoxLayout(overlay._toolbar)
    tb_layout.setContentsMargins(2, 0, 2, 0)
    tb_layout.setSpacing(4)

    _TB_BTN = (
        "QPushButton { background: rgba(60,60,60,200); color: #ccc; "
        "border: 1px solid #555; border-radius: 3px; padding: 2px 8px; font-size: 10px; }"
        "QPushButton:hover { color: #FFD200; border-color: #FFD200; }"
    )

    settings_btn = QPushButton(tr("overlay.settings"))
    # Kept on the overlay so a language change can reach it: a Qt widget holds
    # the string it was built with, and a local goes out of scope here.
    overlay._settings_btn = settings_btn
    settings_btn.setFixedHeight(20)
    settings_btn.setStyleSheet(_TB_BTN)
    settings_btn.clicked.connect(overlay.settings_requested.emit)
    tb_layout.addWidget(settings_btn)

    opacity_label = QLabel(tr("overlay.opacity"))
    overlay._opacity_label = opacity_label
    opacity_label.setStyleSheet("color: #999; font-size: 10px;")
    tb_layout.addWidget(opacity_label)

    overlay._opacity_slider = QSlider(Qt.Orientation.Horizontal)
    overlay._opacity_slider.setRange(30, 255)
    overlay._opacity_slider.setValue(overlay._bg_opacity)
    overlay._opacity_slider.setFixedWidth(80)
    overlay._opacity_slider.setFixedHeight(16)
    overlay._opacity_slider.setStyleSheet(
        "QSlider::groove:horizontal { height: 4px; background: #333; border-radius: 2px; }"
        "QSlider::handle:horizontal { background: #FFD200; width: 10px; height: 10px; "
        "margin: -3px 0; border-radius: 5px; }"
        "QSlider::sub-page:horizontal { background: #997d00; border-radius: 2px; }"
    )
    overlay._opacity_slider.valueChanged.connect(overlay._on_opacity_changed)
    tb_layout.addWidget(overlay._opacity_slider)

    tb_layout.addStretch()
    overlay._toolbar.show()
    container_layout.addWidget(overlay._toolbar)

    # Channel filter tabs
    overlay._filter_bar = ChannelFilterBar()
    overlay._filter_bar.filter_changed.connect(overlay._on_filter_changed)
    container_layout.addWidget(overlay._filter_bar)

    # Chat message area
    overlay._chat_area = QTextEdit()
    overlay._chat_area.setReadOnly(True)
    overlay._chat_area.document().setMaximumBlockCount(_MAX_DOC_BLOCKS)
    overlay._chat_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    overlay._chat_area.setStyleSheet("QTextEdit { background: transparent; border: none; color: #FFFFFF; }")
    font = QFont("Consolas", 10)
    overlay._chat_area.setFont(font)
    container_layout.addWidget(overlay._chat_area)

    # ── Reply translator panel (always visible) ──
    overlay._reply_panel = QWidget()
    overlay._reply_panel.setStyleSheet("background: rgba(20, 20, 20, 220); border-top: 1px solid #444;")
    reply_layout = QVBoxLayout(overlay._reply_panel)
    reply_layout.setContentsMargins(4, 4, 4, 4)
    reply_layout.setSpacing(3)

    # Input row: text field + Enter hint + target lang combobox
    input_row = QHBoxLayout()
    input_row.setSpacing(4)
    overlay._reply_input = QLineEdit()
    overlay._reply_input.setPlaceholderText(tr("overlay.reply.input_hint"))
    overlay._reply_input.setMaxLength(255)
    overlay._reply_input.setStyleSheet(
        "QLineEdit { background: #111; color: #e0e0e0; border: 1px solid #555; "
        "border-radius: 3px; padding: 4px 6px; font-size: 11px; }"
        "QLineEdit:focus { border-color: #FFD200; }"
    )
    overlay._reply_input.returnPressed.connect(overlay._do_reply_translate)
    # On Linux with X11BypassWindowManagerHint, temporarily drop the bypass
    # flag when the input has focus so keyboard events are routed correctly
    if sys.platform != "win32":
        overlay._reply_input.focusInEvent = overlay._on_reply_focus_in
        overlay._reply_input.focusOutEvent = overlay._on_reply_focus_out
    input_row.addWidget(overlay._reply_input)

    # Enter button
    enter_btn = QPushButton("\u23ce")
    enter_btn.setFixedSize(24, 24)
    enter_btn.setStyleSheet(
        "QPushButton { color: #555; font-size: 14px; background: transparent; "
        "border: 1px solid transparent; border-radius: 3px; }"
        "QPushButton:hover { color: #FFD200; border-color: #FFD200; }"
    )
    enter_btn.setToolTip("Enter")
    enter_btn.clicked.connect(overlay._do_reply_translate)
    input_row.addWidget(enter_btn)

    # Language selector combobox
    overlay._reply_lang_combo = QComboBox()
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
        overlay._reply_lang_combo.addItem(f"\u2192 {label}", code)
    overlay._reply_lang_combo.setStyleSheet(
        "QComboBox { background: #222; color: #FFD200; border: 1px solid #555; "
        "border-radius: 3px; padding: 2px 4px; font-size: 10px; font-weight: bold; "
        "min-width: 60px; }"
        "QComboBox:focus { border-color: #FFD200; }"
        "QComboBox::drop-down { border: none; background: #333; width: 16px; }"
        "QComboBox QAbstractItemView { background: #1a1a1a; color: #e0e0e0; "
        "selection-background-color: #FFD200; selection-color: #000; "
        "border: 1px solid #555; }"
    )
    overlay._reply_lang_combo.setFixedHeight(24)
    overlay._reply_lang_combo.currentIndexChanged.connect(overlay._on_reply_lang_changed)
    input_row.addWidget(overlay._reply_lang_combo)
    reply_layout.addLayout(input_row)

    # Result row: output field + copy button
    result_row = QHBoxLayout()
    result_row.setSpacing(4)
    overlay._reply_output = QLineEdit()
    overlay._reply_output.setReadOnly(True)
    overlay._reply_output.setStyleSheet(
        "QLineEdit { background: #0a0a0a; color: #FFD200; border: 1px solid #444; "
        "border-radius: 3px; padding: 4px 6px; font-size: 11px; }"
    )
    result_row.addWidget(overlay._reply_output)

    overlay._reply_copy_btn = QPushButton(tr("overlay.reply.copy"))
    overlay._reply_copy_btn.setFixedHeight(24)
    overlay._reply_copy_btn.setStyleSheet(
        "QPushButton { background: rgba(60,60,60,200); color: #ccc; "
        "border: 1px solid #555; border-radius: 3px; font-size: 10px; }"
        "QPushButton:hover { color: #FFD200; border-color: #FFD200; }"
    )
    overlay._reply_copy_btn.clicked.connect(overlay._copy_reply)
    result_row.addWidget(overlay._reply_copy_btn)
    reply_layout.addLayout(result_row)

    # "Copied!" flash label
    overlay._reply_status = QLabel("")
    overlay._reply_status.setStyleSheet("color: #40FF40; font-size: 10px; font-weight: bold;")
    overlay._reply_status.setAlignment(Qt.AlignmentFlag.AlignRight)
    reply_layout.addWidget(overlay._reply_status)

    container_layout.addWidget(overlay._reply_panel)
    # On Linux, the reply dialog is a separate window — hide the embedded panel
    if sys.platform != "win32":
        overlay._reply_panel.hide()

    # Resize grip in bottom-right corner
    grip_row = QHBoxLayout()
    grip_row.setContentsMargins(0, 0, 0, 0)
    grip_row.addStretch()
    overlay._resize_grip = _ResizeGrip(overlay)
    grip_row.addWidget(overlay._resize_grip)
    container_layout.addLayout(grip_row)

    layout.addWidget(overlay._container)
