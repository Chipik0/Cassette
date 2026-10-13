from __future__ import annotations

from PyQt6.QtCore import (
    Qt,
    QRect
)

from PyQt6.QtGui import (
    QColor,
    QPainter,
    QPaintEvent
)

from PyQt6.QtWidgets import (
    QWidget,
    QSizePolicy
)

from System.Common import Styles

from System.Interface.Animation import (
    Lifecycle,
    LoomEngine
)

class TutorialProgressBar(Lifecycle.LoomAnimationMixin, QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.total           = 1.0
        self.completed       = 0.0
        self.displayed_ratio = 0.0

        self.setFixedHeight(6)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.progress_handle = LoomEngine.ui_engine.bind(
            owner      = self,
            name       = "displayed_ratio",
            base_value = 0.0,
            on_change  = self.on_displayed_ratio_changed
        )

    # Interface

    def set_total(self, total: float) -> None:
        self.total           = max(1.0, total)
        self.completed       = 0.0
        self.displayed_ratio = 0.0

        self.progress_handle.set_base(0.0)

    def set_completed(self, completed: float) -> None:
        self.completed = max(0.0, min(self.total, completed))
        target_ratio   = self.completed / self.total

        self.progress_handle.set_target(
            value           = target_ratio,
            duration_ms     = 300,
            easing_function = LoomEngine.Easing.ease_out_cubic
        )

    # Animation

    def on_displayed_ratio_changed(self, ratio: float) -> None:
        self.displayed_ratio = ratio

        self.update()

    # Events

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        track_rectangle = self.rect()
        radius_px       = track_rectangle.height() / 2.0

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(Styles.Colors.GlassBorder))
        painter.drawRoundedRect(
            track_rectangle,
            radius_px,
            radius_px
        )

        fill_width_px = track_rectangle.width() * self.displayed_ratio

        if fill_width_px <= 0.0:
            painter.end()
            return

        fill_rectangle = QRect(
            track_rectangle.x(),
            track_rectangle.y(),
            int(round(fill_width_px)),
            track_rectangle.height()
        )

        painter.setBrush(QColor(Styles.Colors.NothingAccent))
        painter.drawRoundedRect(
            fill_rectangle,
            radius_px,
            radius_px
        )

        painter.end()