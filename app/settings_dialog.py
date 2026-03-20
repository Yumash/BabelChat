"""Settings dialog for BabelChat — WoW-themed dark UI."""

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

from app.about_dialog import VERSION
from app.config import AppConfig, detect_wow_path
from app.i18n import UI_LANGUAGES, tr

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

        self._label = QLabel(current or tr("settings.hk.none"))
        self._label.setStyleSheet(
            "color: #FFD200; font-weight: bold; font-size: 12px; padding: 4px 8px;"
            "background: #111; border: 1px solid #555; border-radius: 3px;"
        )
        self._label.setMinimumWidth(140)
        layout.addWidget(self._label)

        self._btn = QPushButton(tr("settings.hk.change"))
        self._btn.setFixedWidth(90)
        self._btn.clicked.connect(self._start_recording)
        layout.addWidget(self._btn)

        self._clear_btn = QPushButton(tr("settings.hk.clear"))
        self._clear_btn.setFixedWidth(70)
        self._clear_btn.clicked.connect(self._clear)
        layout.addWidget(self._clear_btn)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def text(self) -> str:
        return self._hotkey

    def _start_recording(self) -> None:
        self._recording = True
        self._label.setText(tr("settings.hk.press_keys"))
        self._label.setStyleSheet(
            "color: #40FF40; font-weight: bold; font-size: 12px; padding: 4px 8px;"
            "background: #111; border: 1px solid #40FF40; border-radius: 3px;"
        )
        self._btn.setText(tr("settings.hk.cancel"))
        self._btn.clicked.disconnect()
        self._btn.clicked.connect(self._cancel_recording)
        self.setFocus()

    def _cancel_recording(self) -> None:
        self._recording = False
        self._label.setText(self._hotkey or tr("settings.hk.none"))
        self._label.setStyleSheet(
            "color: #FFD200; font-weight: bold; font-size: 12px; padding: 4px 8px;"
            "background: #111; border: 1px solid #555; border-radius: 3px;"
        )
        self._btn.setText(tr("settings.hk.change"))
        self._btn.clicked.disconnect()
        self._btn.clicked.connect(self._start_recording)

    def _clear(self) -> None:
        self._hotkey = ""
        self._label.setText(tr("settings.hk.none"))
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
        self._btn.setText(tr("settings.hk.change"))
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


_SETTINGS_DIALOG_POS_FILE = "settings_dialog_pos.json"


