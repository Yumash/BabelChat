"""GTK entry point for BabelChat (Linux/Wayland layer-shell frontend).

Qt-free counterpart to app/main.py: builds the reusable TranslationPipeline and
TranslatorService, then runs the GTK4 layer-shell overlay. The pipeline runs in
its own background thread and pushes TranslatedMessages to the overlay, which
marshals them onto the GTK main loop.

Stage 1: overlay display + reply box. Settings/tray come later; for now the
overlay's settings/quit buttons quit the app (settings UI is still the Qt
SettingsDialog, launched separately, or to be ported).
"""

from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv
from lingua import Language

from app import debug_log
from app.config import AppConfig, enabled_channels, resolve_chatlog_path, saved_config_exists
from app.i18n import startup_ui_language, tr
from app.overlay_gtk import ChatOverlayGtk
from app.pipeline import PipelineConfig, TranslationPipeline
from app.settings_gtk import SettingsWindowGtk
from app.translator import TranslatorService, any_configured
from app.tray_sni import MenuItem, TrayIcon

_LANG_CODE_TO_LINGUA: dict[str, Language] = {
    "EN": Language.ENGLISH,
    "RU": Language.RUSSIAN,
    "ES": Language.SPANISH,
    "DE": Language.GERMAN,
    "FR": Language.FRENCH,
    "PT": Language.PORTUGUESE,
    "IT": Language.ITALIAN,
    "PL": Language.POLISH,
    "ZH": Language.CHINESE,
    "KO": Language.KOREAN,
    "JA": Language.JAPANESE,
}


def _build_pipeline_config(config: AppConfig) -> PipelineConfig:
    chatlog = resolve_chatlog_path(config)
    own_lang = _LANG_CODE_TO_LINGUA.get(config.own_language, Language.ENGLISH)

    channels = enabled_channels(config)

    return PipelineConfig(
        chatlog_path=chatlog,
        providers=config.providers,
        translator_priority=config.translator_priority,
        target_lang=config.target_language,
        own_language=own_lang,
        enabled_channels=channels,
        skip_own_messages=config.skip_own_messages,
        translation_enabled=config.translation_enabled_default,
    )


