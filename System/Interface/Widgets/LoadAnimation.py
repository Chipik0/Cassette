from __future__ import annotations

import time
import math
import numpy

from enum import Enum

from PyQt6.QtCore import (
    Qt,
    pyqtSignal
)

from PyQt6.QtGui import (
    QPen,
    QBrush,
    QColor,
    QPainter,
    QHideEvent,
    QShowEvent,
    QPaintEvent,
    QResizeEvent,
    QPainterPath
)

from PyQt6.QtWidgets import (
    QWidget,
    QSizePolicy
)

from System.Common import Constants

from System.Interface import Timing
from System.Interface.Animation import (
    Lifecycle,
    LoomEngine
)

# Wave Types

class WaveMode(Enum):
    PULSE = 0
    SINE  = 1

# Pulse Shape Metrics

class PulseShapeConfiguration:
    P_WAVE_CENTER    = 0.18
    P_WAVE_WIDTH     = 0.036
    P_WAVE_AMPLITUDE = 0.16

    Q_WAVE_CENTER    = 0.32
    Q_WAVE_WIDTH     = 0.022
    Q_WAVE_AMPLITUDE = -0.10

    R_PEAK_CENTER    = 0.38
    R_PEAK_WIDTH     = 0.028
    R_PEAK_AMPLITUDE = 0.95

    S_WAVE_CENTER    = 0.44
    S_WAVE_WIDTH     = 0.024
    S_WAVE_AMPLITUDE = -0.22

    T_WAVE_CENTER    = 0.64
    T_WAVE_WIDTH     = 0.058
    T_WAVE_AMPLITUDE = 0.24

# Wave Synthesizer

class HeartbeatSynthesizer:
    @staticmethod
    def evaluate_normalized_sample(phase: float) -> float:
        p_wave = PulseShapeConfiguration.P_WAVE_AMPLITUDE * math.exp(
            -((phase - PulseShapeConfiguration.P_WAVE_CENTER) ** 2) /
             (2.0 * (PulseShapeConfiguration.P_WAVE_WIDTH ** 2))
        )

        q_wave = PulseShapeConfiguration.Q_WAVE_AMPLITUDE * math.exp(
            -((phase - PulseShapeConfiguration.Q_WAVE_CENTER) ** 2) /
             (2.0 * (PulseShapeConfiguration.Q_WAVE_WIDTH ** 2))
        )

        r_peak = PulseShapeConfiguration.R_PEAK_AMPLITUDE * math.exp(
            -((phase - PulseShapeConfiguration.R_PEAK_CENTER) ** 2) /
             (2.0 * (PulseShapeConfiguration.R_PEAK_WIDTH ** 2))
        )

        s_wave = PulseShapeConfiguration.S_WAVE_AMPLITUDE * math.exp(
            -((phase - PulseShapeConfiguration.S_WAVE_CENTER) ** 2) /
             (2.0 * (PulseShapeConfiguration.S_WAVE_WIDTH ** 2))
        )

        t_wave = PulseShapeConfiguration.T_WAVE_AMPLITUDE * math.exp(
            -((phase - PulseShapeConfiguration.T_WAVE_CENTER) ** 2) /
             (2.0 * (PulseShapeConfiguration.T_WAVE_WIDTH ** 2))
        )

        return p_wave + q_wave + r_peak + s_wave + t_wave

    @staticmethod
    def did_phase_cross_target(
            previous_phase: float,
            current_phase:  float,
            target_phase:   float
        ) -> bool:

        if previous_phase <= current_phase:
            return previous_phase <= target_phase < current_phase

        return previous_phase <= target_phase or target_phase < current_phase

# Path Assembler

