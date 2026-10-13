from __future__ import annotations

from PyQt6.QtGui import (
    QCursor,
    QMouseEvent
)

from PyQt6.QtCore import (
    Qt,
    QEvent,
    QPoint,
    QRectF,
    QPointF,
    QObject,
    pyqtSignal
)

from PyQt6.QtWidgets import QApplication

from System.Common import Styles

from .. import Timeline

# Mouse Controller Class

class MouseController(QObject):
    drag_scroll_requested = pyqtSignal(QPoint)
    drag_scroll_stopped   = pyqtSignal()

    def __init__(self, conductor: Timeline.ScrollableContent) -> None:
        super().__init__(conductor)

        self.conductor            = conductor
        self.playback_manager     = conductor.playback_manager
        self.is_marquee_selecting = False
        self.is_dragging_glyphs   = False

    # State

    def set_glyphs_dragging(self, is_dragging: bool) -> None:
        self.is_dragging_glyphs = is_dragging

    # Marquee Selection

    def start_marquee(self, event: QMouseEvent) -> None:
        self.conductor.marquee_item.start_marquee(self.conductor.mapToScene(event.pos()))
        self.is_marquee_selecting = True

    def end_marquee(self) -> None:
        if not self.is_marquee_selecting:
            return

        self.conductor.marquee_item.end_marquee()
        self.is_marquee_selecting = False
        self.drag_scroll_stopped.emit()

    def marquee_tick(self, event: QMouseEvent) -> None:
        if not self.is_marquee_selecting:
            return

        self.conductor.marquee_item.update_end_point(
            self.conductor.mapToScene(event.pos()),
            animate = False
        )

        global_position = self.conductor.viewport().mapToGlobal(event.pos())
        self.drag_scroll_requested.emit(global_position)

    # Ruler Interactions

    def handle_ruler_press(self, event: QMouseEvent) -> None:
        if self.playback_manager.is_playing:
            return

        new_position_x = self.conductor.mapToScene(event.pos()).x()

        if self.conductor.get_playhead_position_px() != new_position_x:
            self.conductor.set_playhead_position_px(new_position_x, True)

    def handle_ruler_hover(self, event: QMouseEvent) -> None:
        position_y     = event.position().y()
        playhead_hover = self.conductor.playhead_hover
        waveform_end   = Styles.Metrics.Waveform.Height + Styles.Metrics.Tracks.RulerHeight

        if waveform_end > position_y > 0:
            target_scene_x = float(self.conductor.mapToScene(event.pos()).x())
            is_playing     = self.playback_manager.is_playing

            playhead_hover.show_at(target_scene_x, immediate = is_playing)

        elif playhead_hover.isVisible():
            playhead_hover.hide_animated()

    # Synthetic Events

    def force_mouse_update(self) -> None:
        if (
            not self.is_marquee_selecting and
            not self.is_dragging_glyphs and
            not self.conductor.playhead_hover.isVisible()
        ):
            return

        global_position = QCursor.pos()
        local_position  = self.conductor.viewport().mapFromGlobal(global_position)

        synthetic_event = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(local_position),
            QPointF(global_position),
            Qt.MouseButton.NoButton,
            QApplication.mouseButtons(),
            QApplication.keyboardModifiers()
        )

        self.process_mouse_move_event(synthetic_event)

    # Event Dispatching

    def process_mouse_press_event(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        ruler_area = QRectF(
            0.0,
            0.0,
            float(self.conductor.width()),
            float(Styles.Metrics.Tracks.RulerHeight + Styles.Metrics.Waveform.Height)
        )

        if ruler_area.contains(event.position()):
            self.handle_ruler_press(event)
            event.accept()

            return

        viewport_position = event.position().toPoint()

        if self.conductor.itemAt(viewport_position):
            event.ignore()

            return

        if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.conductor.scene.clearSelection()

        self.start_marquee(event)
        event.accept()

    def process_mouse_move_event(self, event: QMouseEvent) -> None:
        self.marquee_tick(event)
        self.handle_ruler_hover(event)

    def process_mouse_release_event(self, event: QMouseEvent) -> None:
        self.end_marquee()

    def process_mouse_leave_event(self, event: QMouseEvent) -> None:
        self.conductor.playhead_hover.hide_animated()