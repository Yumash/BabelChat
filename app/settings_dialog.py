"""Settings dialog for WoWTranslator — WoW-themed dark UI."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import deepl
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QKeyEvent, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import AppConfig, detect_wow_path

# DeepL supported target languages
LANGUAGES = {
    "EN": "English",
    "RU": "Russian",
    "DE": "German",
    "FR": "French",
    "ES": "Spanish",
    "IT": "Italian",
    "PT": "Portuguese",
    "PL": "Polish",
    "NL": "Dutch",
    "SV": "Swedish",
    "DA": "Danish",
    "FI": "Finnish",
    "CS": "Czech",
    "RO": "Romanian",
    "HU": "Hungarian",
    "BG": "Bulgarian",
    "EL": "Greek",
    "TR": "Turkish",
    "UK": "Ukrainian",
    "JA": "Japanese",
    "KO": "Korean",
    "ZH": "Chinese",
}

# WoW-inspired dark theme stylesheet
WOW_THEME_STYLESHEET = """
QDialog {
    background-color: #1a1a1a;
    color: #e0e0e0;
}

QTabWidget::pane {
    border: 1px solid #333;
    background: #1a1a1a;
    border-radius: 4px;
}
QTabBar::tab {
    background: #2a2a2a;
    color: #999;
    border: 1px solid #333;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background: #333;
    color: #FFD200;
    border-bottom-color: #333;
}
QTabBar::tab:hover:!selected {
    color: #CCC;
    background: #2e2e2e;
}

QGroupBox {
    border: 1px solid #444;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 16px;
    background: #222;
    font-weight: bold;
    color: #FFD200;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 8px;
    color: #FFD200;
}

QLineEdit, QSpinBox {
    background: #111;
    color: #e0e0e0;
    border: 1px solid #555;
    border-radius: 3px;
    padding: 6px;
    selection-background-color: #FFD200;
    selection-color: #000;
}
QLineEdit:focus, QSpinBox:focus {
    border-color: #FFD200;
}

