"""Settings dialog for WoWTranslator."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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


class SettingsDialog(QDialog):
    """Settings window with tabs for General, Overlay, and Hotkeys."""

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("WoWTranslator Settings")
        self.setMinimumSize(450, 400)

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
        layout.addWidget(buttons)

    def _create_general_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # API Key
        api_group = QGroupBox("DeepL API")
        api_layout = QFormLayout(api_group)
        self._api_key_input = QLineEdit(self._config.deepl_api_key)
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("API Key:", self._api_key_input)
        layout.addWidget(api_group)

        # WoW Path
        path_group = QGroupBox("World of Warcraft")
        path_layout = QFormLayout(path_group)

        wow_row = QHBoxLayout()
        self._wow_path_input = QLineEdit(self._config.wow_path)
        wow_row.addWidget(self._wow_path_input)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_wow_path)
        wow_row.addWidget(browse_btn)
        detect_btn = QPushButton("Auto")
        detect_btn.clicked.connect(self._auto_detect_wow)
        wow_row.addWidget(detect_btn)
        path_layout.addRow("WoW Path:", wow_row)

        self._chatlog_input = QLineEdit(self._config.chatlog_path)
        path_layout.addRow("Chat Log:", self._chatlog_input)
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

        # Channels
        ch_group = QGroupBox("Channels to translate")
        ch_layout = QVBoxLayout(ch_group)
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
        for cb in (self._ch_party, self._ch_raid, self._ch_guild,
                   self._ch_say, self._ch_whisper, self._ch_instance):
            ch_layout.addWidget(cb)
        layout.addWidget(ch_group)

        layout.addStretch()
        return tab

    def _create_overlay_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Opacity
        opacity_group = QGroupBox("Overlay")
        opacity_layout = QFormLayout(opacity_group)

        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(50, 255)
        self._opacity_slider.setValue(self._config.overlay_opacity)
        self._opacity_label = QLabel(str(self._config.overlay_opacity))
        self._opacity_slider.valueChanged.connect(
            lambda v: self._opacity_label.setText(str(v))
        )
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(self._opacity_slider)
        opacity_row.addWidget(self._opacity_label)
        opacity_layout.addRow("Opacity:", opacity_row)

        self._font_size = QSpinBox()
        self._font_size.setRange(8, 20)
        self._font_size.setValue(self._config.overlay_font_size)
        opacity_layout.addRow("Font size:", self._font_size)

        self._translate_default = QCheckBox("Translation ON by default")
        self._translate_default.setChecked(self._config.translation_enabled_default)
        opacity_layout.addRow(self._translate_default)

        layout.addWidget(opacity_group)
        layout.addStretch()
        return tab

    def _create_hotkeys_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        hk_group = QGroupBox("Hotkeys")
        hk_layout = QFormLayout(hk_group)

        self._hk_toggle = QLineEdit(self._config.hotkey_toggle_translate)
        hk_layout.addRow("Toggle translate:", self._hk_toggle)

        self._hk_interactive = QLineEdit(self._config.hotkey_toggle_interactive)
        hk_layout.addRow("Toggle interactive:", self._hk_interactive)

        self._hk_clipboard = QLineEdit(self._config.hotkey_clipboard_translate)
        hk_layout.addRow("Clipboard translate:", self._hk_clipboard)

        layout.addWidget(hk_group)
        layout.addStretch()
        return tab

    def _browse_wow_path(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select WoW Directory")
        if path:
            self._wow_path_input.setText(path)

    def _auto_detect_wow(self) -> None:
        detected = detect_wow_path()
        if detected:
            self._wow_path_input.setText(detected)

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
        self._config.hotkey_toggle_translate = self._hk_toggle.text().strip()
        self._config.hotkey_toggle_interactive = self._hk_interactive.text().strip()
        self._config.hotkey_clipboard_translate = self._hk_clipboard.text().strip()
        self._config.save()
        self.accept()

    def get_config(self) -> AppConfig:
        return self._config
