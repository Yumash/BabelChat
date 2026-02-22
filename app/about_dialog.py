"""About dialog for WoWTranslator — WoW-themed."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.i18n import tr

VERSION = "1.0.3"

ABOUT_STYLESHEET = """
QDialog {
    background-color: #1a1a1a;
    color: #e0e0e0;
}
QLabel {
    color: #ccc;
}
QPushButton {
    background: #333;
    color: #e0e0e0;
    border: 1px solid #555;
    border-radius: 3px;
    padding: 8px 20px;
}
QPushButton:hover {
    background: #444;
    border-color: #FFD200;
    color: #FFD200;
}
"""


def _create_logo_pixmap() -> QPixmap:
    """Create a large 'W' logo."""
    pixmap = QPixmap(80, 80)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHints(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(30, 30, 30, 220))
    painter.setPen(QColor(255, 210, 0))
    painter.drawRoundedRect(2, 2, 76, 76, 8, 8)
    painter.setFont(QFont("Arial", 44, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "W")
    painter.end()
    return pixmap


class AboutDialog(QDialog):
    """About window with project info, credits, and links."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("about.title"))
        self.setFixedSize(420, 380)
        self.setStyleSheet(ABOUT_STYLESHEET)

        # Window icon — load from .ico, fallback to programmatic
        icon_set = False
        for icon_path in [
            Path(getattr(sys, "_MEIPASS", "")) / "assets" / "icon.ico",
            Path(__file__).parent.parent / "assets" / "icon.ico",
        ]:
            if icon_path.is_file():
                self.setWindowIcon(QIcon(str(icon_path)))
                icon_set = True
                break
        if not icon_set:
            icon_pixmap = QPixmap(32, 32)
            icon_pixmap.fill(QColor(0, 0, 0, 0))
            p = QPainter(icon_pixmap)
            p.setRenderHints(QPainter.RenderHint.Antialiasing)
            p.setBrush(QColor(30, 30, 30, 220))
            p.setPen(QColor(255, 210, 0))
            p.drawRoundedRect(1, 1, 30, 30, 4, 4)
            p.setFont(QFont("Arial", 18, QFont.Weight.Bold))
            p.drawText(icon_pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "W")
            p.end()
            self.setWindowIcon(QIcon(icon_pixmap))

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Logo + title row
        header = QHBoxLayout()
        logo_label = QLabel()
        logo_label.setPixmap(_create_logo_pixmap())
        logo_label.setFixedSize(80, 80)
        header.addWidget(logo_label)

        title_block = QVBoxLayout()
        title_block.setSpacing(4)

        title = QLabel("WoWTranslator")
        title.setStyleSheet("color: #FFD200; font-size: 22px; font-weight: bold;")
        title_block.addWidget(title)

        version = QLabel(f"Version {VERSION}")
        version.setStyleSheet("color: #999; font-size: 12px;")
        title_block.addWidget(version)

        subtitle = QLabel(tr("about.subtitle"))
        subtitle.setStyleSheet("color: #ccc; font-size: 13px;")
        title_block.addWidget(subtitle)

        title_block.addStretch()
        header.addLayout(title_block)
        header.addStretch()
        layout.addLayout(header)

        # Separator
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #444;")
        layout.addWidget(sep)

        # Developer
        dev_label = QLabel(f"{tr('about.developer')} <b>Andrey Yumashev</b>")
        dev_label.setStyleSheet("color: #ccc; font-size: 12px;")
        layout.addWidget(dev_label)

        # License
        license_label = QLabel(tr("about.license"))
        license_label.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(license_label)

        # Links
        links_sep = QLabel()
        links_sep.setFixedHeight(1)
        links_sep.setStyleSheet("background: #444;")
        layout.addWidget(links_sep)

        github_link = QLabel(
            '<a href="https://github.com/Yumash/WoWTranslator" '
            'style="color: #FFD200; font-size: 11px;">GitHub: Yumash/WoWTranslator</a>'
        )
        github_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        github_link.setOpenExternalLinks(True)
        layout.addWidget(github_link)

        layout.addStretch()

        # Close button
        close_btn = QPushButton(tr("about.close"))
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedWidth(100)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
