"""First-run setup wizard for WoWTranslator — WoW-themed."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import deepl
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.about_dialog import _create_logo_pixmap
from app.config import AppConfig, detect_wow_path
from app.settings_dialog import (
    LANGUAGES,
    WOW_THEME_STYLESHEET,
    _create_dialog_icon,
)

PAGE_WELCOME = 0
PAGE_API_KEY = 1
PAGE_WOW_PATH = 2
PAGE_LANGUAGE = 3
PAGE_READY = 4
TOTAL_PAGES = 5

_STEP_NAMES = ["Welcome", "API Key", "WoW Path", "Language", "Ready"]

# Gold-styled primary action button
_GOLD_BTN_STYLE = (
    "QPushButton { background: #3a3000; color: #FFD200; "
    "border: 1px solid #FFD200; border-radius: 3px; padding: 8px 20px; }"
    "QPushButton:hover { background: #4a4000; }"
    "QPushButton:pressed { background: #555; }"
    "QPushButton:disabled { background: #222; color: #666; "
    "border-color: #444; }"
)


class SetupWizard(QDialog):
    """First-run setup wizard with WoW-themed dark UI."""

    def __init__(
        self, config: AppConfig, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("WoWTranslator Setup")
        self.setWindowIcon(_create_dialog_icon())
        self.setMinimumSize(550, 480)
        self.setStyleSheet(WOW_THEME_STYLESHEET)

        main_layout = QVBoxLayout(self)

        # Step indicator
        main_layout.addWidget(self._create_step_indicator())
        main_layout.addWidget(self._separator())

        # Stacked pages
        self._stack = QStackedWidget()
        self._stack.addWidget(self._create_welcome_page())
        self._stack.addWidget(self._create_api_key_page())
        self._stack.addWidget(self._create_wow_path_page())
        self._stack.addWidget(self._create_language_page())
        self._stack.addWidget(self._create_ready_page())
        main_layout.addWidget(self._stack, stretch=1)

        # Navigation
        main_layout.addWidget(self._separator())
        nav = QHBoxLayout()

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)
        nav.addWidget(self._cancel_btn)
        nav.addStretch()

        self._back_btn = QPushButton("\u2190 Back")
        self._back_btn.clicked.connect(self._go_back)
        nav.addWidget(self._back_btn)

        self._next_btn = QPushButton("Next \u2192")
        self._next_btn.setStyleSheet(_GOLD_BTN_STYLE)
        self._next_btn.clicked.connect(self._go_next)
        nav.addWidget(self._next_btn)

        main_layout.addLayout(nav)
        self._update_navigation()

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _separator() -> QLabel:
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #444;")
        return sep

    # ── Step indicator ────────────────────────────────────────────

    def _create_step_indicator(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 8, 12, 8)

        self._step_dots: list[QLabel] = []
        for _ in range(TOTAL_PAGES):
            dot = QLabel()
            dot.setFixedSize(12, 12)
            layout.addWidget(dot)
            self._step_dots.append(dot)

        layout.addSpacing(8)
        self._step_text = QLabel("")
        self._step_text.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(self._step_text)
        layout.addStretch()
        return widget

    def _update_step_indicator(self) -> None:
        current = self._stack.currentIndex()
        for i, dot in enumerate(self._step_dots):
            if i < current:
                dot.setStyleSheet(
                    "background: #997D00; border-radius: 6px;"
                )
            elif i == current:
                dot.setStyleSheet(
                    "background: #FFD200; border-radius: 6px;"
                )
            else:
                dot.setStyleSheet(
                    "background: #555; border-radius: 6px;"
                )

        name = _STEP_NAMES[current]
        self._step_text.setText(
            f"Step {current + 1} of {TOTAL_PAGES} \u2014 {name}"
        )

    # ── Page 1: Welcome ──────────────────────────────────────────

    def _create_welcome_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch()

        # Logo
        logo = QLabel()
        logo.setPixmap(_create_logo_pixmap())
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        layout.addSpacing(12)

        # Title
        title = QLabel("Welcome to WoWTranslator!")
        title.setStyleSheet(
            "color: #FFD200; font-size: 22px; font-weight: bold;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(8)

        # Description
        desc = QLabel(
            "WoWTranslator is a companion app that translates\n"
            "World of Warcraft chat in real time.\n\n"
            "How it works:\n"
            "1. A tiny WoW addon enables chat logging\n"
            "2. This app monitors the chat log file\n"
            "3. Messages are auto-detected and translated via DeepL\n"
            "4. Translations appear in a smart overlay on top of WoW\n\n"
            "Let's set it up!"
        )
        desc.setStyleSheet("color: #ccc; font-size: 13px;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addStretch()
        return page

    # ── Page 2: DeepL API Key ────────────────────────────────────

    def _create_api_key_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("DeepL API Key")
        title.setStyleSheet(
            "color: #FFD200; font-size: 16px; font-weight: bold;"
        )
        layout.addWidget(title)

        layout.addSpacing(4)

        explain = QLabel(
            "WoWTranslator uses DeepL \u2014 one of the best translation "
            "services available.\nThe free plan includes 500,000 characters "
            "per month (that's a LOT of chat)."
        )
        explain.setStyleSheet("color: #ccc; font-size: 12px;")
        explain.setWordWrap(True)
        layout.addWidget(explain)

        layout.addSpacing(8)

        steps = QLabel(
            "To get your free API key:\n\n"
            "  1. Click the link below to sign up at DeepL\n"
            "  2. Create a free account (DeepL API Free plan)\n"
            "  3. After signup, go to your API Keys page\n"
            "     (click the second link below)\n"
            "  4. Copy your key (looks like: xxxxxxxx-xxxx-...:fx)\n"
            "  5. Paste it in the field below"
        )
        steps.setStyleSheet("color: #e0e0e0; font-size: 12px;")
        steps.setWordWrap(True)
        layout.addWidget(steps)

        layout.addSpacing(8)

        # Links
        signup = QLabel(
            '<a href="https://www.deepl.com/pro-api" '
            'style="color: #FFD200; font-size: 12px;">'
            "\u2192 1. Sign up at DeepL (free)</a>"
        )
        signup.setOpenExternalLinks(True)
        layout.addWidget(signup)

        keys_link = QLabel(
            '<a href="https://www.deepl.com/your-account/keys" '
            'style="color: #FFD200; font-size: 12px;">'
            "\u2192 2. Open API Keys page (after signup)</a>"
        )
        keys_link.setOpenExternalLinks(True)
        layout.addWidget(keys_link)

        layout.addSpacing(12)

        # API Key input + Show/Hide
        key_row = QHBoxLayout()
        self._api_key_input = QLineEdit(self._config.deepl_api_key)
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_input.setPlaceholderText(
            "Paste your DeepL API key here..."
        )
        self._api_key_input.textChanged.connect(self._on_api_key_changed)
        key_row.addWidget(self._api_key_input, stretch=1)

        self._show_key_btn = QPushButton("Show")
        self._show_key_btn.setFixedWidth(60)
        self._show_key_btn.setCheckable(True)
        self._show_key_btn.clicked.connect(self._toggle_key_visibility)
        key_row.addWidget(self._show_key_btn)
        layout.addLayout(key_row)

        # Validate + status
        action_row = QHBoxLayout()
        self._validate_btn = QPushButton("Validate Key")
        self._validate_btn.clicked.connect(self._validate_api_key)
        action_row.addWidget(self._validate_btn)

        self._api_status_label = QLabel("")
        self._api_status_label.setWordWrap(True)
        action_row.addWidget(self._api_status_label, stretch=1)
        layout.addLayout(action_row)

        layout.addStretch()
        return page

    def _on_api_key_changed(self, text: str) -> None:
        if self._stack.currentIndex() == PAGE_API_KEY:
            self._next_btn.setEnabled(bool(text.strip()))

    def _toggle_key_visibility(self, checked: bool) -> None:
        if checked:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._show_key_btn.setText("Hide")
        else:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._show_key_btn.setText("Show")

    def _validate_api_key(self) -> None:
        key = self._api_key_input.text().strip()
        if not key:
            self._set_api_status("unconfigured", "No API key entered")
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
                self._set_api_status(
                    "valid",
                    f"Key valid! Usage: {count:,} / {limit:,} ({pct}%)",
                )
            else:
                self._set_api_status("valid", "API key valid!")
        except deepl.AuthorizationException:
            self._set_api_status("invalid", "Invalid API key")
        except Exception as e:
            self._set_api_status("error", f"Connection error: {e}")
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
        self._api_status_label.setStyleSheet(
            f"color: {color}; font-weight: bold;"
        )

    # ── Page 3: WoW Path ─────────────────────────────────────────

    def _create_wow_path_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("World of Warcraft Location")
        title.setStyleSheet(
            "color: #FFD200; font-size: 16px; font-weight: bold;"
        )
        layout.addWidget(title)

        layout.addSpacing(4)

        explain = QLabel(
            "We need to find your WoW installation to monitor\n"
            "the chat log file. We'll try to detect it automatically."
        )
        explain.setStyleSheet("color: #ccc; font-size: 12px;")
        explain.setWordWrap(True)
        layout.addWidget(explain)

        layout.addSpacing(12)

        # Path input + Browse
        path_row = QHBoxLayout()
        self._wow_path_input = QLineEdit(self._config.wow_path)
        self._wow_path_input.setPlaceholderText(
            "C:/Program Files/World of Warcraft"
        )
        path_row.addWidget(self._wow_path_input, stretch=1)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_wow_path)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        # Status
        self._wow_status_label = QLabel("")
        self._wow_status_label.setWordWrap(True)
        layout.addWidget(self._wow_status_label)

        layout.addSpacing(8)

        hint = QLabel(
            "You can skip this step and configure it later\n"
            "in Settings."
        )
        hint.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(hint)

        layout.addStretch()
        return page

    def _auto_detect_wow(self) -> None:
        detected = detect_wow_path()
        if detected:
            self._wow_path_input.setText(detected)
            self._wow_status_label.setText(
                "\u2713 WoW installation found!"
            )
            self._wow_status_label.setStyleSheet(
                "color: #40FF40; font-weight: bold;"
            )
        else:
            self._wow_status_label.setText(
                "\u26A0 WoW not found automatically. "
                "Please browse to your installation, "
                "or skip and configure later."
            )
            self._wow_status_label.setStyleSheet(
                "color: #FF7F00; font-weight: bold;"
            )

    def _browse_wow_path(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Select WoW Directory"
        )
        if path:
            self._wow_path_input.setText(path)
            self._wow_status_label.setText("\u2713 Path set")
            self._wow_status_label.setStyleSheet(
                "color: #40FF40; font-weight: bold;"
            )

    # ── Page 4: Language ──────────────────────────────────────────

    def _create_language_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Choose Your Languages")
        title.setStyleSheet(
            "color: #FFD200; font-size: 16px; font-weight: bold;"
        )
        layout.addWidget(title)

        layout.addSpacing(8)

        own_label = QLabel("What language do you speak?")
        own_label.setStyleSheet("color: #ccc; font-size: 13px;")
        layout.addWidget(own_label)

        self._own_lang = QComboBox()
        for code, name in LANGUAGES.items():
            self._own_lang.addItem(f"{name} ({code})", code)
        self._own_lang.setCurrentIndex(
            self._own_lang.findData(self._config.own_language)
        )
        layout.addWidget(self._own_lang)

        layout.addSpacing(12)

        target_label = QLabel("Translate messages to:")
        target_label.setStyleSheet("color: #ccc; font-size: 13px;")
        layout.addWidget(target_label)

        self._target_lang = QComboBox()
        for code, name in LANGUAGES.items():
            self._target_lang.addItem(f"{name} ({code})", code)
        self._target_lang.setCurrentIndex(
            self._target_lang.findData(self._config.target_language)
        )
        layout.addWidget(self._target_lang)

        layout.addSpacing(12)

        hint = QLabel(
            "Messages in your language won't be translated.\n"
            "Everything else will be translated to your target language."
        )
        hint.setStyleSheet("color: #999; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch()
        return page

    # ── Page 5: Ready ─────────────────────────────────────────────

    def _create_ready_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch()

        title = QLabel("\u2713 You're all set!")
        title.setStyleSheet(
            "color: #FFD200; font-size: 20px; font-weight: bold;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(8)

        self._summary_label = QLabel("")
        self._summary_label.setStyleSheet("color: #ccc; font-size: 12px;")
        self._summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._summary_label.setWordWrap(True)
        layout.addWidget(self._summary_label)

        layout.addSpacing(12)

        # Addon install
        addon_group = QGroupBox("WoW Addon")
        addon_layout = QVBoxLayout(addon_group)
        addon_text = QLabel(
            "The tiny addon auto-enables chat logging so the "
            "translator can read your messages."
        )
        addon_text.setWordWrap(True)
        addon_text.setStyleSheet("color: #ccc; font-size: 12px;")
        addon_layout.addWidget(addon_text)

        addon_layout.addSpacing(4)

        self._install_addon_btn = QPushButton("Install Addon")
        self._install_addon_btn.setStyleSheet(_GOLD_BTN_STYLE)
        self._install_addon_btn.clicked.connect(self._install_addon)
        addon_layout.addWidget(self._install_addon_btn)

        self._addon_status_label = QLabel("")
        self._addon_status_label.setWordWrap(True)
        addon_layout.addWidget(self._addon_status_label)

        layout.addWidget(addon_group)

        layout.addSpacing(8)

        closing = QLabel(
            "The overlay will appear on top of WoW.\n"
            "Right-click the tray icon to access Settings and About."
        )
        closing.setStyleSheet("color: #999; font-size: 11px;")
        closing.setAlignment(Qt.AlignmentFlag.AlignCenter)
        closing.setWordWrap(True)
        layout.addWidget(closing)

        layout.addStretch()
        return page

    @staticmethod
    def _addon_source_path() -> Path:
        """Return path to bundled ChatTranslatorHelper addon folder."""
        if getattr(sys, "frozen", False):
            # PyInstaller bundle
            base = Path(sys.executable).parent
        else:
            base = Path(__file__).resolve().parent.parent
        return base / "addon" / "ChatTranslatorHelper"

    def _install_addon(self) -> None:
        wow = self._wow_path_input.text().strip()
        if not wow:
            self._addon_status_label.setText(
                "\u2717 WoW path not set — go back and configure it"
            )
            self._addon_status_label.setStyleSheet(
                "color: #FF4040; font-weight: bold;"
            )
            return

        addons_dir = Path(wow) / "_retail_" / "Interface" / "AddOns"
        if not addons_dir.parent.exists():
            self._addon_status_label.setText(
                f"\u2717 Path not found: {addons_dir.parent}"
            )
            self._addon_status_label.setStyleSheet(
                "color: #FF4040; font-weight: bold;"
            )
            return

        src = self._addon_source_path()
        if not src.exists():
            self._addon_status_label.setText(
                "\u2717 Addon files not found in app directory"
            )
            self._addon_status_label.setStyleSheet(
                "color: #FF4040; font-weight: bold;"
            )
            return

        dest = addons_dir / "ChatTranslatorHelper"
        try:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
            self._addon_status_label.setText(
                f"\u2713 Installed to {dest}"
            )
            self._addon_status_label.setStyleSheet(
                "color: #40FF40; font-weight: bold;"
            )
            self._install_addon_btn.setText("Reinstall Addon")
        except OSError as e:
            self._addon_status_label.setText(f"\u2717 {e}")
            self._addon_status_label.setStyleSheet(
                "color: #FF4040; font-weight: bold;"
            )

    def _update_summary(self) -> None:
        key = self._api_key_input.text().strip()
        masked = f"****{key[-4:]}" if len(key) >= 4 else "****"
        own = LANGUAGES.get(self._own_lang.currentData(), "?")
        target = LANGUAGES.get(self._target_lang.currentData(), "?")
        wow = self._wow_path_input.text() or "(not configured)"

        self._summary_label.setText(
            f"<b>API Key:</b> {masked}<br>"
            f"<b>WoW Path:</b> {wow}<br>"
            f"<b>Your language:</b> {own}<br>"
            f"<b>Translate to:</b> {target}"
        )

    # ── Navigation ────────────────────────────────────────────────

    def _go_next(self) -> None:
        current = self._stack.currentIndex()
        if current == TOTAL_PAGES - 1:
            self._finish()
            return
        self._stack.setCurrentIndex(current + 1)
        self._on_page_entered(current + 1)
        self._update_navigation()

    def _go_back(self) -> None:
        current = self._stack.currentIndex()
        if current > 0:
            self._stack.setCurrentIndex(current - 1)
            self._on_page_entered(current - 1)
            self._update_navigation()

    def _on_page_entered(self, index: int) -> None:
        if index == PAGE_WOW_PATH:
            if not self._wow_path_input.text().strip():
                self._auto_detect_wow()
        elif index == PAGE_READY:
            self._update_summary()

    def _update_navigation(self) -> None:
        current = self._stack.currentIndex()

        self._back_btn.setVisible(current > 0)

        if current == TOTAL_PAGES - 1:
            self._next_btn.setText("Start \u2713")
        else:
            self._next_btn.setText("Next \u2192")

        if current == PAGE_API_KEY:
            self._next_btn.setEnabled(
                bool(self._api_key_input.text().strip())
            )
        else:
            self._next_btn.setEnabled(True)

        self._update_step_indicator()

    # ── Finalization ──────────────────────────────────────────────

    def _finish(self) -> None:
        self._config.deepl_api_key = self._api_key_input.text().strip()
        self._config.wow_path = self._wow_path_input.text().strip()
        self._config.own_language = self._own_lang.currentData()
        self._config.target_language = self._target_lang.currentData()
        self._config.save()
        self.accept()

    def get_config(self) -> AppConfig:
        return self._config
