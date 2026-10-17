from __future__ import annotations

import math
import random

from System.Services import Player

# Base Anomaly Effect

class AnomalyEffect:
    def __init__(self, duration_seconds: float) -> None:
        self.duration_seconds: float = duration_seconds
        self.elapsed_seconds:  float = 0.0

    def compute_bell_envelope(self) -> float:
        normalized_progress = min(1.0, self.elapsed_seconds / max(0.001, self.duration_seconds))
        return math.sin(normalized_progress * math.pi)

    def update(
            self,
            manager:            AnomalyEventManager,
            delta_time_seconds: float
        ) -> bool:

        self.elapsed_seconds += delta_time_seconds
        return self.elapsed_seconds >= self.duration_seconds

# Specialized Anomaly Effects

class SubtleDerealizationEffect(AnomalyEffect):
    def update(
            self,
            manager:            AnomalyEventManager,
            delta_time_seconds: float
        ) -> bool:

        super().update(manager, delta_time_seconds)
        bell_envelope = self.compute_bell_envelope()

        target_derealization            = bell_envelope * 0.55
        manager.derealization_intensity += (target_derealization - manager.derealization_intensity) * min(1.0, delta_time_seconds * 3.5)
        manager.vertigo_fov_offset      *= 0.88
        manager.vertigo_roll_offset     *= 0.88

        return self.elapsed_seconds >= self.duration_seconds


class MildVertigoEffect(AnomalyEffect):
    def update(
            self,
            manager:            AnomalyEventManager,
            delta_time_seconds: float
        ) -> bool:

        super().update(manager, delta_time_seconds)
        bell_envelope = self.compute_bell_envelope()

        manager.derealization_intensity = max(0.0, manager.derealization_intensity - delta_time_seconds * 0.5)
        vertigo_wave                    = math.sin(self.elapsed_seconds * 2.2) * bell_envelope
        manager.vertigo_fov_offset      = vertigo_wave * 4.5
        manager.vertigo_roll_offset     = math.cos(self.elapsed_seconds * 1.7) * bell_envelope * 2.2

        return self.elapsed_seconds >= self.duration_seconds


class CombinedLobotomyEffect(AnomalyEffect):
    def update(
            self,
            manager:            AnomalyEventManager,
            delta_time_seconds: float
        ) -> bool:

        super().update(manager, delta_time_seconds)
        bell_envelope = self.compute_bell_envelope()

        target_derealization            = bell_envelope * 0.48
        manager.derealization_intensity += (target_derealization - manager.derealization_intensity) * min(1.0, delta_time_seconds * 3.5)
        vertigo_wave                    = math.sin(self.elapsed_seconds * 1.9) * bell_envelope
        manager.vertigo_fov_offset      = vertigo_wave * 3.8
        manager.vertigo_roll_offset     = math.cos(self.elapsed_seconds * 1.5) * bell_envelope * 1.8

        return self.elapsed_seconds >= self.duration_seconds


class LobotomyPulseEffect(AnomalyEffect):
    def __init__(self, duration_seconds: float) -> None:
        super().__init__(duration_seconds)
        self.pulse_rate:  float = random.uniform(5.0, 8.0)
        self.phase_offset: float = random.uniform(0.0, math.tau)

    def update(
            self,
            manager:            AnomalyEventManager,
            delta_time_seconds: float
        ) -> bool:

        super().update(manager, delta_time_seconds)
        bell_envelope = self.compute_bell_envelope()
        pulse_strength = 0.25 + 0.75 * abs(math.sin(self.elapsed_seconds * self.pulse_rate + self.phase_offset))

        manager.lobotomy_intensity = bell_envelope * pulse_strength * 0.72
        manager.vertigo_roll_offset = math.sin(self.elapsed_seconds * 2.0 + self.phase_offset) * bell_envelope * 1.1

        return self.elapsed_seconds >= self.duration_seconds


class HeavyEyelidsEffect(AnomalyEffect):
    def __init__(self, duration_seconds: float) -> None:
        super().__init__(duration_seconds)
        self.maximum_eyelid_factor: float = random.uniform(0.55, 0.82)

    def update(
            self,
            manager:            AnomalyEventManager,
            delta_time_seconds: float
        ) -> bool:

        super().update(manager, delta_time_seconds)
        bell_envelope = self.compute_bell_envelope()
        manager.heavy_eyelids_intensity = bell_envelope * self.maximum_eyelid_factor
        manager.derealization_intensity = max(manager.derealization_intensity, bell_envelope * 0.18)

        return self.elapsed_seconds >= self.duration_seconds


