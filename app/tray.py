"""System tray icon for WoWTranslator."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from app.i18n import tr

# Icon path: works both in dev (assets/) and bundled (PyInstaller _MEIPASS)
_ICON_CANDIDATES = [
    Path(getattr(sys, "_MEIPASS", "")) / "assets" / "icon.ico",
    Path(__file__).parent.parent / "assets" / "icon.ico",
]


def _create_default_icon() -> QIcon:
    """Load icon from .ico file, or generate programmatically as fallback."""
    for path in _ICON_CANDIDATES:
        if path.is_file():
            return QIcon(str(path))

    # Fallback: draw icon programmatically
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


class TrayIcon(QSystemTrayIcon):
    """System tray icon with context menu."""

    show_overlay_requested = pyqtSignal()
    hide_overlay_requested = pyqtSignal()
    toggle_translation_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    about_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(_create_default_icon(), parent)
        self.setToolTip("WoWTranslator")
        self._overlay_visible = True

        self._menu = QMenu()

        self._show_action = QAction(tr("tray.hide_overlay"))
        self._show_action.triggered.connect(self._toggle_overlay)
        self._menu.addAction(self._show_action)

        self._translate_action = QAction(tr("tray.toggle_translation"))
        self._translate_action.triggered.connect(self.toggle_translation_requested)
        self._menu.addAction(self._translate_action)

        self._menu.addSeparator()

        settings_action = QAction(tr("tray.settings"))
        settings_action.triggered.connect(self.settings_requested)
        self._menu.addAction(settings_action)

        about_action = QAction(tr("tray.about"))
        about_action.triggered.connect(self.about_requested)
        self._menu.addAction(about_action)

        self._menu.addSeparator()

        quit_action = QAction(tr("tray.quit"))
        quit_action.triggered.connect(self.quit_requested)
        self._menu.addAction(quit_action)

        self.setContextMenu(self._menu)
        self.activated.connect(self._on_activated)

    def _toggle_overlay(self) -> None:
        if self._overlay_visible:
            self._overlay_visible = False
            self._show_action.setText(tr("tray.show_overlay"))
            self.hide_overlay_requested.emit()
        else:
            self._overlay_visible = True
            self._show_action.setText(tr("tray.hide_overlay"))
            self.show_overlay_requested.emit()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_overlay()
