from __future__ import annotations

import time
import random

from collections.abc import Callable

from PyQt6.QtCore import (
    Qt,
    QEvent,
    QPoint,
    QRectF,
    QObject,
    pyqtSignal
)

from PyQt6.QtGui import (
    QColor,
    QPixmap,
    QPainter,
    QVector4D,
    QMatrix4x4,
    QTransform,
    QPaintEvent
)

from PyQt6.QtWidgets import (
    QWidget,
    QMainWindow,
    QGraphicsView
)

from System.Common    import Styles
from System.Services  import Player
from System.Interface import Timing

from System.Interface.Animation import LoomEngine

# Visual Presentation Layer

class WindowAnimationOverlay(QWidget):
    def __init__(
            self,
            animator: WindowAnimator,
            parent:   QWidget
        ) -> None:

        super().__init__(parent)

        self.animator = animator

        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.hide()

    def paintEvent(self, event: QPaintEvent) -> None:
        if self.animator.live_updates_enabled:
            self.animator.refresh_live_viewport_region()

        pixmap = self.animator.captured_pixmap

        if pixmap is None or pixmap.isNull():
            return

        painter = QPainter(self)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        painter.fillRect(self.rect(), self.animator.background_color)

        transform_matrix = self.animator.calculate_projection_transform()
        painter.setTransform(transform_matrix)

        width_px  = float(self.width())
        height_px = float(self.height())

        painter.drawPixmap(
            QRectF(0.0, 0.0, width_px, height_px),
            pixmap,
            QRectF(pixmap.rect())
        )

        painter.end()

# Window Animator

