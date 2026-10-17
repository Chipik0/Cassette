from __future__ import annotations

from PyQt6.QtGui import (
    QFont,
    QResizeEvent
)

from PyQt6.QtCore import (
    Qt,
    QTimer
)

from PyQt6.QtWidgets import (
    QLabel,
    QWidget,
    QVBoxLayout
)

from . import Constants
from .Widget import AuditSimulationWidget

# Audit Container Widget

class AuditContainerWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.simulation_widget = AuditSimulationWidget(self)
        self.main_layout.addWidget(self.simulation_widget)

        self.intro_osd_label = QLabel(
            f"REC  ▶\nUSER {Constants.USER_NAME}\nFATE {self.simulation_widget.run_fate_scenario}",
            self.simulation_widget
        )
        self.intro_osd_label.setFont(QFont("Monospace", 20, QFont.Weight.Bold))
        self.intro_osd_label.setStyleSheet("color: #2bf04c; background-color: transparent; letter-spacing: 3px;")
        self.intro_osd_label.move(40, 40)
        self.intro_osd_label.show()

        self.hud_message_label = QLabel("[ Take the scanner. ]", self.simulation_widget)
        self.hud_message_label.setFont(QFont("Impact", 21))
        self.hud_message_label.setStyleSheet("color: #30f040; background-color: rgba(0, 0, 0, 160); padding: 6px 16px; border-radius: 6px;")
        self.hud_message_label.adjustSize()
        self.hud_message_label.show()

        self.reposition_hud_message()

    def hide_intro_osd(self) -> None:
        self.intro_osd_label.hide()

    def display_onscreen_message(self, message_text: str) -> None:
        self.hud_message_label.setText(message_text)
        self.hud_message_label.adjustSize()
        self.reposition_hud_message()
        self.hud_message_label.show()
        self.hud_message_label.raise_()

        QTimer.singleShot(7000, self.hud_message_label.hide)

    def reposition_hud_message(self) -> None:
        center_x = (self.simulation_widget.width() - self.hud_message_label.width()) // 2
        self.hud_message_label.move(center_x, 60)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.reposition_hud_message()