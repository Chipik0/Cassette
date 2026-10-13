from __future__ import annotations

import random

from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from PyQt6.QtCore import (
    Qt,
    QEvent,
    QPoint,
    QRectF,
    QTimer,
    QObject,
    pyqtSignal
)

from PyQt6.QtGui import (
    QColor,
    QPixmap,
    QPainter,
    QKeyEvent,
    QVector4D,
    QMatrix4x4,
    QWheelEvent,
    QMouseEvent,
    QPaintEvent,
    QResizeEvent
)

from PyQt6.QtWidgets import (
    QWidget,
    QMainWindow,
    QGraphicsView
)

from System.Common import Styles

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
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.hide()

    # Painting

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

    # Event Absorption

    def mousePressEvent(self, event: QMouseEvent) -> None:
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        event.accept()

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        event.accept()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        event.accept()

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
        self.last_live_render_time = 0.0
        self.focal_length          = 1100.0

        self.background_color      = QColor(Styles.Colors.Background)

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

    def setup_idle_watchdog(self) -> None:
        self.idle_watchdog_timer = Timing.Timer(
            interval    = 600,
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

    def calculate_projection_transform(self):
        width_px  = float(self.target_window.width())
        height_px = float(self.target_window.height())

        center_x_px = width_px  / 2.0
        center_y_px = height_px / 2.0

        offset_x_px = float(self.offset_x_handle.value)
        offset_y_px = float(self.offset_y_handle.value)
        scale_ratio = max(0.60, min(1.35, float(self.scale_handle.value)))

        rot_x = max(-35.0, min(35.0, float(self.rotation_x_handle.value)))
        rot_y = max(-35.0, min(35.0, float(self.rotation_y_handle.value)))
        rot_z = max(-30.0, min(30.0, float(self.rotation_z_handle.value)))

        matrix = QMatrix4x4()

        matrix.translate(center_x_px + offset_x_px, center_y_px + offset_y_px, 0.0)
        matrix.setRow(3, QVector4D(0.0, 0.0, -1.0 / self.focal_length, 1.0))

        matrix.rotate(rot_x, 1.0, 0.0, 0.0)
        matrix.rotate(rot_y, 0.0, 1.0, 0.0)
        matrix.rotate(rot_z, 0.0, 0.0, 1.0)

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

    def start_visual_transformation(self, duration_ms: int = 500) -> None:
        if not self.is_visual_animating:
            self.capture_content_buffer()

            self.overlay.setGeometry(self.target_window.rect())
            self.overlay.show()
            self.overlay.raise_()
            self.overlay.setFocus()

            LoomEngine.ui_engine.acquire()

            self.is_visual_animating = True

        self.idle_watchdog_timer.start(duration_ms + 120)

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
            abs(self.rotation_x_handle.value) > 0.04 or
            abs(self.rotation_y_handle.value) > 0.04 or
            abs(self.rotation_z_handle.value) > 0.04 or
            abs(self.scale_handle.value - 1.0) > 0.008 or
            abs(self.offset_x_handle.value) > 0.3 or
            abs(self.offset_y_handle.value) > 0.3
        )

    def evaluate_animation_idle_state(self) -> None:
        if not self.is_visual_animating:
            return

        if self.is_transform_busy():
            self.idle_watchdog_timer.start(100)

            return

        self.finish_visual_transformation()

    # Callbacks

    def handle_visual_property_changed(self, value: float) -> None:
        if self.is_visual_animating:
            self.overlay.update()

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