class WindowAnimator(QObject):
    transformed = pyqtSignal()

    active_animators: dict[QWidget, WindowAnimator] = {}

    def __init__(self, window: QMainWindow) -> None:
        super().__init__(window)

        self.target_window         = window
        self.target_content_widget = window.centralWidget()
        self.captured_pixmap       = None
        self.static_frame_pixmap   = None
        self.is_visual_animating   = False
        self.live_updates_enabled  = True
        self.focal_length          = 1100.0

        self.background_color = QColor(Styles.Colors.Background)

        self.overlay = WindowAnimationOverlay(self, self.target_window)

        self.setup_animation_handles()
        self.setup_idle_watchdog()

        self.target_window.installEventFilter(self)

        WindowAnimator.active_animators[window] = self

    # Setup

    def setup_animation_handles(self) -> None:
        self.rotation_x_handle = LoomEngine.ui_engine.bind(
            owner      = self,
            name       = "window_rotation_x",
            base_value = 0.0,
            mix_mode   = LoomEngine.MixMode.ADD,
            on_change  = self.handle_visual_property_changed
        )

        self.rotation_y_handle = LoomEngine.ui_engine.bind(
            owner      = self,
            name       = "window_rotation_y",
            base_value = 0.0,
            mix_mode   = LoomEngine.MixMode.ADD,
            on_change  = self.handle_visual_property_changed
        )

        self.rotation_z_handle = LoomEngine.ui_engine.bind(
            owner      = self,
            name       = "window_rotation_z",
            base_value = 0.0,
            mix_mode   = LoomEngine.MixMode.ADD,
            on_change  = self.handle_visual_property_changed
        )

        self.scale_handle = LoomEngine.ui_engine.bind(
            owner      = self,
            name       = "window_scale",
            base_value = 1.0,
            mix_mode   = LoomEngine.MixMode.MULTIPLY,
            on_change  = self.handle_visual_property_changed
        )

        self.offset_x_handle = LoomEngine.ui_engine.bind(
            owner      = self,
            name       = "window_offset_x",
            base_value = 0.0,
            mix_mode   = LoomEngine.MixMode.ADD,
            on_change  = self.handle_visual_property_changed
        )

        self.offset_y_handle = LoomEngine.ui_engine.bind(
            owner      = self,
            name       = "window_offset_y",
            base_value = 0.0,
            mix_mode   = LoomEngine.MixMode.ADD,
            on_change  = self.handle_visual_property_changed
        )

        self.collapse_timer = Timing.Timer(
            interval    = 45,
            callback    = self.process_corrupt_collapse_step,
            single_shot = False,
            parent      = self
        )

    def setup_idle_watchdog(self) -> None:
        self.idle_watchdog_timer = Timing.Timer(
            interval    = 80,
            callback    = self.evaluate_animation_idle_state,
            single_shot = True,
            parent      = self
        )

    # Event Filtering

    def eventFilter(
            self,
            watched: QObject,
            event:   QEvent
        ) -> bool:

        if event.type() == QEvent.Type.Resize:
            self.overlay.setGeometry(self.target_window.rect())

        return super().eventFilter(watched, event)

    # 3D Matrix Projection

    def calculate_projection_transform(self) -> QTransform:
        width_px  = float(self.target_window.width())
        height_px = float(self.target_window.height())

        center_x_px = width_px  / 2.0
        center_y_px = height_px / 2.0

        offset_x_px = float(self.offset_x_handle.value)
        offset_y_px = float(self.offset_y_handle.value)
        scale_ratio = max(0.60, min(1.35, float(self.scale_handle.value)))

        rotation_x = max(-35.0, min(35.0, float(self.rotation_x_handle.value)))
        rotation_y = max(-35.0, min(35.0, float(self.rotation_y_handle.value)))
        rotation_z = max(-30.0, min(30.0, float(self.rotation_z_handle.value)))

        matrix = QMatrix4x4()

        matrix.translate(center_x_px + offset_x_px, center_y_px + offset_y_px, 0.0)
        matrix.setRow(3, QVector4D(0.0, 0.0, -1.0 / self.focal_length, 1.0))

        matrix.rotate(rotation_x, 1.0, 0.0, 0.0)
        matrix.rotate(rotation_y, 0.0, 1.0, 0.0)
        matrix.rotate(rotation_z, 0.0, 0.0, 1.0)

        matrix.scale(scale_ratio, scale_ratio, 1.0)
        matrix.translate(-center_x_px, -center_y_px, 0.0)

        return matrix.toTransform()

    # Presentation Management

    def capture_content_buffer(self) -> None:
        if self.target_content_widget is None:
            self.target_content_widget = self.target_window.centralWidget()

        if self.target_content_widget is None:
            return

        self.static_frame_pixmap = self.target_content_widget.grab()
        self.captured_pixmap     = QPixmap(self.static_frame_pixmap)

        self.refresh_live_viewport_region(force = True)

    def refresh_live_viewport_region(self, force: bool = False) -> None:
        if not self.is_visual_animating and not force:
            return

        if self.static_frame_pixmap is None or self.captured_pixmap is None:
            return

        views = self.target_content_widget.findChildren(QGraphicsView)

        if not views:
            return

        device_ratio = self.target_content_widget.devicePixelRatio()

        painter = QPainter(self.captured_pixmap)

        for graphics_view in views:
            if graphics_view.isWindow() or not graphics_view.isVisible():
                continue

            viewport  = graphics_view.viewport()
            view_size = viewport.size()

            if view_size.width() <= 0 or view_size.height() <= 0:
                continue

            viewport_position = viewport.mapTo(self.target_content_widget, QPoint(0, 0))

            viewport_rectangle = QRectF(
                float(viewport_position.x()),
                float(viewport_position.y()),
                float(view_size.width()),
                float(view_size.height())
            )

            painter.drawPixmap(
                viewport_rectangle,
                self.static_frame_pixmap,
                QRectF(
                    viewport_rectangle.x() * device_ratio,
                    viewport_rectangle.y() * device_ratio,
                    viewport_rectangle.width() * device_ratio,
                    viewport_rectangle.height() * device_ratio
                )
            )

            view_pixmap = QPixmap(
                int(view_size.width() * device_ratio),
                int(view_size.height() * device_ratio)
            )

            view_pixmap.setDevicePixelRatio(device_ratio)
            view_pixmap.fill(Qt.GlobalColor.transparent)

            view_painter = QPainter(view_pixmap)
            view_painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            view_painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

            graphics_view.render(view_painter)
            view_painter.end()

            painter.drawPixmap(viewport_position, view_pixmap)

        painter.end()

    def activate_visual_transformation(self) -> None:
        if self.is_visual_animating:
            return

        self.capture_content_buffer()

        self.overlay.setGeometry(self.target_window.rect())
        self.overlay.show()
        self.overlay.raise_()

        LoomEngine.ui_engine.acquire()

        self.is_visual_animating = True

    def finish_visual_transformation(self) -> None:
        if not self.is_visual_animating:
            return

        self.is_visual_animating = False

        self.overlay.hide()

        self.captured_pixmap     = None
        self.static_frame_pixmap = None

        LoomEngine.ui_engine.release()

    def is_transform_busy(self) -> bool:
        return (
            abs(self.rotation_x_handle.value) > 0.05       or
            abs(self.rotation_y_handle.value) > 0.05       or
            abs(self.rotation_z_handle.value) > 0.05       or
            abs(self.scale_handle.value - 1.0) > 0.005     or
            abs(self.offset_x_handle.value) > 0.5          or
            abs(self.offset_y_handle.value) > 0.5
        )

    def evaluate_animation_idle_state(self) -> None:
        if not self.is_visual_animating:
            return

        if self.is_transform_busy():
            self.idle_watchdog_timer.start(80)

            return

        self.finish_visual_transformation()

    # Callbacks

    def handle_visual_property_changed(self, value: float) -> None:
        if self.is_transform_busy():
            if not self.is_visual_animating:
                self.activate_visual_transformation()

            self.overlay.update()
            self.idle_watchdog_timer.start(80)

        elif self.is_visual_animating:
            if not self.idle_watchdog_timer.isActive():
                self.idle_watchdog_timer.start(80)

        self.transformed.emit()

    def reset(
            self,
            duration_ms: int = 250
        ) -> None:

        self.rotation_x_handle.set_target(0.0, duration_ms, LoomEngine.Easing.ease_out_cubic)
        self.rotation_y_handle.set_target(0.0, duration_ms, LoomEngine.Easing.ease_out_cubic)
        self.rotation_z_handle.set_target(0.0, duration_ms, LoomEngine.Easing.ease_out_cubic)

        self.scale_handle.set_target(1.0, duration_ms, LoomEngine.Easing.ease_out_cubic)

        self.offset_x_handle.set_target(0.0, duration_ms, LoomEngine.Easing.ease_out_cubic)
        self.offset_y_handle.set_target(0.0, duration_ms, LoomEngine.Easing.ease_out_cubic)

        self.idle_watchdog_timer.start(duration_ms + 40)

    # Corrupt Glitch Collapse

    def start_corrupt_collapse(
            self,
            duration_ms: int = 5000,
            on_finished: Callable[[], object] | None = None
        ) -> None:

        if duration_ms <= 0:
            raise ValueError("Collapse duration must be greater than zero")

        if self.captured_pixmap is None:
            self.activate_visual_transformation()

        self.collapse_duration_ms       = float(duration_ms)
        self.collapse_start_time_sec    = time.perf_counter()
        self.collapse_finished_callback = on_finished

        self.collapse_timer.start()

    def process_corrupt_collapse_step(self) -> None:
        if self.captured_pixmap is None or self.captured_pixmap.isNull():
            self.stop_corrupt_collapse()
            return

        elapsed_time_ms = (time.perf_counter() - self.collapse_start_time_sec) * 1000.0
        progress_ratio  = max(0.0, min(1.0, elapsed_time_ms / self.collapse_duration_ms))

        eased_progress = progress_ratio ** 1.7

        current_chunk_size = max(2, int(round(20.0 - (18.0 * eased_progress))))
        next_interval_ms   = max(12, int(round(45.0 - (33.0 * eased_progress))))
        self.collapse_timer.setInterval(next_interval_ms)

        pixmap_width  = self.captured_pixmap.width()
        pixmap_height = self.captured_pixmap.height()

        painter = QPainter(self.captured_pixmap)

        slices_per_tick = int(25 + (650 * eased_progress))

        darkness_alpha = int(round(255.0 * eased_progress))

        for _ in range(slices_per_tick):
            source_x = random.randint(0, max(0, pixmap_width - current_chunk_size))
            source_y = random.randint(0, max(0, pixmap_height - current_chunk_size))

            target_x = random.randint(0, max(0, pixmap_width - current_chunk_size))
            target_y = random.randint(0, max(0, pixmap_height - current_chunk_size))

            copied_fragment = self.captured_pixmap.copy(
                source_x,
                source_y,
                current_chunk_size,
                current_chunk_size
            )

            painter.drawPixmap(target_x, target_y, copied_fragment)

            if darkness_alpha > 0:
                painter.fillRect(
                    target_x,
                    target_y,
                    current_chunk_size,
                    current_chunk_size,
                    QColor(0, 0, 0, darkness_alpha)
                )

                if random.random() < (darkness_alpha / 255.0):
                    painter.fillRect(
                        target_x,
                        target_y,
                        current_chunk_size,
                        current_chunk_size,
                        QColor(0, 0, 0, 255)
                    )

        dot_spacing = 18
        dot_radius  = max(1, int(round((dot_spacing * 0.85) * eased_progress)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, darkness_alpha))

        for dot_y in range(-dot_spacing // 2, pixmap_height + dot_spacing // 2, dot_spacing):
            for dot_x in range(-dot_spacing // 2, pixmap_width + dot_spacing // 2, dot_spacing):
                painter.drawEllipse(
                    dot_x - dot_radius,
                    dot_y - dot_radius,
                    dot_radius * 2,
                    dot_radius * 2
                )

        if progress_ratio >= 1.0:
            painter.fillRect(self.captured_pixmap.rect(), QColor(0, 0, 0, 255))

        painter.end()

        self.overlay.update()

        if progress_ratio >= 1.0:
            self.stop_corrupt_collapse()

    def stop_corrupt_collapse(self) -> None:
        if self.collapse_timer is not None:
            self.collapse_timer.stop()
            self.collapse_timer.deleteLater()
            self.collapse_timer = None

        if self.collapse_finished_callback is not None:
            callback = self.collapse_finished_callback
            self.collapse_finished_callback = None
            callback()

    # Static Registry

    @classmethod
    def get(
            cls,
            window: QWidget | None = None
        ) -> WindowAnimator | None:

        if window is not None and window in cls.active_animators:
            return cls.active_animators[window]

        if not cls.active_animators:
            return None

        return next(iter(cls.active_animators.values()))