QComboBox {
    background: #111;
    color: #e0e0e0;
    border: 1px solid #555;
    border-radius: 3px;
    padding: 6px;
}
QComboBox:focus { border-color: #FFD200; }
QComboBox::drop-down {
    border: none;
    background: #333;
    width: 24px;
}
QComboBox QAbstractItemView {
    background: #1a1a1a;
    color: #e0e0e0;
    selection-background-color: #FFD200;
    selection-color: #000;
    border: 1px solid #555;
}

QCheckBox {
    color: #e0e0e0;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #555;
    border-radius: 3px;
    background: #111;
}
QCheckBox::indicator:checked {
    background: #FFD200;
    border-color: #FFD200;
}
QCheckBox::indicator:hover {
    border-color: #FFD200;
}

QPushButton {
    background: #333;
    color: #e0e0e0;
    border: 1px solid #555;
    border-radius: 3px;
    padding: 6px 14px;
}
QPushButton:hover {
    background: #444;
    border-color: #FFD200;
    color: #FFD200;
}
QPushButton:pressed {
    background: #555;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #333;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #FFD200;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #997d00, stop:1 #FFD200);
    border-radius: 3px;
}

QProgressBar {
    border: 1px solid #555;
    border-radius: 3px;
    background: #111;
    text-align: center;
    color: #e0e0e0;
    height: 20px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #997d00, stop:1 #FFD200);
    border-radius: 3px;
}

QLabel {
    color: #ccc;
}

QDialogButtonBox QPushButton {
    min-width: 80px;
}
"""


class HotkeyEdit(QWidget):
    """Widget for capturing keyboard shortcuts: shows current combo + Change button."""

    hotkey_changed = pyqtSignal(str)

    _MOD_NAMES = {
        Qt.Key.Key_Control: "Ctrl",
        Qt.Key.Key_Shift: "Shift",
        Qt.Key.Key_Alt: "Alt",
        Qt.Key.Key_Meta: "Win",
    }

    def __init__(self, current: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._hotkey = current
        self._recording = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._label = QLabel(current or "(none)")
        self._label.setStyleSheet(
            "color: #FFD200; font-weight: bold; font-size: 12px; padding: 4px 8px;"
            "background: #111; border: 1px solid #555; border-radius: 3px;"
        )
        self._label.setMinimumWidth(140)
        layout.addWidget(self._label)

        self._btn = QPushButton("Change")
        self._btn.setFixedWidth(70)
        self._btn.clicked.connect(self._start_recording)
        layout.addWidget(self._btn)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setFixedWidth(50)
        self._clear_btn.clicked.connect(self._clear)
        layout.addWidget(self._clear_btn)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def text(self) -> str:
        return self._hotkey

    def _start_recording(self) -> None:
        self._recording = True
        self._label.setText("Press keys...")
        self._label.setStyleSheet(
            "color: #40FF40; font-weight: bold; font-size: 12px; padding: 4px 8px;"
            "background: #111; border: 1px solid #40FF40; border-radius: 3px;"
        )
        self._btn.setText("Cancel")
        self._btn.clicked.disconnect()
        self._btn.clicked.connect(self._cancel_recording)
        self.setFocus()

    def _cancel_recording(self) -> None:
        self._recording = False
        self._label.setText(self._hotkey or "(none)")
        self._label.setStyleSheet(
            "color: #FFD200; font-weight: bold; font-size: 12px; padding: 4px 8px;"
            "background: #111; border: 1px solid #555; border-radius: 3px;"
        )
        self._btn.setText("Change")
        self._btn.clicked.disconnect()
        self._btn.clicked.connect(self._start_recording)

    def _clear(self) -> None:
        self._hotkey = ""
        self._label.setText("(none)")
        self._cancel_recording()
        self.hotkey_changed.emit("")

    def keyPressEvent(self, event: QKeyEvent | None) -> None:  # type: ignore[override]
        if not self._recording or event is None:
            super().keyPressEvent(event)  # type: ignore[arg-type]
            return

        key = event.key()
        # Ignore bare modifier presses
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return

        parts: list[str] = []
        mods = event.modifiers()
        if mods & Qt.KeyboardModifier.ControlModifier:
            parts.append("Ctrl")
        if mods & Qt.KeyboardModifier.ShiftModifier:
            parts.append("Shift")
        if mods & Qt.KeyboardModifier.AltModifier:
            parts.append("Alt")

        # Map key to name
        key_name = ""
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            key_name = chr(key)
        elif Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
            key_name = f"F{key - Qt.Key.Key_F1 + 1}"
        elif key == Qt.Key.Key_Escape:
            self._cancel_recording()
            return
        else:
            # Try Qt enum name
            try:
                key_name = Qt.Key(key).name.replace("Key_", "")
            except (ValueError, AttributeError):
                key_name = f"0x{key:X}"

        if not parts:
            # Require at least one modifier
            return

        parts.append(key_name)
        combo = "+".join(parts)
        self._hotkey = combo
        self._label.setText(combo)
        self._recording = False
        self._label.setStyleSheet(
            "color: #FFD200; font-weight: bold; font-size: 12px; padding: 4px 8px;"
            "background: #111; border: 1px solid #555; border-radius: 3px;"
        )
        self._btn.setText("Change")
        self._btn.clicked.disconnect()
        self._btn.clicked.connect(self._start_recording)
        self.hotkey_changed.emit(combo)


def _create_dialog_icon() -> QIcon:
    """Load icon from .ico file, or generate programmatically as fallback."""
    candidates = [
        Path(getattr(sys, "_MEIPASS", "")) / "assets" / "icon.ico",
        Path(__file__).parent.parent / "assets" / "icon.ico",
    ]
    for path in candidates:
        if path.is_file():
            return QIcon(str(path))

    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHints(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(30, 30, 30, 220))
    painter.setPen(QColor(255, 210, 0))
    painter.drawRoundedRect(1, 1, 30, 30, 4, 4)
    painter.setFont(QFont("Arial", 18, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), 0x0084, "W")  # AlignCenter
    painter.end()
    return QIcon(pixmap)


class SettingsDialog(QDialog):
    """Settings window with WoW-themed dark UI."""

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("WoWTranslator Settings")
        self.setWindowIcon(_create_dialog_icon())
        self.setMinimumSize(500, 520)
        self.setStyleSheet(WOW_THEME_STYLESHEET)

        layout = QVBoxLayout(self)

        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "General")
        tabs.addTab(self._create_overlay_tab(), "Overlay")
        tabs.addTab(self._create_hotkeys_tab(), "Hotkeys")
        layout.addWidget(tabs)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)

        # Gold-styled Save button
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText("Save")
        ok_btn.setStyleSheet(
            "QPushButton { background: #3a3000; color: #FFD200; "
            "border: 1px solid #FFD200; border-radius: 3px; padding: 8px 20px; }"
            "QPushButton:hover { background: #4a4000; }"
            "QPushButton:pressed { background: #555; }"
        )

        layout.addWidget(buttons)

    # ── General Tab ──────────────────────────────────────────────

    def _create_general_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # API Key
        layout.addWidget(self._create_api_group())

        # WoW Path
        path_group = QGroupBox("World of Warcraft")
        path_layout = QFormLayout(path_group)

        wow_row = QHBoxLayout()
        self._wow_path_input = QLineEdit(self._config.wow_path)
        self._wow_path_input.setPlaceholderText("C:/Program Files/World of Warcraft")
        wow_row.addWidget(self._wow_path_input)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_wow_path)
        wow_row.addWidget(browse_btn)
        detect_btn = QPushButton("Auto")
        detect_btn.clicked.connect(self._auto_detect_wow)
        wow_row.addWidget(detect_btn)
        path_layout.addRow("WoW Path:", wow_row)

        self._chatlog_input = QLineEdit(self._config.chatlog_path)
        self._chatlog_input.setPlaceholderText("Auto-detected from WoW path")
        path_layout.addRow("Chat Log:", self._chatlog_input)

        addon_row = QHBoxLayout()
        self._install_addon_btn = QPushButton("Install Addon to WoW")
        self._install_addon_btn.setStyleSheet(
            "QPushButton { background: #3a3000; color: #FFD200; "
            "border: 1px solid #FFD200; border-radius: 3px; padding: 6px 14px; }"
            "QPushButton:hover { background: #4a4000; }"
        )
        self._install_addon_btn.clicked.connect(self._install_addon)
        addon_row.addWidget(self._install_addon_btn)
        self._addon_status = QLabel("")
        self._addon_status.setWordWrap(True)
        addon_row.addWidget(self._addon_status, stretch=1)
        path_layout.addRow("", addon_row)

        layout.addWidget(path_group)

        # Language
        lang_group = QGroupBox("Languages")
        lang_layout = QFormLayout(lang_group)

        self._own_lang = QComboBox()
        self._target_lang = QComboBox()
        for code, name in LANGUAGES.items():
            self._own_lang.addItem(f"{name} ({code})", code)
            self._target_lang.addItem(f"{name} ({code})", code)

        self._own_lang.setCurrentIndex(
            self._own_lang.findData(self._config.own_language)
        )
        self._target_lang.setCurrentIndex(
            self._target_lang.findData(self._config.target_language)
        )
        lang_layout.addRow("My language:", self._own_lang)
        lang_layout.addRow("Translate to:", self._target_lang)
        layout.addWidget(lang_group)

        # Channels — 3-column grid
        ch_group = QGroupBox("Channels to translate")
        ch_grid = QGridLayout(ch_group)
        self._ch_party = QCheckBox("Party")
        self._ch_party.setChecked(self._config.channels_party)
        self._ch_raid = QCheckBox("Raid")
        self._ch_raid.setChecked(self._config.channels_raid)
        self._ch_guild = QCheckBox("Guild")
        self._ch_guild.setChecked(self._config.channels_guild)
        self._ch_say = QCheckBox("Say / Yell")
        self._ch_say.setChecked(self._config.channels_say)
        self._ch_whisper = QCheckBox("Whisper")
        self._ch_whisper.setChecked(self._config.channels_whisper)
        self._ch_instance = QCheckBox("Instance")
        self._ch_instance.setChecked(self._config.channels_instance)
        ch_grid.addWidget(self._ch_party, 0, 0)
        ch_grid.addWidget(self._ch_raid, 0, 1)
        ch_grid.addWidget(self._ch_guild, 0, 2)
        ch_grid.addWidget(self._ch_say, 1, 0)
        ch_grid.addWidget(self._ch_whisper, 1, 1)
        ch_grid.addWidget(self._ch_instance, 1, 2)
        layout.addWidget(ch_group)

        layout.addStretch()
        return tab

    # ── API Key Group ────────────────────────────────────────────

    def _create_api_group(self) -> QGroupBox:
        api_group = QGroupBox("DeepL API")
        api_layout = QVBoxLayout(api_group)

        # Row 1: API Key input + Show/Hide
        key_row = QHBoxLayout()
        self._api_key_input = QLineEdit(self._config.deepl_api_key)
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_input.setPlaceholderText("Enter your DeepL API key...")
        key_row.addWidget(self._api_key_input, stretch=1)

        self._show_key_btn = QPushButton("Show")
        self._show_key_btn.setFixedWidth(60)
        self._show_key_btn.setCheckable(True)
        self._show_key_btn.clicked.connect(self._toggle_key_visibility)
        key_row.addWidget(self._show_key_btn)
        api_layout.addLayout(key_row)

        # Row 2: Validate + status + signup link
        action_row = QHBoxLayout()

        self._validate_btn = QPushButton("Validate Key")
        self._validate_btn.clicked.connect(self._validate_api_key)
        action_row.addWidget(self._validate_btn)

        self._api_status_label = QLabel("")
        self._api_status_label.setWordWrap(True)
        action_row.addWidget(self._api_status_label, stretch=1)

        keys_link = QLabel(
            '<a href="https://www.deepl.com/your-account/keys" '
            'style="color: #FFD200;">Get API key</a>'
        )
        keys_link.setOpenExternalLinks(True)
        action_row.addWidget(keys_link)
        api_layout.addLayout(action_row)

        # Row 3: Usage bar (hidden until validated)
        self._usage_widget = QWidget()
        usage_layout = QVBoxLayout(self._usage_widget)
        usage_layout.setContentsMargins(0, 4, 0, 0)

        usage_header = QHBoxLayout()
        usage_title = QLabel("Character Usage")
        usage_title.setStyleSheet("color: #999; font-size: 11px;")
        usage_header.addWidget(usage_title)
        self._usage_detail_label = QLabel("")
        self._usage_detail_label.setStyleSheet("color: #999; font-size: 11px;")
        self._usage_detail_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        usage_header.addWidget(self._usage_detail_label)
        usage_layout.addLayout(usage_header)

        self._usage_bar = QProgressBar()
        self._usage_bar.setRange(0, 100)
        self._usage_bar.setValue(0)
        usage_layout.addWidget(self._usage_bar)

        self._usage_widget.hide()
        api_layout.addWidget(self._usage_widget)

        # Initial state
        self._update_api_status_indicator()

        return api_group

    def _toggle_key_visibility(self, checked: bool) -> None:
        if checked:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._show_key_btn.setText("Hide")
        else:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._show_key_btn.setText("Show")

    def _validate_api_key(self) -> None:
        """Test the API key and show usage stats."""
        key = self._api_key_input.text().strip()
        if not key:
            self._set_api_status("unconfigured", "No API key entered")
            self._usage_widget.hide()
            return

        self._validate_btn.setEnabled(False)
        self._validate_btn.setText("Validating...")
        QApplication.processEvents()

        try:
            translator = deepl.Translator(key)
            usage = translator.get_usage()

            if usage.character and usage.character.valid:
                count = usage.character.count
                limit = usage.character.limit
                pct = int((count / limit) * 100) if limit else 0

                self._usage_bar.setValue(pct)
                self._usage_detail_label.setText(
                    f"{count:,} / {limit:,} characters ({pct}%)"
                )

                if pct >= 90:
                    bar_color = "#FF4040"
                elif pct >= 70:
                    bar_color = "#FF7F00"
                else:
                    bar_color = "#FFD200"
                self._usage_bar.setStyleSheet(
                    f"QProgressBar::chunk {{ background: {bar_color}; border-radius: 3px; }}"
                )

                self._usage_widget.show()
                self._set_api_status("valid", "API key valid")
            else:
                self._set_api_status("valid", "API key valid (no usage data)")
                self._usage_widget.hide()

        except deepl.AuthorizationException:
            self._set_api_status("invalid", "Invalid API key")
            self._usage_widget.hide()
        except Exception as e:
            self._set_api_status("error", f"Connection error: {e}")
            self._usage_widget.hide()
        finally:
            self._validate_btn.setEnabled(True)
            self._validate_btn.setText("Validate Key")

    def _set_api_status(self, state: str, message: str) -> None:
        colors = {
            "unconfigured": "#999",
            "valid": "#40FF40",
            "invalid": "#FF4040",
            "error": "#FF7F00",
        }
        icons = {
            "unconfigured": "\u2022",
            "valid": "\u2713",
            "invalid": "\u2717",
            "error": "\u26A0",
        }
        color = colors.get(state, "#999")
        icon = icons.get(state, "")
        self._api_status_label.setText(f"{icon} {message}")
        self._api_status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

    def _update_api_status_indicator(self) -> None:
        if self._config.deepl_api_key:
            self._set_api_status("unconfigured", "Key saved \u2014 click Validate to check")
        else:
            self._set_api_status("unconfigured", "No API key configured")

    # ── Overlay Tab ──────────────────────────────────────────────

    def _create_overlay_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Appearance
        appear_group = QGroupBox("Appearance")
        appear_layout = QFormLayout(appear_group)

        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(50, 255)
        self._opacity_slider.setValue(self._config.overlay_opacity)
        self._opacity_label = QLabel(
            f"{int(self._config.overlay_opacity / 255 * 100)}%"
        )
        self._opacity_label.setFixedWidth(40)
        self._opacity_slider.valueChanged.connect(
            lambda v: self._opacity_label.setText(f"{int(v / 255 * 100)}%")
        )
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(self._opacity_slider)
        opacity_row.addWidget(self._opacity_label)
        appear_layout.addRow("Opacity:", opacity_row)

        self._font_size = QSpinBox()
        self._font_size.setRange(8, 20)
        self._font_size.setValue(self._config.overlay_font_size)
        appear_layout.addRow("Font size:", self._font_size)

        layout.addWidget(appear_group)

        # Behavior
        behavior_group = QGroupBox("Behavior")
        behavior_layout = QVBoxLayout(behavior_group)

        self._translate_default = QCheckBox("Translation ON by default")
        self._translate_default.setChecked(self._config.translation_enabled_default)
        behavior_layout.addWidget(self._translate_default)

        layout.addWidget(behavior_group)
        layout.addStretch()
        return tab

    # ── Hotkeys Tab ──────────────────────────────────────────────

    def _create_hotkeys_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        hk_group = QGroupBox("Hotkeys")
        hk_layout = QFormLayout(hk_group)

        self._hk_toggle = HotkeyEdit(self._config.hotkey_toggle_translate)
        hk_layout.addRow("Toggle translate:", self._hk_toggle)
        toggle_hint = QLabel("Show/hide translations in the overlay")
        toggle_hint.setStyleSheet("color: #666; font-size: 10px;")
        hk_layout.addRow("", toggle_hint)

        self._hk_interactive = HotkeyEdit(self._config.hotkey_toggle_interactive)
        hk_layout.addRow("Toggle interactive:", self._hk_interactive)
        interactive_hint = QLabel("Switch overlay between click-through and interactive mode")
        interactive_hint.setStyleSheet("color: #666; font-size: 10px;")
        hk_layout.addRow("", interactive_hint)

        self._hk_clipboard = HotkeyEdit(self._config.hotkey_clipboard_translate)
        hk_layout.addRow("Clipboard translate:", self._hk_clipboard)
        clipboard_hint = QLabel("Translate clipboard text and copy result back")
        clipboard_hint.setStyleSheet("color: #666; font-size: 10px;")
        hk_layout.addRow("", clipboard_hint)

        layout.addWidget(hk_group)
        layout.addStretch()
        return tab

    # ── Actions ──────────────────────────────────────────────────

    def _browse_wow_path(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select WoW Directory")
        if path:
            self._wow_path_input.setText(path)

    def _auto_detect_wow(self) -> None:
        detected = detect_wow_path()
        if detected:
            self._wow_path_input.setText(detected)

    def _install_addon(self) -> None:
        wow = self._wow_path_input.text().strip()
        if not wow:
            self._addon_status.setText("\u2717 Set WoW path first")
            self._addon_status.setStyleSheet("color: #FF4040; font-weight: bold;")
            return

        addons_dir = Path(wow) / "_retail_" / "Interface" / "AddOns"
        if not addons_dir.parent.exists():
            self._addon_status.setText(f"\u2717 Not found: {addons_dir.parent}")
            self._addon_status.setStyleSheet("color: #FF4040; font-weight: bold;")
            return

        if getattr(sys, "frozen", False):
            src = Path(sys.executable).parent / "addon" / "ChatTranslatorHelper"
        else:
            src = Path(__file__).resolve().parent.parent / "addon" / "ChatTranslatorHelper"

        if not src.exists():
            self._addon_status.setText("\u2717 Addon files not found")
            self._addon_status.setStyleSheet("color: #FF4040; font-weight: bold;")
            return

        dest = addons_dir / "ChatTranslatorHelper"
        try:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
            self._addon_status.setText(f"\u2713 Installed!")
            self._addon_status.setStyleSheet("color: #40FF40; font-weight: bold;")
            self._install_addon_btn.setText("Reinstall Addon")
        except OSError as e:
            self._addon_status.setText(f"\u2717 {e}")
            self._addon_status.setStyleSheet("color: #FF4040; font-weight: bold;")

    def _save_and_accept(self) -> None:
        self._config.deepl_api_key = self._api_key_input.text().strip()
        self._config.wow_path = self._wow_path_input.text().strip()
        self._config.chatlog_path = self._chatlog_input.text().strip()
        self._config.own_language = self._own_lang.currentData()
        self._config.target_language = self._target_lang.currentData()
        self._config.channels_party = self._ch_party.isChecked()
        self._config.channels_raid = self._ch_raid.isChecked()
        self._config.channels_guild = self._ch_guild.isChecked()
        self._config.channels_say = self._ch_say.isChecked()
        self._config.channels_whisper = self._ch_whisper.isChecked()
        self._config.channels_instance = self._ch_instance.isChecked()
        self._config.overlay_opacity = self._opacity_slider.value()
        self._config.overlay_font_size = self._font_size.value()
        self._config.translation_enabled_default = self._translate_default.isChecked()
        self._config.hotkey_toggle_translate = self._hk_toggle.text()
        self._config.hotkey_toggle_interactive = self._hk_interactive.text()
        self._config.hotkey_clipboard_translate = self._hk_clipboard.text()
        self._config.save()
        self.accept()

    def get_config(self) -> AppConfig:
        return self._config