def main() -> int:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = AppConfig.load()
    # Off unless asked for: it records every chat line in full.
    debug_log.configure(config.debug_capture_trace)

    # The Qt entry point has always applied the saved language and the GTK one
    # never did, so every Linux user got the default — Russian — whatever they
    # had picked in Settings. This has to happen before the wizard, because the
    # wizard is what a first-time player reads first.
    # Whether a saved config exists is config.py's question to answer, not a
    # stat of one filename: load() reads config.json.bak too, so the main file
    # being gone does not mean the user's language preference is.
    config_exists = saved_config_exists()
    tr.set_language(startup_ui_language(config_exists=config_exists, saved=config.ui_language))

    # First run: no config file yet, or no translation API configured →
    # run the setup wizard (its own blocking GTK loop) before normal startup.
    if not config_exists or not any_configured(config.providers):
        from app.setup_wizard_gtk import run_setup_wizard

        config = run_setup_wizard(config)
        if config is None:  # user closed the wizard without finishing
            return 0

        # The wizard saves a language of its own — adopt it, or the app starts
        # in whatever was on screen before the user chose.
        tr.set_language(config.ui_language)

    overlay = ChatOverlayGtk(config)

    # Reply translator (outgoing): default EN unless own language is EN.
    reply_translator = TranslatorService.from_config(config)
    reply_lang = "EN" if config.own_language != "EN" else config.target_language
    overlay.set_translator(reply_translator, reply_lang)

    tray = None  # created below; referenced by _quit

    # Pipeline: deliver each TranslatedMessage to the overlay (thread-safe).
    pipeline = TranslationPipeline(
        config=_build_pipeline_config(config),
        on_message=overlay.deliver_message,
    )

    def _quit() -> None:
        try:
            if tray is not None:
                tray.shutdown()
            pipeline.stop()
        finally:
            overlay._app.quit()

    overlay.on_quit = _quit

    settings_win: dict[str, SettingsWindowGtk | None] = {"ref": None}

    def _open_settings() -> None:
        # If a settings window is already open, just bring it forward instead of
        # opening another one.
        existing = settings_win["ref"]
        if existing is not None:
            existing.present()
            return

        def _on_saved(updated: AppConfig) -> None:
            nonlocal config
            config = updated

            # The translation helper is process-global. Changing the saved config
            # alone is not enough because existing GTK widgets already contain
            # strings produced by tr() at construction time.
            tr.set_language(updated.ui_language)
            overlay.apply_language()
            if tray is not None:
                # The tray is built once at startup and there is no reopening
                # it, so nothing else will ever bring it into the new language.
                tray.update_item("overlay", label=_overlay_item_label())
                tray.update_item("tr", label=tr("tray.toggle_translation"))
                tray.update_item("settings", label=tr("tray.settings"))
                tray.update_item("quit", label=tr("tray.quit"))

            # Apply live: rebuild pipeline config (channels/langs).
            pipeline.update_config(_build_pipeline_config(updated))
            # Rebuild the reply translator so API key/priority changes take
            # effect without a restart.
            new_translator = TranslatorService.from_config(updated)
            new_reply_lang = "EN" if updated.own_language != "EN" else updated.target_language
            overlay.set_translator(new_translator, new_reply_lang)
            # Restyle the overlay live (opacity/font) without a restart.
            overlay.apply_appearance()
            logging.info("settings applied live")

        win = SettingsWindowGtk(config, on_saved=_on_saved, app=overlay._app)
        settings_win["ref"] = win

        def _on_close(_w: object) -> bool:
            settings_win["ref"] = None
            return False  # allow the window to close

        win._win.connect("close-request", _on_close)
        win.present()

    overlay.on_settings = _open_settings

    # ── system tray (StatusNotifierItem) ─────────────────────────────────
    def _icon_path() -> str | None:
        import sys as _sys
        base = getattr(_sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, "assets", "icon.png")
        return path if os.path.exists(path) else None

    #: Whether the overlay is on screen, which decides what the first tray item
    #: offers to do. Kept here so relabelling the menu after a language change
    #: does not have to guess, and cannot offer to hide a hidden window.
    overlay_visible = [True]

    def _overlay_item_label() -> str:
        return tr("tray.hide_overlay") if overlay_visible[0] else tr("tray.show_overlay")

    def _tray_toggle_overlay() -> None:
        overlay_visible[0] = overlay.toggle_visible()
        if tray is not None:
            tray.update_item("overlay", label=_overlay_item_label())

    def _tray_toggle_tr() -> None:
        overlay.set_translation_active(not pipeline.translation_enabled)

    def _toggle_translation(enabled: bool) -> None:
        pipeline.translation_enabled = enabled
        if tray is not None:
            tray.update_item("tr", checked=enabled)

    overlay.on_toggle_translation = _toggle_translation

    try:
        tray = TrayIcon(
            icon_png=_icon_path(),
            on_activate=_tray_toggle_overlay,
            on_secondary_activate=_tray_toggle_tr,
            items=[
                MenuItem("overlay", _overlay_item_label(), _tray_toggle_overlay),
                MenuItem("tr", tr("tray.toggle_translation"), _tray_toggle_tr, checkable=True,
                         checked=bool(config.translation_enabled_default)),
                MenuItem("settings", tr("tray.settings"), _open_settings),
                MenuItem(),  # separator
                MenuItem("quit", tr("tray.quit"), _quit),
            ],
        )
    except Exception:  # noqa: BLE001 — tray is optional; never block startup
        logging.exception("tray icon unavailable (continuing without it)")

    # Show recent history on launch (same as the PyQt frontend). These queue in
    # the overlay's pending list and render once the window is built.
    try:
        for hist_msg in pipeline.load_history(50):
            overlay.deliver_message(hist_msg)
    except Exception:  # noqa: BLE001
        logging.exception("history load failed (continuing without it)")

    pipeline.start()
    try:
        return overlay.run()
    except KeyboardInterrupt:
        # Ctrl-C in a terminal: exit quietly instead of dumping a traceback.
        return 0
    finally:
        pipeline.stop()


if __name__ == "__main__":
    sys.exit(main())