class SettingsDialog(QDialog):
    """Settings window with WoW-themed dark UI."""

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self.setWindowTitle(tr("settings.title"))
        self.setWindowIcon(_create_dialog_icon())
        self.setMinimumSize(500, 520)
        self.setStyleSheet(WOW_THEME_STYLESHEET)
        self._restore_position()

        layout = QVBoxLayout(self)

        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), tr("settings.tab.general"))
        tabs.addTab(self._create_overlay_tab(), tr("settings.tab.overlay"))
        tabs.addTab(self._create_hotkeys_tab(), tr("settings.tab.hotkeys"))
        tabs.addTab(self._create_about_tab(), tr("settings.tab.about"))
        layout.addWidget(tabs)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)

        # Gold-styled Save button
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText(tr("settings.save"))
        ok_btn.setStyleSheet(
            "QPushButton { background: #3a3000; color: #FFD200; "
            "border: 1px solid #FFD200; border-radius: 3px; padding: 8px 20px; }"
            "QPushButton:hover { background: #4a4000; }"
            "QPushButton:pressed { background: #555; }"
        )

        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setText(tr("wizard.cancel"))

        layout.addWidget(buttons)

    # ── General Tab ──────────────────────────────────────────────

    def _create_general_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # API Key
        layout.addWidget(self._create_api_group())

        # WoW Path
        path_group = QGroupBox(tr("settings.wow_group"))
        path_layout = QFormLayout(path_group)

        wow_row = QHBoxLayout()
        self._wow_path_input = QLineEdit(self._config.wow_path)
        self._wow_path_input.setPlaceholderText("C:/Program Files/World of Warcraft")
        wow_row.addWidget(self._wow_path_input)
        browse_btn = QPushButton(tr("settings.wow.browse"))
        browse_btn.clicked.connect(self._browse_wow_path)
        wow_row.addWidget(browse_btn)
        detect_btn = QPushButton(tr("settings.wow.auto"))
        detect_btn.clicked.connect(self._auto_detect_wow)
        wow_row.addWidget(detect_btn)
        path_layout.addRow(tr("settings.wow.path"), wow_row)

        addon_row = QHBoxLayout()
        self._install_addon_btn = QPushButton(tr("settings.wow.install_addon"))
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
        lang_group = QGroupBox(tr("settings.lang_group"))
        lang_layout = QFormLayout(lang_group)

        self._ui_lang = QComboBox()
        for code, name in UI_LANGUAGES.items():
            self._ui_lang.addItem(name, code)
        self._ui_lang.setCurrentIndex(
            self._ui_lang.findData(self._config.ui_language)
        )
        lang_layout.addRow(tr("settings.lang.ui"), self._ui_lang)

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
        lang_layout.addRow(tr("settings.lang.own"), self._own_lang)
        lang_layout.addRow(tr("settings.lang.target"), self._target_lang)
        layout.addWidget(lang_group)

        # Channels — 3-column grid
        ch_group = QGroupBox(tr("settings.channels_group"))
        ch_grid = QGridLayout(ch_group)
        self._ch_party = QCheckBox(tr("settings.ch.party"))
        self._ch_party.setChecked(self._config.channels_party)
        self._ch_raid = QCheckBox(tr("settings.ch.raid"))
        self._ch_raid.setChecked(self._config.channels_raid)
        self._ch_guild = QCheckBox(tr("settings.ch.guild"))
        self._ch_guild.setChecked(self._config.channels_guild)
        self._ch_say = QCheckBox(tr("settings.ch.say"))
        self._ch_say.setChecked(self._config.channels_say)
        self._ch_whisper = QCheckBox(tr("settings.ch.whisper"))
        self._ch_whisper.setChecked(self._config.channels_whisper)
        self._ch_instance = QCheckBox(tr("settings.ch.instance"))
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
        api_group = QGroupBox(tr("settings.api_group"))
        api_layout = QVBoxLayout(api_group)

        # Row 1: API Key input (always visible)
        self._api_key_input = QLineEdit(self._config.deepl_api_key)
        self._api_key_input.setPlaceholderText(tr("settings.api.placeholder"))
        api_layout.addWidget(self._api_key_input)

        # Row 2: Validate + status + signup link
        action_row = QHBoxLayout()

        self._validate_btn = QPushButton(tr("settings.api.validate"))
        self._validate_btn.clicked.connect(self._validate_api_key)
        action_row.addWidget(self._validate_btn)

        self._api_status_label = QLabel("")
        self._api_status_label.setWordWrap(True)
        action_row.addWidget(self._api_status_label, stretch=1)

        keys_link = QLabel(
            '<a href="https://www.deepl.com/your-account/keys" '
            f'style="color: #FFD200;">{tr("settings.api.get_key")}</a>'
        )
        keys_link.setOpenExternalLinks(True)
        action_row.addWidget(keys_link)
        api_layout.addLayout(action_row)

        # Row 3: Usage bar (hidden until validated)
        self._usage_widget = QWidget()
        usage_layout = QVBoxLayout(self._usage_widget)
        usage_layout.setContentsMargins(0, 4, 0, 0)

        usage_header = QHBoxLayout()
        usage_title = QLabel(tr("settings.api.usage"))
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

    def _validate_api_key(self) -> None:
        """Test the API key and show usage stats."""
        key = self._api_key_input.text().strip()
        if not key:
            self._set_api_status("unconfigured", tr("settings.api.no_key"))
            self._usage_widget.hide()
            return

        self._validate_btn.setEnabled(False)
        self._validate_btn.setText(tr("settings.api.validating"))
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
                    f"{count:,} / {limit:,} ({pct}%)"
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
                self._set_api_status("valid", tr("settings.api.valid"))
            else:
                self._set_api_status("valid", tr("settings.api.valid_no_data"))
                self._usage_widget.hide()

        except deepl.AuthorizationException:
            self._set_api_status("invalid", tr("settings.api.invalid"))
            self._usage_widget.hide()
        except Exception as e:
            self._set_api_status("error", tr("settings.api.error", e=e))
            self._usage_widget.hide()
        finally:
            self._validate_btn.setEnabled(True)
            self._validate_btn.setText(tr("settings.api.validate"))

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
            self._set_api_status("unconfigured", tr("settings.api.saved_hint"))
        else:
            self._set_api_status("unconfigured", tr("settings.api.not_configured"))

    # ── Overlay Tab ──────────────────────────────────────────────

    def _create_overlay_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Appearance
        appear_group = QGroupBox(tr("settings.appearance_group"))
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
        appear_layout.addRow(tr("settings.overlay.opacity"), opacity_row)

        self._font_size = QSpinBox()
        self._font_size.setRange(8, 20)
        self._font_size.setValue(self._config.overlay_font_size)
        appear_layout.addRow(tr("settings.overlay.font_size"), self._font_size)

        layout.addWidget(appear_group)

        # Behavior
        behavior_group = QGroupBox(tr("settings.behavior_group"))
        behavior_layout = QVBoxLayout(behavior_group)

        self._translate_default = QCheckBox(tr("settings.overlay.translate_default"))
        self._translate_default.setChecked(self._config.translation_enabled_default)
        behavior_layout.addWidget(self._translate_default)

        self._skip_own_messages = QCheckBox(tr("settings.overlay.skip_own_messages"))
        self._skip_own_messages.setChecked(self._config.skip_own_messages)
        behavior_layout.addWidget(self._skip_own_messages)

        self._show_console = QCheckBox(tr("settings.overlay.show_console"))
        self._show_console.setChecked(self._config.show_debug_console)
        behavior_layout.addWidget(self._show_console)

        layout.addWidget(behavior_group)
        layout.addStretch()
        return tab

    # ── Hotkeys Tab ──────────────────────────────────────────────

    def _create_hotkeys_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        hk_group = QGroupBox(tr("settings.hk_group"))
        hk_layout = QFormLayout(hk_group)

        self._hk_toggle = HotkeyEdit(self._config.hotkey_toggle_translate)
        hk_layout.addRow(tr("settings.hk.toggle_translate"), self._hk_toggle)
        toggle_hint = QLabel(tr("settings.hk.toggle_translate_hint"))
        toggle_hint.setStyleSheet("color: #666; font-size: 10px;")
        hk_layout.addRow("", toggle_hint)

        self._hk_clipboard = HotkeyEdit(self._config.hotkey_clipboard_translate)
        hk_layout.addRow(tr("settings.hk.clipboard"), self._hk_clipboard)
        clipboard_hint = QLabel(tr("settings.hk.clipboard_hint"))
        clipboard_hint.setStyleSheet("color: #666; font-size: 10px;")
        hk_layout.addRow("", clipboard_hint)

        layout.addWidget(hk_group)
        layout.addStretch()
        return tab

    # ── About Tab ────────────────────────────────────────────────

    def _create_about_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        # Title + version
        title = QLabel(f"BabelChat {VERSION}")
        title.setStyleSheet("color: #FFD200; font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel(tr("about.subtitle"))
        subtitle.setStyleSheet("color: #ccc; font-size: 12px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Developer
        dev = QLabel(f"{tr('about.developer')} <b>Andrey Yumashev</b>")
        dev.setStyleSheet("color: #ccc; font-size: 12px;")
        dev.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(dev)

        # License
        lic = QLabel(tr("about.license"))
        lic.setStyleSheet("color: #999; font-size: 11px;")
        lic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lic)

        # GitHub
        github = QLabel(
            '<a href="https://github.com/Yumash/BabelChat" '
            'style="color: #FFD200;">GitHub: Yumash/BabelChat</a>'
        )
        github.setAlignment(Qt.AlignmentFlag.AlignCenter)
        github.setOpenExternalLinks(True)
        layout.addWidget(github)

        # ── Glossary credit ──
        sep1 = QLabel()
        sep1.setFixedHeight(1)
        sep1.setStyleSheet("background: #444;")
        layout.addWidget(sep1)

        glossary_credit = QLabel(tr("about.glossary_credit"))
        glossary_credit.setStyleSheet("color: #ccc; font-size: 11px;")
        glossary_credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        glossary_credit.setOpenExternalLinks(True)
        glossary_credit.setWordWrap(True)
        layout.addWidget(glossary_credit)

        # ── Donate: Pirson (WoW Dictionary) ──
        sep2 = QLabel()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background: #444;")
        layout.addWidget(sep2)

        dict_donate_title = QLabel(tr("about.donate_dictionary"))
        dict_donate_title.setStyleSheet("color: #FFD200; font-size: 12px; font-weight: bold;")
        dict_donate_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(dict_donate_title)

        dict_donate_desc = QLabel(tr("about.donate_dictionary_desc"))
        dict_donate_desc.setStyleSheet("color: #999; font-size: 11px;")
        dict_donate_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dict_donate_desc.setWordWrap(True)
        layout.addWidget(dict_donate_desc)

        pirson_link = QLabel(
            '<a href="https://buymeacoffee.com/franciscorb" '
            'style="color: #FFD200; font-size: 12px;">'
            'Buy Me a Coffee — Pirson</a>'
        )
        pirson_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pirson_link.setOpenExternalLinks(True)
        layout.addWidget(pirson_link)

        # ── Donate: Companion App ──
        sep3 = QLabel()
        sep3.setFixedHeight(1)
        sep3.setStyleSheet("background: #444;")
        layout.addWidget(sep3)

        app_donate_title = QLabel(tr("about.donate_app"))
        app_donate_title.setStyleSheet("color: #FFD200; font-size: 12px; font-weight: bold;")
        app_donate_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(app_donate_title)

        app_donate_desc = QLabel(tr("about.donate_app_desc"))
        app_donate_desc.setStyleSheet("color: #999; font-size: 11px;")
        app_donate_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_donate_desc.setWordWrap(True)
        layout.addWidget(app_donate_desc)

        for label, addr in [
            ("USDT TRC20", "TGaUz963ZaCoHrfoDDgy1sCvSrK1wsZvcx"),
            ("BTC", "1BkYvFT8iBVG3GfTqkR2aBkABNkTrhYuja"),
            ("TON", "UQDFaHBN1pcQZ7_9-w1E_hS_JNfGf3d0flS_467w7LOQ7xbK"),
        ]:
            row = QHBoxLayout()
            crypto_label = QLabel(f"<b>{label}:</b>")
            crypto_label.setStyleSheet("color: #ccc; font-size: 11px;")
            crypto_label.setFixedWidth(90)
            row.addWidget(crypto_label)

            addr_field = QLineEdit(addr)
            addr_field.setReadOnly(True)
            addr_field.setStyleSheet(
                "color: #e0e0e0; font-size: 10px; background: #111; "
                "border: 1px solid #444; border-radius: 3px; padding: 4px;"
            )
            row.addWidget(addr_field)

            copy_btn = QPushButton(tr("overlay.reply.copy"))
            copy_btn.setFixedWidth(80)
            copy_btn.clicked.connect(
                lambda checked, a=addr: QApplication.clipboard().setText(a)
            )
            row.addWidget(copy_btn)
            layout.addLayout(row)

        layout.addStretch()
        return tab

    # ── Actions ──────────────────────────────────────────────────

    def _browse_wow_path(self) -> None:
        path = QFileDialog.getExistingDirectory(self, tr("settings.wow.browse_title"))
        if path:
            self._wow_path_input.setText(path)

    def _auto_detect_wow(self) -> None:
        detected = detect_wow_path()
        if detected:
            self._wow_path_input.setText(detected)

    def _install_addon(self) -> None:
        wow = self._wow_path_input.text().strip()
        if not wow:
            self._addon_status.setText(tr("settings.wow.addon_no_path"))
            self._addon_status.setStyleSheet("color: #FF4040; font-weight: bold;")
            return

        addons_dir = Path(wow) / "_retail_" / "Interface" / "AddOns"
        if not addons_dir.parent.exists():
            self._addon_status.setText(
                tr("settings.wow.addon_not_found", path=addons_dir.parent)
            )
            self._addon_status.setStyleSheet("color: #FF4040; font-weight: bold;")
            return

        if getattr(sys, "frozen", False):
            src = Path(getattr(sys, "_MEIPASS", "")) / "addon" / "BabelChat"
        else:
            src = Path(__file__).resolve().parent.parent / "addon" / "BabelChat"

        if not src.exists():
            self._addon_status.setText(tr("settings.wow.addon_files_missing"))
            self._addon_status.setStyleSheet("color: #FF4040; font-weight: bold;")
            return

        dest = addons_dir / "BabelChat"
        try:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
            self._addon_status.setText(tr("settings.wow.addon_installed"))
            self._addon_status.setStyleSheet("color: #40FF40; font-weight: bold;")
            self._install_addon_btn.setText(tr("settings.wow.reinstall_addon"))
        except OSError as e:
            self._addon_status.setText(f"\u2717 {e}")
            self._addon_status.setStyleSheet("color: #FF4040; font-weight: bold;")

    def _save_and_accept(self) -> None:
        self._config.deepl_api_key = self._api_key_input.text().strip()
        self._config.wow_path = self._wow_path_input.text().strip()
        self._config.ui_language = self._ui_lang.currentData()
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
        self._config.skip_own_messages = self._skip_own_messages.isChecked()
        self._config.show_debug_console = self._show_console.isChecked()
        self._config.hotkey_toggle_translate = self._hk_toggle.text()
        self._config.hotkey_clipboard_translate = self._hk_clipboard.text()
        # Apply UI language change
        new_lang = self._ui_lang.currentData()
        if new_lang != tr.get_language():
            tr.set_language(new_lang)
        self._config.save()
        self.accept()

    def _restore_position(self) -> None:
        import json
        try:
            data = json.loads(Path(_SETTINGS_DIALOG_POS_FILE).read_text(encoding="utf-8"))
            self.move(data.get("x", 200), data.get("y", 200))
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass

    def _save_position(self) -> None:
        import contextlib
        import json
        with contextlib.suppress(OSError):
            data = {"x": self.x(), "y": self.y()}
            Path(_SETTINGS_DIALOG_POS_FILE).write_text(
                json.dumps(data), encoding="utf-8"
            )

    def closeEvent(self, event: object) -> None:
        self._save_position()
        super().closeEvent(event)  # type: ignore[arg-type]

    def get_config(self) -> AppConfig:
        return self._config