class ColdBloomEffect(AnomalyEffect):
    def __init__(self, duration_seconds: float) -> None:
        super().__init__(duration_seconds)
        self.pulse_rate: float = random.uniform(2.5, 4.5)
        self.phase_offset: float = random.uniform(0.0, math.tau)

    def update(
            self,
            manager:            AnomalyEventManager,
            delta_time_seconds: float
        ) -> bool:

        super().update(manager, delta_time_seconds)
        bell_envelope = self.compute_bell_envelope()
        pulse_strength = 0.65 + 0.35 * abs(math.sin(self.elapsed_seconds * self.pulse_rate + self.phase_offset))

        manager.cold_desaturation_intensity = bell_envelope * 0.72
        manager.white_bloom_intensity = bell_envelope * pulse_strength * 0.36

        return self.elapsed_seconds >= self.duration_seconds


class RealityTearEffect(AnomalyEffect):
    def __init__(self, duration_seconds: float) -> None:
        super().__init__(duration_seconds)
        self.pulse_rate: float = random.uniform(7.0, 11.0)
        self.phase_offset: float = random.uniform(0.0, math.tau)

    def update(
            self,
            manager:            AnomalyEventManager,
            delta_time_seconds: float
        ) -> bool:

        super().update(manager, delta_time_seconds)
        bell_envelope = self.compute_bell_envelope()
        tear_pulse = 0.45 + 0.55 * abs(math.sin(self.elapsed_seconds * self.pulse_rate + self.phase_offset))

        manager.reality_tear_intensity = bell_envelope * tear_pulse * 0.68
        manager.derealization_intensity = max(manager.derealization_intensity, bell_envelope * 0.3)

        return self.elapsed_seconds >= self.duration_seconds


class BlackoutEffect(AnomalyEffect):
    def __init__(self, duration_seconds: float) -> None:
        super().__init__(duration_seconds)
        self.sound_played: bool = False

    def update(
            self,
            manager:            AnomalyEventManager,
            delta_time_seconds: float
        ) -> bool:

        if not self.sound_played:
            self.sound_played = True
            Player.ui_player.play_sound(".vault/Anomaly/SparkPop", volume = 0.9)

        super().update(manager, delta_time_seconds)
        manager.blackout_active = True

        return self.elapsed_seconds >= self.duration_seconds

# Anomaly Event Manager

class AnomalyEventManager:
    def __init__(self) -> None:
        self.next_event_timer_seconds: float                = random.uniform(22.0, 42.0)
        self.active_effect:            AnomalyEffect | None = None
        self.derealization_intensity:  float                = 0.0
        self.vertigo_fov_offset:       float                = 0.0
        self.vertigo_roll_offset:      float                = 0.0
        self.lobotomy_intensity:       float                = 0.0
        self.heavy_eyelids_intensity:  float                = 0.0
        self.white_bloom_intensity:    float                = 0.0
        self.cold_desaturation_intensity: float              = 0.0
        self.reality_tear_intensity:   float                = 0.0
        self.blackout_active:          bool                 = False

    def update(self, delta_time_seconds: float) -> None:
        self.blackout_active = False

        if self.active_effect is not None:
            is_finished = self.active_effect.update(self, delta_time_seconds)

            if is_finished:
                if isinstance(self.active_effect, BlackoutEffect):
                    Player.ui_player.play_sound(".vault/Anomaly/SparkPop", volume = 0.6)

                self.active_effect = None

            return

        self.next_event_timer_seconds -= delta_time_seconds

        if self.next_event_timer_seconds <= 0.0:
            self.next_event_timer_seconds = random.uniform(25.0, 50.0)
            chosen_effect_class           = random.choice([
                SubtleDerealizationEffect,
                MildVertigoEffect,
                CombinedLobotomyEffect,
                LobotomyPulseEffect,
                HeavyEyelidsEffect,
                ColdBloomEffect,
                RealityTearEffect,
                BlackoutEffect
            ])
            if chosen_effect_class == BlackoutEffect:
                effect_duration = random.uniform(5.5, 9.5)
            elif chosen_effect_class in (LobotomyPulseEffect, HeavyEyelidsEffect, ColdBloomEffect, RealityTearEffect):
                effect_duration = random.uniform(3.5, 7.0)
            else:
                effect_duration = random.uniform(7.0, 14.0)

            self.active_effect = chosen_effect_class(effect_duration)

        self.derealization_intensity = max(0.0, self.derealization_intensity - delta_time_seconds * 0.4)
        self.vertigo_fov_offset      *= 0.88
        self.vertigo_roll_offset     *= 0.88