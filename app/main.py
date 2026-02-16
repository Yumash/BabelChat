"""WoWTranslator — entry point."""

from __future__ import annotations

import logging
import signal
import sys

from dotenv import load_dotenv
from lingua import Language
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication

from app.about_dialog import AboutDialog
from app.config import AppConfig, resolve_chatlog_path
from app.overlay import ChatOverlay
from app.parser import Channel
from app.pipeline import PipelineConfig, TranslationPipeline
from app.settings_dialog import SettingsDialog
from app.hotkeys import GlobalHotkeyManager
from app.tray import TrayIcon

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Lingua language code mapping
_LANG_CODE_TO_LINGUA: dict[str, Language] = {
    "EN": Language.ENGLISH,
    "RU": Language.RUSSIAN,
    "DE": Language.GERMAN,
    "FR": Language.FRENCH,
    "ES": Language.SPANISH,
    "IT": Language.ITALIAN,
    "PT": Language.PORTUGUESE,
    "PL": Language.POLISH,
    "NL": Language.DUTCH,
    "UK": Language.UKRAINIAN,
    "TR": Language.TURKISH,
    "ZH": Language.CHINESE,
    "JA": Language.JAPANESE,
    "KO": Language.KOREAN,
}


class PipelineThread(QThread):
    """Runs TranslationPipeline in a background thread."""

    message_ready = pyqtSignal(object)  # TranslatedMessage

    def __init__(self, config: PipelineConfig) -> None:
        super().__init__()
        self._config = config
        self._pipeline: TranslationPipeline | None = None

    def run(self) -> None:
        self._pipeline = TranslationPipeline(
            config=self._config,
            on_message=lambda msg: self.message_ready.emit(msg),
        )
        self._pipeline.start()
        self.exec()  # Event loop to keep thread alive

    def stop(self) -> None:
        if self._pipeline:
            self._pipeline.stop()
        self.quit()
        self.wait(5000)

    @property
    def pipeline(self) -> TranslationPipeline | None:
        return self._pipeline


def _build_pipeline_config(config: AppConfig) -> PipelineConfig:
    """Convert AppConfig to PipelineConfig."""
    chatlog = resolve_chatlog_path(config)
    own_lang = _LANG_CODE_TO_LINGUA.get(config.own_language, Language.ENGLISH)

    enabled_channels: set[Channel] = set()
    if config.channels_party:
        enabled_channels |= {Channel.PARTY, Channel.PARTY_LEADER}
    if config.channels_raid:
        enabled_channels |= {Channel.RAID, Channel.RAID_LEADER, Channel.RAID_WARNING}
    if config.channels_guild:
        enabled_channels |= {Channel.GUILD, Channel.OFFICER}
    if config.channels_say:
        enabled_channels |= {Channel.SAY, Channel.YELL}
    if config.channels_whisper:
        enabled_channels |= {Channel.WHISPER_FROM, Channel.WHISPER_TO}
    if config.channels_instance:
        enabled_channels |= {Channel.INSTANCE, Channel.INSTANCE_LEADER}

    return PipelineConfig(
        chatlog_path=chatlog,
        deepl_api_key=config.deepl_api_key,
        target_lang=config.target_language,
        own_language=own_lang,
        enabled_channels=enabled_channels,
        translation_enabled=config.translation_enabled_default,
    )


def main() -> int:
    load_dotenv()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Load config
    config = AppConfig.load()

    # First run — setup wizard if no API key
    if not config.deepl_api_key:
        from app.setup_wizard import SetupWizard

        wizard = SetupWizard(config)
        if wizard.exec() != SetupWizard.DialogCode.Accepted:
            return 0
        config = wizard.get_config()

    # Create overlay
    overlay = ChatOverlay()
    overlay.show()

    # Create system tray
    tray = TrayIcon()
    tray.show_overlay_requested.connect(overlay.show)
    tray.hide_overlay_requested.connect(overlay.hide)
    tray.toggle_translation_requested.connect(overlay._toggle_translation)
    tray.quit_requested.connect(app.quit)
    tray.show()

    def open_settings() -> None:
        nonlocal config
        dialog = SettingsDialog(config)
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
            config = dialog.get_config()

    tray.settings_requested.connect(open_settings)
    overlay.settings_requested.connect(open_settings)
    overlay.quit_requested.connect(app.quit)

    def open_about() -> None:
        AboutDialog().exec()

    tray.about_requested.connect(open_about)

    # Global hotkeys
    hotkey_mgr = GlobalHotkeyManager()
    hk_toggle_translate = hotkey_mgr.register(config.hotkey_toggle_translate)
    hk_toggle_interactive = hotkey_mgr.register(config.hotkey_toggle_interactive)

    def on_hotkey(hk_id: int) -> None:
        if hk_id == hk_toggle_translate:
            overlay._toggle_translation()
        elif hk_id == hk_toggle_interactive:
            overlay.toggle_interactive()

    hotkey_mgr.hotkey_pressed.connect(on_hotkey)
    hotkey_mgr.start()

    # Start pipeline
    pipeline_config = _build_pipeline_config(config)
    pipeline_thread = PipelineThread(pipeline_config)
    pipeline_thread.message_ready.connect(overlay.add_message)
    pipeline_thread.start()

    # Graceful shutdown
    def shutdown() -> None:
        logger.info("Shutting down...")
        hotkey_mgr.stop()
        pipeline_thread.stop()
        tray.hide()
        app.quit()

    signal.signal(signal.SIGINT, lambda *_: shutdown())
    app.aboutToQuit.connect(lambda: (hotkey_mgr.stop(), pipeline_thread.stop()))

    logger.info("WoWTranslator started")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