class WavePathAssembler:
    @staticmethod
    def calculate_blended_offset(
            pixel_index:         int,
            samples:             list[float] | numpy.ndarray,
            flatten_ratio:       float,
            transition_ratio:    float,
            effective_amplitude: float,
            wavelength_px:       float,
            sine_phase:          float
        ) -> float:

        sample_count = len(samples)
        pulse_sample = samples[pixel_index] if pixel_index < sample_count else 0.0
        pulse_offset = pulse_sample * flatten_ratio

        spatial_angle = (pixel_index / wavelength_px) * 2.0 * math.pi - sine_phase
        sine_offset   = math.sin(spatial_angle) * effective_amplitude * flatten_ratio

        return pulse_offset * (1.0 - transition_ratio) + sine_offset * transition_ratio

    @staticmethod
    def append_blended_segment(
            path:                QPainterPath,
            start_index:         int,
            end_index:           int,
            samples:             list[float] | numpy.ndarray,
            center_y:            float,
            flatten_ratio:       float,
            transition_ratio:    float,
            effective_amplitude: float,
            wavelength_px:       float,
            sine_phase:          float
        ) -> None:

        if start_index > end_index:
            return

        initial_offset = WavePathAssembler.calculate_blended_offset(
            start_index,
            samples,
            flatten_ratio,
            transition_ratio,
            effective_amplitude,
            wavelength_px,
            sine_phase
        )

        path.moveTo(float(start_index), center_y - initial_offset)

        for index in range(start_index + 1, end_index + 1):
            offset = WavePathAssembler.calculate_blended_offset(
                index,
                samples,
                flatten_ratio,
                transition_ratio,
                effective_amplitude,
                wavelength_px,
                sine_phase
            )

            path.lineTo(float(index), center_y - offset)

    @staticmethod
    def append_contour_segment(
            path:                QPainterPath,
            start_index:         int,
            end_index:           int,
            samples:             list[float] | numpy.ndarray,
            contour_amplitudes:  numpy.ndarray,
            center_y:            float,
            flatten_ratio:       float,
            transition_ratio:    float,
            effective_amplitude: float,
            wavelength_px:       float,
            sine_phase:          float,
            contour_ratio:       float,
            max_contour_height:  float
        ) -> None:

        if start_index > end_index:
            return

        contour_size = len(contour_amplitudes)

        top_points:    list[tuple[float, float]] = []
        bottom_points: list[tuple[float, float]] = []

        for pixel_index in range(start_index, end_index + 1):
            base_wave_offset = WavePathAssembler.calculate_blended_offset(
                pixel_index,
                samples,
                flatten_ratio,
                transition_ratio,
                effective_amplitude,
                wavelength_px,
                sine_phase
            )

            wave_component = base_wave_offset * (1.0 - contour_ratio)

            normalized_amp = float(contour_amplitudes[pixel_index]) if pixel_index < contour_size else 0.0
            contour_offset = normalized_amp * max_contour_height * contour_ratio

            y_top    = center_y - wave_component - contour_offset
            y_bottom = center_y - wave_component + contour_offset

            top_points.append((float(pixel_index), y_top))
            bottom_points.append((float(pixel_index), y_bottom))

        path.moveTo(top_points[0][0], top_points[0][1])

        for x_coord, y_coord in top_points[1:]:
            path.lineTo(x_coord, y_coord)

        for x_coord, y_coord in reversed(bottom_points):
            path.lineTo(x_coord, y_coord)

        path.closeSubpath()

# Pulse Status Widget

