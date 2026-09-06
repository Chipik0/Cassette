from __future__ import annotations

from PyQt6.QtCore import QPoint

from System.Services import Player

from .. import Timeline

class AutoScroller:
    def __init__(self, conductor: Timeline.ScrollableContent) -> None:
        self.conductor          = conductor
        self.damping            = 0.90
        self.max_speed          = 30.0
        self.scroll_margin      = 100
        self.acceleration_curve = 2.0

        self.velocity    = 0.0
        self.is_dragging = False
        self.position    = float(self.conductor.horizontalScrollBar().value())

        self.rewind_sound = None

    # Position Processing

    def process_position(self, global_position: QPoint) -> None:
        if self.conductor.playback_manager.is_playing:
            return

        view_position   = self.conductor.viewport().mapFromGlobal(global_position)
        viewport_width  = self.conductor.viewport().width()
        target_velocity = 0.0

        if view_position.x() < self.scroll_margin:
            ratio           = max(0.0, min(1.0, (self.scroll_margin - view_position.x()) / self.scroll_margin))
            target_velocity = -self.max_speed * (ratio ** self.acceleration_curve)

        elif view_position.x() > viewport_width - self.scroll_margin:
            distance_from_right = view_position.x() - (viewport_width - self.scroll_margin)
            ratio               = max(0.0, min(1.0, distance_from_right / self.scroll_margin))
            target_velocity     = self.max_speed * (ratio ** self.acceleration_curve)

        horizontal_bar = self.conductor.horizontalScrollBar()
        is_at_limit    = (
            (target_velocity < -0.1 and horizontal_bar.value() <= horizontal_bar.minimum()) or
            (target_velocity > 0.1  and horizontal_bar.value() >= horizontal_bar.maximum())
        )

        self.velocity = target_velocity
        self.position = float(horizontal_bar.value())

        if abs(self.velocity) > 0.1 and not is_at_limit:
            sound_speed = min(max(abs(self.velocity / 14), 0.5), 1.7)

            if not self.is_dragging:
                Player.ui_player.play_sound("Rewind/Start", setting_key = "rewind_sounds")

                self.rewind_sound = Player.ui_player.play_sound(
                    "Rewind/Rewind2",
                    True,
                    sound_speed,
                    setting_key = "rewind_sounds"
                )

                self.is_dragging = True

            elif self.rewind_sound:
                self.rewind_sound.set_speed(sound_speed)

            self.conductor.start_scroll_tick()

        elif self.is_dragging:
            self.stop_drag(silent = is_at_limit)

    # Drag Control

    def stop_drag(self, silent: bool = False) -> None:
        self.is_dragging = False

        if not self.rewind_sound:
            return

        if not silent:
            Player.ui_player.play_sound("Rewind/Stop", setting_key = "rewind_sounds")

        self.rewind_sound.stop()
        self.rewind_sound = None

    # Ticking

    def tick(self) -> bool:
        if self.conductor.playback_manager.is_playing:
            return True

        if not self.is_dragging and abs(self.velocity) < 0.1:
            self.velocity = 0.0
            return True

        horizontal_bar = self.conductor.horizontalScrollBar()
        self.position += self.velocity
        self.position  = max(horizontal_bar.minimum(), min(horizontal_bar.maximum(), self.position))

        horizontal_bar.setValue(int(self.position))

        if self.is_dragging:
            return self.velocity == 0.0

        self.velocity *= self.damping

        if abs(self.velocity) > 0.5:
            return False

        self.velocity = 0.0
        return True