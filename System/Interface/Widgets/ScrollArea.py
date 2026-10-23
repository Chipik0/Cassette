from __future__ import annotations

from PyQt6.QtCore import (
    Qt,
    QSize,
    pyqtProperty,
    QPropertyAnimation
)

from PyQt6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QHideEvent,
    QShowEvent,
    QPaintEvent,
    QWheelEvent,
    QResizeEvent,
    QLinearGradient
)

from PyQt6.QtWidgets import (
    QFrame,
    QWidget,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout
)

from System.Common import (
    Dev,
    Styles,
    Constants
)

from System.Interface import Timing

# Content Canvas

@Dev.track_ram
class ContentCanvas(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.layout_manager = QVBoxLayout(self)
        self.layout_manager.setContentsMargins(0, 0, 0, 0)
        self.layout_manager.setSpacing(12)
        self.layout_manager.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def sizeHint(self) -> QSize:
        size_hint = self.layout_manager.sizeHint()

        return QSize(size_hint.width(), size_hint.height())

# Fade Overlay Widget

@Dev.track_ram
class FadeOverlay(QWidget):
    def __init__(
            self,
            color:             QColor,
            is_top_positioned: bool,
            parent:            QWidget | None = None
        ) -> None:

        super().__init__(parent)

        self.overlay_color     = color
        self.is_top_positioned = is_top_positioned
        self.opacity_value     = 0.0

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.hide()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setOpacity(self.opacity_value)

        gradient = QLinearGradient(0, 0, 0, self.height())

        opaque_color      = QColor(self.overlay_color)
        transparent_color = QColor(self.overlay_color)

        opaque_color.setAlpha(255)
        transparent_color.setAlpha(0)

        if self.is_top_positioned:
            gradient.setColorAt(0, opaque_color)
            gradient.setColorAt(1, transparent_color)

        else:
            gradient.setColorAt(0, transparent_color)
            gradient.setColorAt(1, opaque_color)

        painter.setBrush(QBrush(gradient))
        painter.drawRect(self.rect())

    @pyqtProperty(float)
    def opacity(self) -> float:
        return self.opacity_value

    @opacity.setter
    def opacity(self, value: float) -> None:
        self.opacity_value = value
        self.update()

# Elastic Scroll Area

@Dev.track_ram
class ElasticScrollArea(QScrollArea):
    def __init__(
            self,
            parent:      QWidget | None = None,
            fade_color:  QColor  | None = None,
            fade_height: int            = 40
        ) -> None:

        super().__init__(parent)

        self.raw_scroll_position = 0.0
        self.velocity_speed      = 0.0
        self.scrolling_is_active = False
        self.fade_height         = fade_height
        self.animations          = {}

        self.setStyleSheet(Styles.Other.Transparent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.setup_canvas()
        self.setup_fades(fade_color)
        self.setup_timers()
        self.viewport().installEventFilter(self)

    # Setup

    def setup_canvas(self) -> None:
        self.canvas         = ContentCanvas(self.viewport())
        self.layout_manager = self.canvas.layout_manager

    def setup_fades(self, fade_color: QColor | None) -> None:
        self.top_fade    = FadeOverlay(fade_color, True, self)
        self.bottom_fade = FadeOverlay(fade_color, False, self)

    def setup_timers(self) -> None:
        self.idle_timer = Timing.Timer(
            interval    = Constants.USER_SCROLL_IDLE_TIMEOUT,
            callback    = self.handle_scroll_finished,
            single_shot = True,
            parent      = self
        )

        self.animation_timer = Timing.Timer(
            interval    = Constants.ANIMATION_TICK_INTERVAL,
            callback    = self.process_animation_tick,
            parent      = self
        )

    # Widget Management

    def add_widget(self, widget: QWidget) -> None:
        self.layout_manager.addWidget(widget)

    def get_required_width(self) -> int:
        maximum_width_px = 0

        for index in range(self.layout_manager.count()):
            layout_item = self.layout_manager.itemAt(index)
            widget      = layout_item.widget() if layout_item else None

            if not widget:
                continue

            hint = widget.sizeHint()

            if hint.width() > maximum_width_px:
                maximum_width_px = hint.width()

        return max(maximum_width_px, 400)

    # Events

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)

        self.update_canvas_geometry()
        self.update_fade_geometry()

        limit_px                 = self.calculate_maximum_scroll()
        self.raw_scroll_position = max(0.0, min(limit_px, self.raw_scroll_position))

        self.apply_content_position()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)

        self.update_canvas_geometry()
        self.update_fade_geometry()
        self.update_fade_visibility()

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta_y         = event.angleDelta().y()
        limit_px        = self.calculate_maximum_scroll()
        resistance      = self.calculate_resistance(limit_px)
        raw_sensitivity = Constants.current_settings.get("wheel_scroll_sensitivity", 1.0)

        sensitivity = float(raw_sensitivity)

        self.velocity_speed     -= (delta_y * sensitivity / 8.0) * resistance
        self.scrolling_is_active = True

        self.idle_timer.start(Constants.USER_SCROLL_IDLE_TIMEOUT)

        if not self.animation_timer.isActive():
            self.animation_timer.start()

        event.accept()

    def hideEvent(self, event: QHideEvent) -> None:
        self.animation_timer.stop()
        super().hideEvent(event)

    # Animation

    def process_animation_tick(self) -> None:
        limit_px                  = self.calculate_maximum_scroll()
        self.raw_scroll_position += self.velocity_speed

        overshoot_px = self.calculate_overshoot(limit_px)

        self.update_velocity(overshoot_px)
        self.apply_content_position()

        should_stop = (
            abs(self.velocity_speed) < 0.01 and
            abs(overshoot_px) < 0.1 and
            not self.scrolling_is_active
        )

        if should_stop:
            self.raw_scroll_position = max(0.0, min(limit_px, self.raw_scroll_position))
            self.apply_content_position()
            self.animation_timer.stop()

    # Fades

    def update_fade_geometry(self) -> None:
        viewport_width_px = self.viewport().width()
        total_height_px   = self.height()

        self.top_fade.setGeometry(0, 0, viewport_width_px, self.fade_height)
        self.bottom_fade.setGeometry(
            0,
            total_height_px - self.fade_height,
            viewport_width_px,
            self.fade_height
        )

        self.top_fade.raise_()
        self.bottom_fade.raise_()

    def update_fade_visibility(self) -> None:
        limit_px = self.calculate_maximum_scroll()

        is_scrollable   = limit_px > 0.0
        can_scroll_up   = self.raw_scroll_position > 1.0 and is_scrollable
        can_scroll_down = self.raw_scroll_position < (limit_px - 1.0) and is_scrollable

        self.animate_fade(self.top_fade,    can_scroll_up)
        self.animate_fade(self.bottom_fade, can_scroll_down)

    def animate_fade(
            self,
            widget:            FadeOverlay,
            should_be_visible: bool
        ) -> None:

        target_opacity  = 1.0 if should_be_visible else 0.0
        current_opacity = widget.opacity

        if widget in self.animations:
            existing_animation = self.animations[widget]

            if existing_animation.state() == QPropertyAnimation.State.Running:
                if existing_animation.endValue() == target_opacity:
                    return

            existing_animation.stop()

        if current_opacity == target_opacity:
            return

        animation = QPropertyAnimation(widget, b"opacity")
        animation.setDuration(175)
        animation.setStartValue(current_opacity)
        animation.setEndValue(target_opacity)

        if should_be_visible:
            widget.show()

        else:
            animation.finished.connect(lambda target_widget = widget: target_widget.hide())

        animation.start()
        self.animations[widget] = animation

    # Calculation

    def update_canvas_geometry(self) -> None:
        viewport_width_px = self.viewport().width()

        self.canvas.resize(viewport_width_px, self.canvas.height())
        self.layout_manager.activate()

        canvas_height_px = self.layout_manager.sizeHint().height()

        self.canvas.resize(viewport_width_px, canvas_height_px)

    def calculate_maximum_scroll(self) -> float:
        maximum_scroll_px = max(0, self.canvas.height() - self.viewport().height())

        return float(maximum_scroll_px)

    def handle_scroll_finished(self) -> None:
        self.scrolling_is_active = False

    def apply_content_position(self) -> None:
        limit_px = self.calculate_maximum_scroll()
        raw_px   = self.raw_scroll_position
        y_px     = -self.calculate_position(raw_px, limit_px)

        self.canvas.move(0, int(y_px))
        self.update_fade_visibility()

    def calculate_overshoot(self, limit_px: float) -> float:
        if self.raw_scroll_position < 0.0:
            return self.raw_scroll_position

        if self.raw_scroll_position > limit_px:
            return self.raw_scroll_position - limit_px

        return 0.0

    # Physics Calculations

    def calculate_resistance(self, limit_px: float) -> float:
        if 0.0 <= self.raw_scroll_position <= limit_px:
            return 1.0

        if self.raw_scroll_position < 0.0:
            excess_px = abs(self.raw_scroll_position)

        else:
            excess_px = self.raw_scroll_position - limit_px

        raw_base        = Constants.current_settings.get("overscroll_resistance", Constants.VISUAL_RESISTANCE_STRENGTH)
        resistance_base = float(raw_base if raw_base is not None else Constants.VISUAL_RESISTANCE_STRENGTH)

        return max(0.05, 1.0 / (1.0 + excess_px / (resistance_base * 0.5))) * 0.3

    def update_velocity(self, overshoot_px: float) -> None:
        if overshoot_px == 0.0:
            raw_deceleration  = Constants.current_settings.get("inertia_deceleration_rate", Constants.INERTIA_DECELERATION_RATE)
            deceleration_rate = float(raw_deceleration if raw_deceleration is not None else Constants.INERTIA_DECELERATION_RATE)
            self.velocity_speed *= deceleration_rate

            return

        if self.scrolling_is_active:
            self.velocity_speed *= 0.8

            return

        stiffness_setting = float(Constants.current_settings.get("scroll_spring_stiffness", 4) or 4) / 100.0
        damping_setting   = float(Constants.current_settings.get("scroll_spring_damping", 40) or 40) / 100.0

        spring_force         = -overshoot_px        * stiffness_setting
        damping_force        = -self.velocity_speed * damping_setting
        self.velocity_speed += spring_force         + damping_force

    def calculate_position(
            self,
            raw_px:   float,
            limit_px: float
        ) -> float:

        raw_base        = Constants.current_settings.get("overscroll_resistance", Constants.VISUAL_RESISTANCE_STRENGTH)
        resistance_base = float(raw_base if raw_base is not None else Constants.VISUAL_RESISTANCE_STRENGTH)

        if raw_px < 0.0:
            return raw_px / (1.0 + abs(raw_px) / resistance_base)

        if raw_px > limit_px:
            excess_px = raw_px - limit_px

            return limit_px + (excess_px / (1.0 + excess_px / resistance_base))

        return raw_px