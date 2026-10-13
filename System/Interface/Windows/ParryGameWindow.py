from __future__ import annotations

import random

from PyQt6.QtCore import (
    Qt,
    QTimer,
    QElapsedTimer
)
from PyQt6.QtGui import (
    QPixmap,
    QKeyEvent,
    QMouseEvent
)
from PyQt6.QtWidgets import (
    QLabel,
    QWidget
)
from System.Common import Utils
from System.Services import Player
from System.Interface import (
    Timing,
    Widgets
)
from System.Interface.Animation import (
    LoomEngine,
    WindowAnimator
)
from System.Interface.Windows.FloatingWindowGPU import FloatingWindowGPU

# Window

class ParryGameWindow(FloatingWindowGPU):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title                      = None,
            parent                     = parent,
            stays_on_top               = True,
            enable_audioplayer_effects = False
        )

        self.setup_frame_configurations()

        self.approach_duration_ms       = 400.0
        self.approach_step_ms           = 60.0
        self.approach_timer_ms          = 0.0
        self.approach_elapsed_ms        = 0.0
        self.approach_frame_toggle      = False

        self.parry_delay_ms             = 110.0
        self.parry_window_ms            = 100.0

        self.game_over_duration_ms      = 1900.0
        self.game_over_pulse_ms         = 200.0
        self.game_over_fade_duration_ms = 850.0
        self.game_over_timer_ms         = 0.0
        self.game_over_active           = False
        self.game_over_triggered        = False

        self.current_phase              = 1
        self.current_state              = "APPROACH"
        self.animation_timer_ms         = 0.0
        self.action_timer_ms            = 0.0
        self.next_taunt_is_variant_a    = True

        self.active_frame_sequence      = self.frames_approach
        self.sequence_cursor_index      = 0

        self.flash_timer_ms             = 0.0
        self.flash_duration_ms          = 1.0
        self.flash_red                  = 0.0
        self.flash_green                = 0.0
        self.flash_blue                 = 0.0
        self.base_rectangle_color       = [0.17, 0.17, 0.17]

        self.frames                     = self.slice_sprite_sheet()
        self.tick_timer                 = QElapsedTimer()
        self.window_animator            = WindowAnimator.WindowAnimator.get()

        self.setup_parry_layout()
        self.setup_parry_timers()
        self.start_game()
        self.adjustSize()

    # Configurations

    def setup_frame_configurations(self) -> None:
        self.frame_width        = 512
        self.frame_height       = 512
        self.columns_count      = 15
        self.rows_count         = 14
        self.scale_factor       = 0.9
        self.frames_per_second  = 20

        self.frames_taunt_a     = [76, 77, 78, 79, 80, 81, 82, 83]
        self.frames_taunt_b     = [84, 85, 86, 87, 88, 89]

        self.frames_approach    = [148, 149]

        self.frames_swing_one   = [150, 151, 152, 153, 154, 155]
        self.frames_fail_one    = [91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102]

        self.frames_swing_two   = [21, 20, 19, 18, 17, 32, 33, 34]
        self.frames_fail_two    = [19, 20, 21, 22, 23, 24, 25, 26, 27]

        self.frames_swing_three = [18, 19, 20, 35, 36, 37, 38, 39, 40, 41, 42, 43]
        self.frames_fail_three  = [44, 45, 46, 47, 48, 49, 50, 51, 52]

        self.frames_victory     = [
            102, 103, 104, 105, 106, 107, 108, 109, 110,
            111, 112, 113, 114, 115, 116, 117, 118, 119, 120
        ]

    # Layout Setup

    def setup_parry_layout(self) -> None:
        target_width_px  = int(self.frame_width  * self.scale_factor) - 50
        target_height_px = int(self.frame_height * self.scale_factor) - 50

        self.sprite_label = QLabel(self.content_widget)
        self.sprite_label.setFixedSize(target_width_px, target_height_px)
        self.sprite_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sprite_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.status_label = Widgets.DescriptionLabel("RMB to parry.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.content_layout.addWidget(self.sprite_label)
        self.content_layout.addWidget(self.status_label)

    def setup_parry_timers(self) -> None:
        self.game_timer = Timing.Timer(
            interval = 16,
            callback = self.advance_game_tick,
            parent   = self
        )

    # Frame Slicing

    def slice_sprite_sheet(self) -> list[QPixmap]:
        image_path       = Utils.get_resource_path("System/Assets/Image/Enemy.png")
        source_pixmap    = QPixmap(image_path)

        target_width_px  = int(self.frame_width * self.scale_factor)
        target_height_px = int(self.frame_height * self.scale_factor)
        frames           = []

        for row_index in range(self.rows_count):
            for column_index in range(self.columns_count):
                cropped_pixmap = source_pixmap.copy(
                    column_index * self.frame_width,
                    row_index * self.frame_height,
                    self.frame_width,
                    self.frame_height
                )

                scaled_pixmap  = cropped_pixmap.scaled(
                    target_width_px,
                    target_height_px,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

                frames.append(scaled_pixmap)

        return frames

    # Frame Rendering

    def display_current_frame(self) -> None:
        if self.sequence_cursor_index >= len(self.active_frame_sequence):
            return

        frame_identifier = self.active_frame_sequence[self.sequence_cursor_index]

        if not (0 <= frame_identifier < len(self.frames)):
            return

        self.sprite_label.setPixmap(self.frames[frame_identifier])

    def display_scaled_approach_frame(
            self,
            frame_identifier: int,
            scale_ratio:      float
        ) -> None:

        if not (0 <= frame_identifier < len(self.frames)):
            return

        if scale_ratio <= 0.002:
            self.sprite_label.clear()
            return

        source_pixmap    = self.frames[frame_identifier]
        target_width_px  = max(1, int(source_pixmap.width() * scale_ratio))
        target_height_px = max(1, int(source_pixmap.height() * scale_ratio))

        scaled_pixmap    = source_pixmap.scaled(
            target_width_px,
            target_height_px,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self.sprite_label.setPixmap(scaled_pixmap)

    # Audio Feedback

    def play_clash_sound(self, deflect_sound: str) -> None:
        Player.ui_player.play_sound(deflect_sound)
        Player.ui_player.play_sound("Packs/NOK/MeleeWindowOpen")

    # Animation Helpers

    def animate_parry_deflect(self, phase_number: int) -> None:
        duration_ms = 450
        self.window_animator.start_visual_transformation(600)

        if phase_number == 1:
            self.window_animator.offset_x_handle.play_curve(
                [(0.0, -300.0), (1.0, 0.0)],
                duration_ms,
                LoomEngine.Easing.ease_out_expo
            )

            self.window_animator.scale_handle.play_curve(
                [(0.0, 1.3), (1.0, 1.0)],
                duration_ms,
                LoomEngine.Easing.bouncy
            )

        else:
            self.window_animator.offset_x_handle.play_curve(
                [(0.0, 300.0), (1.0, 0.0)],
                duration_ms,
                LoomEngine.Easing.ease_out_expo
            )

            self.window_animator.scale_handle.play_curve(
                [(0.0, 1.3), (1.0, 1.0)],
                duration_ms,
                LoomEngine.Easing.bouncy
            )

    def animate_victory_impact(self) -> None:
        duration_ms = 850
        self.window_animator.start_visual_transformation(1000)

        self.window_animator.rotation_z_handle.play_curve(
            [(0.0, float(random.randint(-30, 30))), (1.0, 0.0)],
            duration_ms,
            LoomEngine.Easing.bouncy
        )

        self.window_animator.scale_handle.play_curve(
            [(0.0, 1.5), (1.0, 1.0)],
            duration_ms,
            LoomEngine.Easing.bouncy
        )

    def animate_taunt_reaction(self, is_variant_a: bool) -> None:
        duration_ms     = random.randint(300, 450)
        target_offset_x = -300.0 if is_variant_a else 300.0

        self.window_animator.start_visual_transformation(1150)

        self.window_animator.offset_x_handle.play_curve(
            [(0.0, target_offset_x), (1.0, 0.0)],
            duration_ms,
            LoomEngine.Easing.ease_out_expo
        )

        self.window_animator.rotation_z_handle.play_curve(
            [(0.0, float(random.randint(-20, 20))), (1.0, 0.0)],
            duration_ms + 700,
            LoomEngine.Easing.bouncy
        )

    # Flash Effects

    def set_base_rectangle_color(
            self,
            red:   float,
            green: float,
            blue:  float
        ) -> None:

        self.base_rectangle_color = [red, green, blue]

        if self.flash_timer_ms <= 0.0:
            self.set_rect_color(red, green, blue, 1.0)

    def trigger_background_flash(
            self,
            red:         float,
            green:       float,
            blue:        float,
            duration_ms: float = 200.0
        ) -> None:

        self.flash_red         = red
        self.flash_green       = green
        self.flash_blue        = blue
        self.flash_duration_ms = duration_ms
        self.flash_timer_ms    = duration_ms

        self.set_rect_color(red, green, blue, 1.0)

    # Sequence Manager

    def launch_frame_sequence(
            self,
            state_name:   str,
            frame_series: list[int]
        ) -> None:

        self.current_state         = state_name
        self.active_frame_sequence = frame_series
        self.sequence_cursor_index = 0
        self.animation_timer_ms    = 0.0

        self.display_current_frame()

    def step_forward_sequence_frame(self) -> bool:
        if self.sequence_cursor_index + 1 < len(self.active_frame_sequence):
            self.sequence_cursor_index += 1

            if not self.game_over_active:
                self.display_current_frame()

            return False

        return True

    # Game Lifecycle

    def start_game(self) -> None:
        self.current_phase            = 1
        self.current_state            = "APPROACH"
        self.approach_timer_ms        = 0.0
        self.approach_elapsed_ms      = 0.0
        self.approach_frame_toggle    = False
        self.animation_timer_ms       = 0.0
        self.action_timer_ms          = 0.0
        self.flash_timer_ms           = 0.0
        self.next_taunt_is_variant_a  = True

        self.game_over_active         = False
        self.game_over_triggered      = False
        self.game_over_timer_ms       = 0.0

        self.scale_property.set_max_value(2.0)
        self.scale_property.set_target(1.0, duration_ms = 100)

        self.status_label.setText("He's coming...")
        self.display_scaled_approach_frame(self.frames_approach[0], 0.0)

        self.set_base_rectangle_color(0.17, 0.17, 0.17)
        self.set_border_color(0.25, 0.25, 0.25, 1.0)

        self.tick_timer.restart()

        if not self.game_timer.isActive():
            self.game_timer.start()

    def trigger_instant_taunt(self) -> None:
        self.animation_timer_ms = 0.0

        self.status_label.setText("Too early.")

        self.animate_taunt_reaction(self.next_taunt_is_variant_a)
        self.trigger_background_flash(1.00, 0.85, 0.15, 200.0)
        self.set_border_color(1.00, 0.70, 0.15, 1.0)

        if self.next_taunt_is_variant_a:
            self.play_clash_sound("Parry/MeleeDeflect1")
            self.launch_frame_sequence("TAUNT_SWING_A", self.frames_taunt_a)
            self.next_taunt_is_variant_a = False

        else:
            self.play_clash_sound("Parry/MeleeDeflect2")
            self.launch_frame_sequence("TAUNT_SWING_B", self.frames_taunt_b)
            self.next_taunt_is_variant_a = True

    def trigger_phase_failure(
            self,
            phase_number:    int,
            fail_state_name: str,
            fail_frames:     list[int],
            status_text:     str
        ) -> None:

        self.status_label.setText(status_text)
        self.set_base_rectangle_color(0.25, 0.10, 0.10)
        self.trigger_background_flash(1.00, 0.08, 0.08, 280.0)
        self.set_border_color(0.90, 0.20, 0.20, 1.0)

        self.launch_frame_sequence(fail_state_name, fail_frames)

    def trigger_phase_success(
            self,
            next_state_name: str,
            next_frames:     list[int],
            status_text:     str,
            deflect_sound:   str
        ) -> None:

        self.play_clash_sound(deflect_sound)
        self.status_label.setText(status_text)

        self.set_base_rectangle_color(0.17, 0.17, 0.17)
        self.trigger_background_flash(0.35, 1.00, 0.65, 240.0)
        self.set_border_color(0.25, 0.95, 0.45, 1.0)

        self.animate_parry_deflect(self.current_phase)
        self.wobble()
        self.launch_frame_sequence(next_state_name, next_frames)

    def trigger_final_victory(self) -> None:
        self.play_clash_sound("Parry/MeleeDeflect2")
        Player.ui_player.play_sound("Packs/NOK/Stab1")

        self.status_label.setText("Perfection.")

        self.set_base_rectangle_color(0.12, 0.22, 0.15)
        self.trigger_background_flash(0.85, 1.00, 0.90, 320.0)
        self.set_border_color(0.35, 1.00, 0.55, 1.0)

        self.animate_victory_impact()
        self.wobble()
        self.launch_frame_sequence("VICTORY", self.frames_victory)

    # Game Over Cinematic

    def start_game_over_sequence(self) -> None:
        self.game_over_active    = True
        self.game_over_triggered = True
        self.game_over_timer_ms  = 0.0

        Player.ui_player.play_sound("Packs/NOK/GameOver")

        self.scale_property.set_max_value(2.0)

        pulse_ratio = self.game_over_pulse_ms / self.game_over_duration_ms

        keyframes = [
            (0.0, 1.0),
            (pulse_ratio, 1.2),
            (1.0, 0.2)
        ]

        self.scale_property.play_curve(
            keyframes,
            int(self.game_over_duration_ms),
            LoomEngine.Easing.ease_out_cubic,
            multiply_duration_by_speed = False
        )

        self.configure_shake(35, 6.0)
        self.start_shake()

        QTimer.singleShot(int(self.game_over_duration_ms), self.finish_game_over_sequence)

    def process_game_over_effects(self, delta_ms: float) -> None:
        self.game_over_timer_ms += delta_ms

        elapsed_since_pulse = max(0.0, self.game_over_timer_ms - self.game_over_pulse_ms)
        fade_ratio          = min(1.0, elapsed_since_pulse / self.game_over_fade_duration_ms)
        character_scale     = max(0.0, 1.0 - fade_ratio)

        current_frame = self.active_frame_sequence[min(self.sequence_cursor_index, len(self.active_frame_sequence) - 1)]

        self.display_scaled_approach_frame(current_frame, character_scale)

        intensity_ratio = max(0.0, 1.0 - (self.game_over_timer_ms / self.game_over_duration_ms))

        jitter_offset_x = float(random.uniform(-0.15, 0.15) * intensity_ratio)
        jitter_offset_y = float(random.uniform(-0.15, 0.15) * intensity_ratio)
        jitter_angle_z  = float(random.uniform(-8.0, 8.0) * intensity_ratio)

        self.x_offset_property.set_target(jitter_offset_x, duration_ms = 40)
        self.y_offset_property.set_target(jitter_offset_y, duration_ms = 40)
        self.rotation_z_property.set_target(jitter_angle_z, duration_ms = 40)

    def finish_game_over_sequence(self) -> None:
        self.game_over_active = False

        self.stop_shake()
        self.reset_shake_parameters()

        self.x_offset_property.set_target(0.0, duration_ms = 150)
        self.y_offset_property.set_target(0.0, duration_ms = 150)
        self.rotation_z_property.set_target(0.0, duration_ms = 150)

        self.sprite_label.clear()
        self.status_label.setText("RMB to retry.")
        self.current_state = "STOPPED"

        Player.ui_player.play_sound("Packs/NOK/NewGame")

        self.scale_property.set_target(
            1.0,
            duration_ms                = 1200,
            easing_function            = LoomEngine.Easing.ease_out_quint,
            multiply_duration_by_speed = False
        )

    # State Processing

    def process_approach_state(self, delta_ms: float) -> None:
        self.approach_elapsed_ms += delta_ms
        self.approach_timer_ms   += delta_ms

        progress_ratio = min(1.0, self.approach_elapsed_ms / self.approach_duration_ms)
        current_scale  = progress_ratio

        if self.approach_timer_ms >= self.approach_step_ms:
            self.approach_timer_ms     -= self.approach_step_ms
            self.approach_frame_toggle  = not self.approach_frame_toggle

        active_frame = self.frames_approach[1] if self.approach_frame_toggle else self.frames_approach[0]
        self.display_scaled_approach_frame(active_frame, current_scale)

        if progress_ratio < 1.0:
            return

        Player.ui_player.play_sound("Packs/NOK/MeleeStart")
        self.status_label.setText("RMB to parry.")
        self.current_phase = 1
        self.launch_frame_sequence("SWING_1", self.frames_swing_one)

    def process_delay_state(
            self,
            delta_ms:        float,
            next_state_name: str
        ) -> None:

        self.action_timer_ms += delta_ms

        if self.action_timer_ms < self.parry_delay_ms:
            return

        self.current_state   = next_state_name
        self.action_timer_ms = 0.0

        self.set_base_rectangle_color(0.35, 0.12, 0.12)
        self.trigger_background_flash(0.95, 0.20, 0.20, 160.0)
        self.set_border_color(1.00, 0.25, 0.25, 1.0)

    def trigger_current_phase_failure(self, status_text: str) -> None:
        if self.current_phase == 1:
            self.trigger_phase_failure(1, "FAIL_1", self.frames_fail_one, status_text)

        elif self.current_phase == 2:
            self.trigger_phase_failure(2, "FAIL_2", self.frames_fail_two, status_text)

        else:
            self.trigger_phase_failure(3, "FAIL_3", self.frames_fail_three, status_text)

    def advance_game_tick(self) -> None:
        delta_ms = min(50.0, float(self.tick_timer.restart()))

        if self.flash_timer_ms > 0.0:
            self.flash_timer_ms = max(0.0, self.flash_timer_ms - delta_ms)
            flash_ratio         = self.flash_timer_ms / self.flash_duration_ms
            curve_ratio         = flash_ratio * flash_ratio

            current_red         = self.base_rectangle_color[0] + (self.flash_red - self.base_rectangle_color[0]) * curve_ratio
            current_green       = self.base_rectangle_color[1] + (self.flash_green - self.base_rectangle_color[1]) * curve_ratio
            current_blue        = self.base_rectangle_color[2] + (self.flash_blue - self.base_rectangle_color[2]) * curve_ratio

            self.set_rect_color(current_red, current_green, current_blue, 1.0)

        frame_interval_ms = 1000.0 / self.frames_per_second
        should_step_frame = False

        self.animation_timer_ms += delta_ms

        if self.animation_timer_ms >= frame_interval_ms:
            self.animation_timer_ms -= frame_interval_ms
            should_step_frame        = True

        if self.current_state in ("APPROACH", "STOPPED"):
            if self.current_state == "APPROACH":
                self.process_approach_state(delta_ms)

            return

        if self.current_state == "SWING_1":
            self.current_phase = 1

            if should_step_frame and self.step_forward_sequence_frame():
                self.current_state   = "DELAY_1"
                self.action_timer_ms = 0.0
                self.set_base_rectangle_color(0.24, 0.20, 0.12)
                self.set_border_color(0.95, 0.80, 0.20, 1.0)

        elif self.current_state == "DELAY_1":
            self.process_delay_state(delta_ms, "WINDOW_1")

        elif self.current_state == "WINDOW_1":
            self.action_timer_ms += delta_ms

            if self.action_timer_ms >= self.parry_window_ms:
                self.trigger_phase_failure(1, "FAIL_1", self.frames_fail_one, "Loser.")

        elif self.current_state == "SWING_2":
            self.current_phase = 2

            if should_step_frame and self.step_forward_sequence_frame():
                self.current_state   = "DELAY_2"
                self.action_timer_ms = 0.0
                self.set_base_rectangle_color(0.24, 0.20, 0.12)
                self.set_border_color(0.95, 0.80, 0.20, 1.0)

        elif self.current_state == "DELAY_2":
            self.process_delay_state(delta_ms, "WINDOW_2")

        elif self.current_state == "WINDOW_2":
            self.action_timer_ms += delta_ms

            if self.action_timer_ms >= self.parry_window_ms:
                self.trigger_phase_failure(2, "FAIL_2", self.frames_fail_two, "Loser.")

        elif self.current_state == "SWING_3":
            self.current_phase = 3

            if should_step_frame and self.step_forward_sequence_frame():
                self.current_state   = "DELAY_3"
                self.action_timer_ms = 0.0
                self.set_base_rectangle_color(0.24, 0.20, 0.12)
                self.set_border_color(0.95, 0.80, 0.20, 1.0)

        elif self.current_state == "DELAY_3":
            self.process_delay_state(delta_ms, "WINDOW_3")

        elif self.current_state == "WINDOW_3":
            self.action_timer_ms += delta_ms

            if self.action_timer_ms >= self.parry_window_ms:
                self.trigger_phase_failure(3, "FAIL_3", self.frames_fail_three, "Loser.")

        elif self.current_state == "TAUNT_SWING_A":
            if should_step_frame and self.step_forward_sequence_frame():
                self.current_state   = "DELAY_TAUNT_A"
                self.action_timer_ms = 0.0
                self.set_base_rectangle_color(0.24, 0.20, 0.12)
                self.set_border_color(0.95, 0.80, 0.20, 1.0)

        elif self.current_state == "DELAY_TAUNT_A":
            self.process_delay_state(delta_ms, "WINDOW_TAUNT_A")

        elif self.current_state == "WINDOW_TAUNT_A":
            self.action_timer_ms += delta_ms

            if self.action_timer_ms >= self.parry_window_ms:
                self.trigger_current_phase_failure("Loser.")

        elif self.current_state == "TAUNT_SWING_B":
            if should_step_frame and self.step_forward_sequence_frame():
                self.current_state   = "DELAY_TAUNT_B"
                self.action_timer_ms = 0.0
                self.set_base_rectangle_color(0.24, 0.20, 0.12)
                self.set_border_color(0.95, 0.80, 0.20, 1.0)

        elif self.current_state == "DELAY_TAUNT_B":
            self.process_delay_state(delta_ms, "WINDOW_TAUNT_B")

        elif self.current_state == "WINDOW_TAUNT_B":
            self.action_timer_ms += delta_ms

            if self.action_timer_ms >= self.parry_window_ms:
                self.trigger_current_phase_failure("Loser.")

        elif self.current_state in ("FAIL_1", "FAIL_2", "FAIL_3"):
            if should_step_frame:
                has_finished_sequence = self.step_forward_sequence_frame()

                if has_finished_sequence and not self.game_over_active:
                    self.current_state = "STOPPED"
                    self.status_label.setText("Loser.")

            middle_threshold = len(self.active_frame_sequence) // 2

            if not self.game_over_triggered and self.sequence_cursor_index >= middle_threshold:
                self.start_game_over_sequence()

        elif self.current_state == "VICTORY":
            if should_step_frame and self.step_forward_sequence_frame():
                self.current_state = "STOPPED"
                self.status_label.setText("Flawless.")

        if self.game_over_active:
            self.process_game_over_effects(delta_ms)

    # Input Handling

    def handle_parry_action(self) -> None:
        if self.game_over_active or self.current_state in ("APPROACH", "STOPPED"):
            return

        if self.current_state in (
            "SWING_1",
            "DELAY_1",
            "SWING_2",
            "DELAY_2",
            "SWING_3",
            "DELAY_3",
            "TAUNT_SWING_A",
            "DELAY_TAUNT_A",
            "TAUNT_SWING_B",
            "DELAY_TAUNT_B"
        ):
            self.trigger_instant_taunt()
            return

        if self.current_state == "WINDOW_1":
            self.current_phase = 2
            self.trigger_phase_success("SWING_2", self.frames_swing_two, "Deflected! Focus!", "Parry/MeleeDeflect1")
            return

        if self.current_state == "WINDOW_2":
            self.current_phase = 3
            self.trigger_phase_success("SWING_3", self.frames_swing_three, "Final strike! Strike now!", "Parry/MeleeDeflect2")
            return

        if self.current_state == "WINDOW_3":
            self.trigger_final_victory()
            return

        if self.current_state in ("WINDOW_TAUNT_A", "WINDOW_TAUNT_B"):
            if self.current_phase == 1:
                self.current_phase = 2
                self.trigger_phase_success("SWING_2", self.frames_swing_two, "Deflected! Focus!", "Parry/MeleeDeflect1")

            elif self.current_phase == 2:
                self.current_phase = 3
                self.trigger_phase_success("SWING_3", self.frames_swing_three, "Final strike! Strike now!", "Parry/MeleeDeflect2")

            else:
                self.trigger_final_victory()

    # Event Handlers

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.RightButton:
            super().mousePressEvent(event)
            return

        event.accept()

        if self.current_state == "STOPPED" and not self.game_over_active:
            self.start_game()
            return

        self.handle_parry_action()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.isAutoRepeat():
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key.Key_Space:
            event.accept()

            if self.current_state == "STOPPED" and not self.game_over_active:
                self.start_game()
                return

            self.handle_parry_action()
            return

        if event.key() == Qt.Key.Key_R:
            event.accept()

            if not self.game_over_active:
                self.start_game()

            return

        if event.key() == Qt.Key.Key_Escape:
            event.accept()
            self.on_cancel()
            return

        super().keyPressEvent(event)

    def really_close(self) -> None:
        if self.game_timer.isActive():
            self.game_timer.stop()

        super().really_close()