class PulseStatusWidget(Lifecycle.LoomAnimationMixin, QWidget):
    heartbeat_occurred = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.wave_mode                = WaveMode.PULSE
        self.cardiac_arrest_active    = False
        self.sweep_position           = 0.0
        self.sweep_speed_px           = 220.0
        self.erase_gap_px             = 30.0
        self.wavelength_px            = 130.0
        self.sine_phase               = 0.0
        self.cardiac_phase            = 0.0
        self.buffer_values            = []
        self.line_thickness_px        = 2.0
        self.last_update_time_sec     = time.perf_counter()
        self.manual_beat_mode         = False
        self.manual_beat_active       = False

        self.target_contour             = numpy.empty(0, dtype = numpy.float32)
        self.cached_resampled_contour   = None
        self.cached_contour_source_size = 0

        self.simulation_timer = Timing.Timer(
            interval = Constants.FPS_60,
            callback = self.advance_simulation,
            parent   = self
        )

        self.setup_user_interface()
        self.setup_animations()

    # User Interface

    def setup_user_interface(self) -> None:
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )

        self.setMinimumHeight(64)

    # Animations

    def setup_animations(self) -> None:
        self.color_handle = LoomEngine.ui_engine.bind(
            owner      = self,
            name       = "line_color",
            base_value = QColor(255, 255, 255, 255),
            mix_mode   = LoomEngine.MixMode.REPLACE,
            on_change  = self.on_property_update
        )

        self.flatten_handle = LoomEngine.ui_engine.bind(
            owner      = self,
            name       = "flatten_ratio",
            base_value = 1.0,
            mix_mode   = LoomEngine.MixMode.REPLACE,
            on_change  = self.on_property_update
        )

        self.amplitude_handle = LoomEngine.ui_engine.bind(
            owner      = self,
            name       = "amplitude",
            base_value = 28.0,
            mix_mode   = LoomEngine.MixMode.REPLACE,
            on_change  = self.on_property_update
        )

        self.beats_per_minute_handle = LoomEngine.ui_engine.bind(
            owner      = self,
            name       = "beats_per_minute",
            base_value = 72.0,
            mix_mode   = LoomEngine.MixMode.REPLACE
        )

        self.sine_speed_handle = LoomEngine.ui_engine.bind(
            owner      = self,
            name       = "sine_speed",
            base_value = 1.0,
            mix_mode   = LoomEngine.MixMode.REPLACE
        )

        self.transition_handle = LoomEngine.ui_engine.bind(
            owner      = self,
            name       = "mode_transition",
            base_value = 0.0,
            mix_mode   = LoomEngine.MixMode.REPLACE,
            on_change  = self.on_property_update
        )

        self.contour_handle = LoomEngine.ui_engine.bind(
            owner      = self,
            name       = "contour_ratio",
            base_value = 0.0,
            mix_mode   = LoomEngine.MixMode.REPLACE,
            on_change  = self.on_property_update
        )

    def on_property_update(self, value: object):
        self.update()

    # Contour Management

    def get_resampled_contour(self, target_width: int) -> numpy.ndarray:
        if self.target_contour.size == 0 or target_width <= 0:
            return numpy.empty(0, dtype = numpy.float32)

        if (
            self.cached_resampled_contour is not None and
            self.cached_resampled_contour.size == target_width and
            self.cached_contour_source_size == self.target_contour.size
        ):
            return self.cached_resampled_contour

        source_indices = numpy.linspace(0.0, float(self.target_contour.size - 1), target_width)
        x_indices      = numpy.arange(self.target_contour.size, dtype = numpy.float32)

        self.cached_resampled_contour   = numpy.interp(source_indices, x_indices, self.target_contour).astype(numpy.float32)
        self.cached_contour_source_size = self.target_contour.size

        return self.cached_resampled_contour

    def transition_to_contour(
            self,
            amplitudes:      numpy.ndarray | list[float],
            duration_ms:     int    = 700,
            easing_function: object = LoomEngine.Easing.ease_out_cubic
        ) -> None:

        self.target_contour             = numpy.asarray(amplitudes, dtype = numpy.float32)
        self.cached_resampled_contour   = None
        self.cached_contour_source_size = 0

        self.transition_to_sine(duration_ms = duration_ms, easing_function = easing_function)
        self.set_amplitude(amplitude = 6.0, duration_ms = duration_ms, easing_function = easing_function)

        self.contour_handle.set_base(0.0)
        self.contour_handle.set_target(
            value                      = 1.0,
            duration_ms                = duration_ms,
            easing_function            = easing_function,
            multiply_duration_by_speed = False
        )

    def reset_contour(self) -> None:
        self.target_contour             = numpy.empty(0, dtype = numpy.float32)
        self.cached_resampled_contour   = None
        self.cached_contour_source_size = 0

        self.contour_handle.stop_targeting()
        self.contour_handle.set_base(0.0)

    # Lifecycle Events

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)

        self.last_update_time_sec = time.perf_counter()
        self.simulation_timer.start()

    def hideEvent(self, event: QHideEvent) -> None:
        super().hideEvent(event)

        self.simulation_timer.stop()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)

        current_width = self.width()

        if current_width <= 0:
            return

        self.reallocate_buffer(current_width)

    def reallocate_buffer(self, target_width: int) -> None:
        current_length = len(self.buffer_values)

        if current_length == target_width:
            return

        if current_length == 0:
            self.buffer_values = [0.0] * target_width

            return

        if target_width > current_length:
            expansion = [0.0] * (target_width - current_length)
            self.buffer_values.extend(expansion)

            return

        self.buffer_values = self.buffer_values[:target_width]

        if self.sweep_position >= target_width:
            self.sweep_position = 0.0

    # Simulation

    def advance_simulation(self) -> None:
        current_time              = time.perf_counter()
        delta_time                = min(0.1, current_time - self.last_update_time_sec)
        self.last_update_time_sec = current_time

        self.advance_pulse_simulation(delta_time)
        self.advance_sine_simulation(delta_time)

        self.update()

    def advance_pulse_simulation(self, delta_time: float) -> None:
        buffer_length = len(self.buffer_values)

        if buffer_length == 0:
            return

        current_amplitude = float(self.amplitude_handle.value)
        current_bpm       = float(self.beats_per_minute_handle.value)
        pixel_advance     = self.sweep_speed_px * delta_time

        if pixel_advance <= 0.0:
            return

        cardiac_frequency = current_bpm / 60.0
        phase_advance     = cardiac_frequency * delta_time

        previous_phase = self.cardiac_phase
        start_index    = int(self.sweep_position)
        end_index      = int(self.sweep_position + pixel_advance)
        pixel_count    = end_index - start_index

        for step_offset, write_index in enumerate(range(start_index, end_index + 1)):
            resolved_index = write_index % buffer_length

            if self.cardiac_arrest_active:
                sample_value = 0.0

            elif self.manual_beat_mode and not self.manual_beat_active:
                sample_value = 0.0

            else:
                interpolation_factor = (step_offset / pixel_count) if pixel_count > 0 else 0.0
                interpolated_phase   = (self.cardiac_phase + phase_advance * interpolation_factor) % 1.0
                sample_value         = HeartbeatSynthesizer.evaluate_normalized_sample(interpolated_phase) * current_amplitude

            self.buffer_values[resolved_index] = sample_value

        if self.manual_beat_mode and self.manual_beat_active:
            self.cardiac_phase += phase_advance

            if self.cardiac_phase >= 1.0:
                self.cardiac_phase      = 0.0
                self.manual_beat_active = False
                self.heartbeat_occurred.emit()

        else:
            self.cardiac_phase = (self.cardiac_phase + phase_advance) % 1.0

        self.sweep_position = (self.sweep_position + pixel_advance) % buffer_length

        if not self.cardiac_arrest_active and not self.manual_beat_mode and self.wave_mode == WaveMode.PULSE:
            if HeartbeatSynthesizer.did_phase_cross_target(
                previous_phase,
                self.cardiac_phase,
                PulseShapeConfiguration.R_PEAK_CENTER
            ):
                self.heartbeat_occurred.emit()

    def advance_sine_simulation(self, delta_time: float) -> None:
        current_speed    = float(self.sine_speed_handle.value)
        angular_velocity = current_speed * 4.0 * math.pi
        self.sine_phase  = (self.sine_phase + angular_velocity * delta_time) % (2.0 * math.pi)

    # Painting

    def paintEvent(self, event: QPaintEvent) -> None:
        current_width  = self.width()
        current_height = self.height()

        if current_width <= 0 or current_height <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        current_color       = self.color_handle.value
        line_pen            = QPen(current_color, self.line_thickness_px)
        center_y            = current_height / 2.0
        flatten_ratio       = float(self.flatten_handle.value)
        transition_ratio    = float(self.transition_handle.value)
        effective_amplitude = float(self.amplitude_handle.value)

        painter.setPen(line_pen)

        self.paint_blended_wave(
            painter,
            current_width,
            center_y,
            flatten_ratio,
            transition_ratio,
            effective_amplitude,
            current_color
        )

    def paint_blended_wave(
            self,
            painter:             QPainter,
            total_width:         int,
            center_y:            float,
            flatten_ratio:       float,
            transition_ratio:    float,
            effective_amplitude: float,
            current_color:       QColor
        ) -> None:

        buffer_length = len(self.buffer_values)

        if buffer_length == 0:
            return

        contour_ratio = float(self.contour_handle.value)

        if contour_ratio > 0.001 and self.target_contour.size > 0:
            wave_path = QPainterPath()

            fill_color = QColor(current_color)
            fill_alpha = int(45.0 * contour_ratio * (current_color.alpha() / 255.0))
            fill_color.setAlpha(fill_alpha)

            painter.setBrush(QBrush(fill_color))

            max_contour_height = center_y * 0.90
            resampled_contour  = self.get_resampled_contour(total_width)

            WavePathAssembler.append_contour_segment(
                path                = wave_path,
                start_index         = 0,
                end_index           = total_width - 1,
                samples             = self.buffer_values,
                contour_amplitudes  = resampled_contour,
                center_y            = center_y,
                flatten_ratio       = flatten_ratio,
                transition_ratio    = transition_ratio,
                effective_amplitude = effective_amplitude,
                wavelength_px       = self.wavelength_px,
                sine_phase          = self.sine_phase,
                contour_ratio       = contour_ratio,
                max_contour_height  = max_contour_height
            )

            painter.drawPath(wave_path)

            return

        painter.setBrush(Qt.BrushStyle.NoBrush)

        effective_gap = int(self.erase_gap_px * (1.0 - transition_ratio))
        wave_path     = QPainterPath()

        if effective_gap <= 1:
            WavePathAssembler.append_blended_segment(
                wave_path,
                0,
                total_width - 1,
                self.buffer_values,
                center_y,
                flatten_ratio,
                transition_ratio,
                effective_amplitude,
                self.wavelength_px,
                self.sine_phase
            )

        else:
            cursor_index  = int(self.sweep_position)
            gap_end_index = cursor_index + effective_gap

            if gap_end_index < buffer_length:
                WavePathAssembler.append_blended_segment(
                    wave_path,
                    0,
                    cursor_index,
                    self.buffer_values,
                    center_y,
                    flatten_ratio,
                    transition_ratio,
                    effective_amplitude,
                    self.wavelength_px,
                    self.sine_phase
                )

                WavePathAssembler.append_blended_segment(
                    wave_path,
                    gap_end_index,
                    buffer_length - 1,
                    self.buffer_values,
                    center_y,
                    flatten_ratio,
                    transition_ratio,
                    effective_amplitude,
                    self.wavelength_px,
                    self.sine_phase
                )

            else:
                wrapped_gap_end = gap_end_index - buffer_length
                WavePathAssembler.append_blended_segment(
                    wave_path,
                    wrapped_gap_end,
                    cursor_index,
                    self.buffer_values,
                    center_y,
                    flatten_ratio,
                    transition_ratio,
                    effective_amplitude,
                    self.wavelength_px,
                    self.sine_phase
                )

        painter.drawPath(wave_path)

    # API

    def set_mode(self, mode: WaveMode) -> None:
        self.wave_mode = mode

        target_value = 0.0 if mode == WaveMode.PULSE else 1.0
        self.transition_handle.set_base(target_value)

        self.update()

    def transition_to_mode(
            self,
            mode:            WaveMode,
            duration_ms:     int    = 800,
            easing_function: object = LoomEngine.Easing.smooth
        ) -> None:

        self.wave_mode = mode
        target_value   = 0.0 if mode == WaveMode.PULSE else 1.0

        if duration_ms <= 0:
            self.transition_handle.set_base(target_value)

            return

        self.transition_handle.set_target(
            value                      = target_value,
            duration_ms                = duration_ms,
            easing_function            = easing_function,
            multiply_duration_by_speed = False
        )

    def transition_to_sine(
            self,
            duration_ms:     int    = 800,
            easing_function: object = LoomEngine.Easing.smooth
        ) -> None:

        self.transition_to_mode(WaveMode.SINE, duration_ms, easing_function)

    def transition_to_pulse(
            self,
            duration_ms:     int    = 800,
            easing_function: object = LoomEngine.Easing.smooth
        ) -> None:

        self.transition_to_mode(WaveMode.PULSE, duration_ms, easing_function)

    def set_amplitude(
            self,
            amplitude:       float,
            duration_ms:     int    = 500,
            easing_function: object = LoomEngine.Easing.smooth
        ) -> None:

        if amplitude < 0.0:
            return

        if duration_ms <= 0:
            self.amplitude_handle.set_base(float(amplitude))

            return

        self.amplitude_handle.set_target(
            value                      = float(amplitude),
            duration_ms                = duration_ms,
            easing_function            = easing_function,
            multiply_duration_by_speed = False
        )

    def set_manual_mode(self, enabled: bool) -> None:
        self.manual_beat_mode   = enabled
        self.manual_beat_active = False
        self.cardiac_phase      = 0.0

        self.update()

    def trigger_single_beat(self, bpm: float = 75.0) -> None:
        self.manual_beat_active = True
        self.cardiac_phase      = 0.0

        self.beats_per_minute_handle.set_base(bpm)

    def set_beats_per_minute(
            self,
            beats_per_minute: float,
            duration_ms:      int    = 500,
            easing_function:  object = LoomEngine.Easing.smooth
        ) -> None:

        if beats_per_minute <= 0.0:
            return

        if duration_ms <= 0:
            self.beats_per_minute_handle.set_base(float(beats_per_minute))

            return

        self.beats_per_minute_handle.set_target(
            value                      = float(beats_per_minute),
            duration_ms                = duration_ms,
            easing_function            = easing_function,
            multiply_duration_by_speed = False
        )

    def set_loading_speed_ratio(
            self,
            ratio:           float,
            duration_ms:     int    = 500,
            easing_function: object = LoomEngine.Easing.smooth
        ) -> None:

        normalized_ratio  = max(0.0, min(1.0, ratio))
        target_bpm        = 42.0 + normalized_ratio * 138.0
        target_sine_speed = 0.8 + normalized_ratio * 3.2

        if duration_ms <= 0:
            self.beats_per_minute_handle.set_base(target_bpm)
            self.sine_speed_handle.set_base(target_sine_speed)

            return

        self.beats_per_minute_handle.set_target(
            value                      = target_bpm,
            duration_ms                = duration_ms,
            easing_function            = easing_function,
            multiply_duration_by_speed = False
        )

        self.sine_speed_handle.set_target(
            value                      = target_sine_speed,
            duration_ms                = duration_ms,
            easing_function            = easing_function,
            multiply_duration_by_speed = False
        )

    def flatten(
            self,
            duration_ms:     int    = 500,
            easing_function: object = LoomEngine.Easing.smooth
        ) -> None:

        if duration_ms <= 0:
            self.flatten_handle.set_base(0.0)

            return

        self.flatten_handle.set_target(
            value                      = 0.0,
            duration_ms                = duration_ms,
            easing_function            = easing_function,
            multiply_duration_by_speed = False
        )

    def unflatten(
            self,
            duration_ms:     int    = 500,
            easing_function: object = LoomEngine.Easing.smooth
        ) -> None:

        if duration_ms <= 0:
            self.flatten_handle.set_base(1.0)

            return

        self.flatten_handle.set_target(
            value                      = 1.0,
            duration_ms                = duration_ms,
            easing_function            = easing_function,
            multiply_duration_by_speed = False
        )

    def transition_to_red(
            self,
            duration_ms:     int    = 450,
            easing_function: object = LoomEngine.Easing.smooth
        ) -> None:

        target_color = QColor(255, 48, 48, 255)

        if duration_ms <= 0:
            self.color_handle.set_base(target_color)

            return

        self.color_handle.set_target(
            value                      = target_color,
            duration_ms                = duration_ms,
            easing_function            = easing_function,
            multiply_duration_by_speed = False
        )

    def transition_to_white(
            self,
            duration_ms:     int    = 450,
            easing_function: object = LoomEngine.Easing.smooth
        ) -> None:

        target_color = QColor(255, 255, 255, 255)

        if duration_ms <= 0:
            self.color_handle.set_base(target_color)

            return

        self.color_handle.set_target(
            value                      = target_color,
            duration_ms                = duration_ms,
            easing_function            = easing_function,
            multiply_duration_by_speed = False
        )

    def fade_out(
            self,
            duration_ms:     int    = 350,
            easing_function: object = LoomEngine.Easing.smooth
        ) -> None:

        current_color = self.color_handle.value

        target_color = QColor(
            current_color.red(),
            current_color.green(),
            current_color.blue(),
            0
        )

        if duration_ms <= 0:
            self.color_handle.set_base(target_color)

            return

        self.color_handle.set_target(
            value                      = target_color,
            duration_ms                = duration_ms,
            easing_function            = easing_function,
            multiply_duration_by_speed = False
        )

    def fade_in(
            self,
            duration_ms:     int    = 350,
            easing_function: object = LoomEngine.Easing.smooth
        ) -> None:

        current_color = self.color_handle.value
        target_color  = QColor(
            current_color.red(),
            current_color.green(),
            current_color.blue(),
            255
        )

        if duration_ms <= 0:
            self.color_handle.set_base(target_color)

            return

        self.color_handle.set_target(
            value                      = target_color,
            duration_ms                = duration_ms,
            easing_function            = easing_function,
            multiply_duration_by_speed = False
        )

    def simulate_cardiac_arrest(self) -> None:
        self.cardiac_arrest_active = True

    def resume_heartbeat(self) -> None:
        self.cardiac_arrest_active = False