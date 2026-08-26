"""First-run setup wizard for BabelChat — WoW-themed."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import AppConfig, detect_wow_path
from app.i18n import tr
from app.provider_settings_qt import ProviderSettingsGroup
from app.qt_widgets import scrollable, size_to_content
from app.settings_dialog import (
    LANGUAGES,
    WOW_THEME_STYLESHEET,
    _create_dialog_icon,
)
from app.translators import all_providers
from app.translators import get as provider_get
from app.wizard_pages_qt import build_ready_page, build_welcome_page
from app.wizard_style import GOLD_BTN_STYLE as _GOLD_BTN_STYLE

PAGE_WELCOME = 0
PAGE_API_KEY = 1
PAGE_WOW_PATH = 2
PAGE_LANGUAGE = 3
PAGE_READY = 4
TOTAL_PAGES = 5

# Gold-styled primary action button


class SetupWizard(QDialog):
    """First-run setup wizard with WoW-themed dark UI."""

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self.setWindowTitle(tr("wizard.title"))
        self.setWindowIcon(_create_dialog_icon())
        # Small enough for any screen; the pages scroll.
        self.setMinimumSize(550, 480)
        self.setStyleSheet(WOW_THEME_STYLESHEET)

        main_layout = QVBoxLayout(self)

        # Step indicator
        main_layout.addWidget(self._create_step_indicator())
        main_layout.addWidget(self._separator())

        # Stacked pages
        self._stack = QStackedWidget()
        # Every page behind a scroll area. The provider page alone needs more
        # height than a laptop screen once there are four services to fill in,
        # and a stack page that cannot scroll gets squeezed instead: the
        # credential fields rendered at 6px against a 32px minimum and the
        # Validate buttons came out as blank slivers. On step 2 of 5, on every
        # fresh install.
        self._stack.addWidget(scrollable(self._create_welcome_page()))
        self._stack.addWidget(scrollable(self._create_api_key_page()))
        self._stack.addWidget(scrollable(self._create_wow_path_page()))
        self._stack.addWidget(scrollable(self._create_language_page()))
        self._stack.addWidget(scrollable(self._create_ready_page()))
        main_layout.addWidget(self._stack, stretch=1)

        # Navigation
        main_layout.addWidget(self._separator())
        nav = QHBoxLayout()

        self._cancel_btn = QPushButton(tr("wizard.cancel"))
        self._cancel_btn.clicked.connect(self.reject)
        nav.addWidget(self._cancel_btn)
        nav.addStretch()

        self._back_btn = QPushButton(tr("wizard.back"))
        self._back_btn.clicked.connect(self._go_back)
        nav.addWidget(self._back_btn)

        self._next_btn = QPushButton(tr("wizard.next"))
        self._next_btn.setStyleSheet(_GOLD_BTN_STYLE)
        self._next_btn.clicked.connect(self._go_next)
        nav.addWidget(self._next_btn)

        main_layout.addLayout(nav)
        self._update_navigation()
        size_to_content(self)

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
                dot.setStyleSheet("background: #997D00; border-radius: 6px;")
            elif i == current:
                dot.setStyleSheet("background: #FFD200; border-radius: 6px;")
            else:
                dot.setStyleSheet("background: #555; border-radius: 6px;")

        step_names = tr("wizard.steps").split("|")
        name = step_names[current] if current < len(step_names) else ""
        self._step_text.setText(tr("wizard.step_of", current=current + 1, total=TOTAL_PAGES, name=name))

    # ── Page 1: Welcome ──────────────────────────────────────────

    def _create_welcome_page(self) -> QWidget:
        return build_welcome_page(self)

    def _on_ui_lang_changed(self) -> None:
        lang = self._ui_lang_combo.currentData()
        if lang and lang != tr.get_language():
            tr.set_language(lang)
            self._config.ui_language = lang
            # Everything typed so far goes into the config first. Restarting is
            # how this wizard changes language, and the new one builds its
            # fields from the config — so anything not written here is simply
            # gone: an API key pasted on page two, the WoW path browsed for on
            # page three. Same two calls _finish makes, for the same reason.
            self._provider_group.apply_to(self._config)
            self._config.wow_path = self._wow_path_input.text().strip()
            # Signal main to restart wizard with new language
            self._restart_requested = True
            self.done(2)  # Custom result code: restart

    # ── Page 2: DeepL API Key ────────────────────────────────────

    def _create_api_key_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel(tr("wizard.api.title"))
        title.setStyleSheet("color: #FFD200; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        layout.addSpacing(4)

        explain = QLabel(
            tr("wizard.api.explain")
        )
        explain.setStyleSheet("color: #ccc; font-size: 12px;")
        explain.setWordWrap(True)
        layout.addWidget(explain)

        layout.addSpacing(10)

        self._provider_group = ProviderSettingsGroup(self._config, page)
        layout.addWidget(self._provider_group)

        layout.addStretch()
        return page


    def _validate_api_key(self) -> None:
        self._validate_deepl_key()

    # ── Page 3: WoW Path ─────────────────────────────────────────

    def _create_wow_path_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel(tr("wizard.wow.title"))
        title.setStyleSheet("color: #FFD200; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        layout.addSpacing(4)

        explain = QLabel(tr("wizard.wow.explain"))
        explain.setStyleSheet("color: #ccc; font-size: 12px;")
        explain.setWordWrap(True)
        layout.addWidget(explain)

        layout.addSpacing(12)

        # Path input + Browse
        path_row = QHBoxLayout()
        self._wow_path_input = QLineEdit(self._config.wow_path)
        self._wow_path_input.setPlaceholderText("C:/Program Files/World of Warcraft")
        path_row.addWidget(self._wow_path_input, stretch=1)

        browse_btn = QPushButton(tr("wizard.wow.browse"))
        browse_btn.clicked.connect(self._browse_wow_path)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        # Status
        self._wow_status_label = QLabel("")
        self._wow_status_label.setWordWrap(True)
        layout.addWidget(self._wow_status_label)

        layout.addSpacing(8)

        hint = QLabel(tr("wizard.wow.skip_hint"))
        hint.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(hint)

        layout.addStretch()
        return page

    def _auto_detect_wow(self) -> None:
        import sys

        if sys.platform != "win32":
            # On Linux, auto-detection is unreliable — open the file browser directly
            self._browse_wow_path()
            return
        detected = detect_wow_path()
        if detected:
            self._wow_path_input.setText(detected)
            self._wow_status_label.setText(tr("wizard.wow.found"))
            self._wow_status_label.setStyleSheet("color: #40FF40; font-weight: bold;")
        else:
            self._wow_status_label.setText(tr("wizard.wow.not_found"))
            self._wow_status_label.setStyleSheet("color: #FF7F00; font-weight: bold;")

    def _browse_wow_path(self) -> None:
        path = QFileDialog.getExistingDirectory(self, tr("wizard.wow.browse_title"))
        if path:
            self._wow_path_input.setText(path)
            self._wow_status_label.setText(tr("wizard.wow.path_set"))
            self._wow_status_label.setStyleSheet("color: #40FF40; font-weight: bold;")

    # ── Page 4: Language ──────────────────────────────────────────

    def _create_language_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel(tr("wizard.lang.title"))
        title.setStyleSheet("color: #FFD200; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        layout.addSpacing(8)

        own_label = QLabel(tr("wizard.lang.own"))
        own_label.setStyleSheet("color: #ccc; font-size: 13px;")
        layout.addWidget(own_label)

        self._own_lang = QComboBox()
        for code, name in LANGUAGES.items():
            self._own_lang.addItem(f"{name} ({code})", code)
        self._own_lang.setCurrentIndex(self._own_lang.findData(self._config.own_language))
        layout.addWidget(self._own_lang)

        layout.addSpacing(12)

        target_label = QLabel(tr("wizard.lang.target"))
        target_label.setStyleSheet("color: #ccc; font-size: 13px;")
        layout.addWidget(target_label)

        self._target_lang = QComboBox()
        for code, name in LANGUAGES.items():
            self._target_lang.addItem(f"{name} ({code})", code)
        self._target_lang.setCurrentIndex(self._target_lang.findData(self._config.target_language))
        layout.addWidget(self._target_lang)

        layout.addSpacing(12)

        hint = QLabel(tr("wizard.lang.hint"))
        hint.setStyleSheet("color: #999; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch()
        return page

    # ── Page 5: Ready ─────────────────────────────────────────────

    def _create_ready_page(self) -> QWidget:
        return build_ready_page(self)

    @staticmethod
    def _addon_source_path() -> Path:
        """Return path to bundled BabelChat addon folder."""
        if getattr(sys, "frozen", False):
            # PyInstaller onefile: data extracted to _MEIPASS temp dir
            base = Path(getattr(sys, "_MEIPASS", ""))
        else:
            base = Path(__file__).resolve().parent.parent
        return base / "addon" / "BabelChat"

    def _install_addon(self) -> None:
        wow = self._wow_path_input.text().strip()
        if not wow:
            self._addon_status_label.setText(tr("wizard.ready.addon_no_path"))
            self._addon_status_label.setStyleSheet("color: #FF4040; font-weight: bold;")
            return

        addons_dir = Path(wow) / "_retail_" / "Interface" / "AddOns"
        if not addons_dir.parent.exists():
            self._addon_status_label.setText(tr("wizard.ready.addon_path_not_found", path=addons_dir.parent))
            self._addon_status_label.setStyleSheet("color: #FF4040; font-weight: bold;")
            return

        src = self._addon_source_path()
        if not src.exists():
            self._addon_status_label.setText(tr("wizard.ready.addon_files_missing"))
            self._addon_status_label.setStyleSheet("color: #FF4040; font-weight: bold;")
            return

        dest = addons_dir / "BabelChat"
        try:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
            self._addon_status_label.setText(tr("wizard.ready.addon_installed", dest=dest))
            self._addon_status_label.setStyleSheet("color: #40FF40; font-weight: bold;")
            self._install_addon_btn.setText(tr("wizard.ready.reinstall_addon"))
        except OSError as e:
            self._addon_status_label.setText(tr("addon.install_failed", detail=e))
            self._addon_status_label.setStyleSheet("color: #FF4040; font-weight: bold;")

    def _update_summary(self) -> None:
        """Summarise what the wizard is about to save.

        This read three widgets that stopped existing when the provider page
        became registry-driven, and it runs on entering the Ready page — so the
        wizard raised before `_finish` could ever be reached, and `_finish` is
        the only place that saves the entered credentials. On a fresh install
        the wizard always opens, so nothing could be configured through it at
        all. It now asks the registry, like everything else does.
        """
        own = LANGUAGES.get(self._own_lang.currentData(), "?")
        target = LANGUAGES.get(self._target_lang.currentData(), "?")
        wow = self._wow_path_input.text() or tr("wizard.ready.not_configured")

        configured = []
        for spec in all_providers():
            values = self._provider_group.values_for(spec.id)
            if not spec.is_configured(values):
                continue
            # Show that a key is set without showing the key: a summary screen
            # is the kind of thing people screenshot.
            secret = next((values.get(f.key, "") for f in spec.fields if f.secret), "")
            suffix = f" (****{secret[-4:]})" if len(secret) >= 4 else ""
            configured.append(f"{spec.display_name}{suffix}")

        backend_str = ", ".join(configured) if configured else tr("wizard.ready.not_configured")

        preferred = ""
        if len(configured) > 1:
            spec = provider_get(self._provider_group.preferred_id())
            if spec is not None:
                preferred = f"<br><b>{tr('settings.api.preferred')}</b> {spec.display_name}"

        self._summary_label.setText(
            f"<b>{tr('wizard.ready.translation')}</b> {backend_str}{preferred}<br>"
            f"<b>{tr('wizard.ready.wow_path')}</b> {wow}<br>"
            f"<b>{tr('wizard.ready.own_lang')}</b> {own}<br>"
            f"<b>{tr('wizard.ready.target_lang')}</b> {target}"
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
        elif index == PAGE_LANGUAGE:
            self._apply_language_defaults()
        elif index == PAGE_READY:
            self._update_summary()

    def _apply_language_defaults(self) -> None:
        """Set smart defaults based on UI language selection.

        Russian UI → own=EN, translate to=RU (русский переводит НА русский)
        English UI → own=RU, translate to=EN (англичанин переводит НА английский)
        """
        ui_lang = tr.get_language()
        if ui_lang == "RU":
            self._own_lang.setCurrentIndex(self._own_lang.findData("EN"))
            self._target_lang.setCurrentIndex(self._target_lang.findData("RU"))
        else:
            self._own_lang.setCurrentIndex(self._own_lang.findData("RU"))
            self._target_lang.setCurrentIndex(self._target_lang.findData("EN"))

    def _update_navigation(self) -> None:
        current = self._stack.currentIndex()

        self._back_btn.setVisible(current > 0)

        if current == TOTAL_PAGES - 1:
            self._next_btn.setText(tr("wizard.start"))
        else:
            self._next_btn.setText(tr("wizard.next"))

        # The provider page never blocks: a player who has no key yet still
        # gets the in-game dictionary and the overlay, and can add a key later
        # from Settings. Requiring one here left them with a disabled Next
        # button and no way into the app at all.
        self._next_btn.setEnabled(True)
        # Update summary on ready page if navigating back
        if current == PAGE_READY:
            self._update_summary()

        self._update_step_indicator()

    # ── Finalization ──────────────────────────────────────────────

    def _finish(self) -> None:
        self._provider_group.apply_to(self._config)
        self._config.wow_path = self._wow_path_input.text().strip()
        self._config.own_language = self._own_lang.currentData()
        self._config.target_language = self._target_lang.currentData()
        self._config.ui_language = tr.get_language()
        self._config.save()
        self.accept()

    def get_config(self) -> AppConfig:
        return self._config
