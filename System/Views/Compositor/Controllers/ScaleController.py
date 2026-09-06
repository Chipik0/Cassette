from __future__ import annotations

from PyQt6.QtCore import (
    QObject,
    pyqtSignal
)

from System.Common    import Constants
from System.Interface import Timing

from .. import Timeline

class ScaleController(QObject):
    zoom_changed = pyqtSignal(float)

    def __init__(self, conductor: Timeline.ScrollableContent) -> None:
        super().__init__(conductor)

        self.conductor = conductor

        self.px_per_sec           = Constants.current_settings["default_scaling"]
        self.target_px_per_sec    = self.px_per_sec
        self.scale_anim_active    = False
        self.scale_anim_center_ms = 0.0

        self.waveform_anim_timer = Timing.Timer(
            Constants.FPS_120,
            self.on_waveform_anim_tick,
            fps_managed = True
        )

        self.tile_fade_subframe  = 0

        self.frozen_tiles:               dict  = {}
        self.frozen_px_per_sec:          float = self.px_per_sec
        self.frozen_fallback_tiles:      dict  = {}
        self.frozen_fallback_px_per_sec: float = self.px_per_sec
        self.tile_fade_alphas:           dict  = {}

    # Scaling

    def scale_view(
            self,
            delta:        float = 0.0,
            force_update: bool  = False
        ) -> None:

        if not self.conductor.total_content_width:
            return

        viewport_width = self.conductor.viewport().width()
        current_scroll = self.conductor.horizontalScrollBar().value()

        duration_sec       = max(self.conductor.playback_manager.duration_ms / 1000.0, 0.001)
        fit_px_per_sec     = viewport_width / duration_sec
        minimum_px_per_sec = max(fit_px_per_sec, 20.0)
        new_target         = max(minimum_px_per_sec, self.target_px_per_sec + delta)

        if self.target_px_per_sec == new_target and not force_update:
            return

        magnitude = abs(new_target - self.target_px_per_sec)

        self.target_px_per_sec = new_target
        self.zoom_changed.emit(magnitude)

        if not self.scale_anim_active:
            center_px = current_scroll + viewport_width / 2.0

            self.scale_anim_center_ms = (center_px / self.px_per_sec) * 1000.0
            self.frozen_tiles         = dict(self.conductor.waveform_tiles)
            self.frozen_px_per_sec    = self.px_per_sec

            self.tile_fade_subframe = 0
            self.tile_fade_alphas.clear()
            self.frozen_fallback_tiles.clear()

        self.scale_anim_active = True

        if not self.waveform_anim_timer.isActive():
            self.waveform_anim_timer.start()

    # Animation Updates

    def on_waveform_anim_tick(self) -> None:
        if self.scale_anim_active:
            self.step_scale_animation()
            return

        self.tile_fade_subframe += 1

        if self.tile_fade_subframe < 2:
            return

        self.tile_fade_subframe = 0

        if self.step_tile_fade():
            self.waveform_anim_timer.stop()
            self.conductor.cached_beat_lines.clear()

    def step_scale_animation(self) -> None:
        difference          = self.target_px_per_sec - self.px_per_sec
        current_playhead_ms = self.conductor.get_playhead_position_ms()

        if abs(difference) < 0.3:
            self.px_per_sec        = self.target_px_per_sec
            self.scale_anim_active = False
            self.conductor.cached_beat_lines.clear()
            self.finish_scale_change(current_playhead_ms)
            return

        self.px_per_sec += difference * 0.18
        self.conductor.cached_beat_lines.clear()
        self.apply_intermediate_scale(current_playhead_ms)

    def apply_intermediate_scale(self, current_playhead_ms: float) -> None:
        self.conductor.update_scene_rect()
        self.synchronize_view_after_scale(current_playhead_ms)

        if self.conductor.composition and self.conductor.glyph_controller:
            self.conductor.glyph_controller.update_glyphs()

        self.conductor.viewport().update()

    def finish_scale_change(self, current_playhead_ms: float) -> None:
        self.conductor.waveform_controller.tile_generation_id += 1

        self.tile_fade_subframe         = 0
        self.tile_fade_alphas.clear()
        self.frozen_fallback_tiles      = dict(self.frozen_tiles)
        self.frozen_fallback_px_per_sec = self.frozen_px_per_sec
        self.frozen_tiles.clear()

        self.conductor.waveform_controller.clear()
        self.conductor.cached_beat_lines.clear()

        self.conductor.update_scene_rect()
        self.synchronize_view_after_scale(current_playhead_ms)

        if self.conductor.composition and self.conductor.glyph_controller:
            self.conductor.glyph_controller.update_glyphs()

        self.conductor.viewport().update()

    def synchronize_view_after_scale(self, current_playhead_ms: float) -> None:
        self.update_scroll_to_center()
        self.conductor.set_playhead_position_ms(current_playhead_ms)

        if self.conductor.playback_manager.is_playing and self.conductor.playback_controller.is_auto_scroll_active:
            self.conductor.playback_controller.on_playback_position_updated()

        else:
            self.update_scroll_to_center()

            if not self.conductor.playback_manager.is_playing:
                self.conductor.set_playhead_position_ms(current_playhead_ms)

    def step_tile_fade(self) -> bool:
        if not self.tile_fade_alphas:
            self.frozen_fallback_tiles.clear()
            return True

        completed_indices = [
            index
            for index, alpha in self.tile_fade_alphas.items()
            if alpha >= 1.0
        ]

        for index in completed_indices:
            del self.tile_fade_alphas[index]

        for index in self.tile_fade_alphas:
            self.tile_fade_alphas[index] = min(1.0, self.tile_fade_alphas[index] + 0.09)

        self.conductor.viewport().update()
        return not self.tile_fade_alphas

    def update_scroll_to_center(self) -> None:
        viewport_width   = self.conductor.viewport().width()
        new_center_px    = (self.scale_anim_center_ms / 1000.0) * self.px_per_sec
        new_scroll_value = round(new_center_px - viewport_width / 2.0)

        self.conductor.horizontalScrollBar().setValue(new_scroll_value)

    # Cleanup

    def cleanup(self) -> None:
        self.waveform_anim_timer.stop()
        self.scale_anim_active = False
        self.frozen_tiles.clear()
        self.frozen_fallback_tiles.clear()
        self.tile_fade_alphas.clear()