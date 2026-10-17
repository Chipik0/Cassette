from __future__ import annotations

import random
from dataclasses import dataclass

from System.Services import Player

# Lamp Particle Definition

@dataclass
class LampSparkParticle:
    position_x:                  float
    position_y:                  float
    position_z:                  float
    velocity_x:                  float
    velocity_y:                  float
    velocity_z:                  float
    life_seconds:                float
    total_life_duration_seconds: float

# Base Lamp Class

class FluorescentLamp:
    def __init__(
            self,
            position_x: float,
            position_z: float
        ) -> None:

        self.position_x:         float                   = position_x
        self.position_z:         float                   = position_z
        self.is_broken:          bool                    = False
        self.flicker_factor:     float                   = 1.0
        self.active_sparks_list: list[LampSparkParticle] = []

    def update(
            self,
            delta_time_seconds:   float,
            audio_pan_calculator: object,
            ceiling_height:       float,
            distance_to_player:   float
        ) -> bool:

        return False

    def spawn_burst_sparks(self, elevation_y: float) -> None:
        spark_count = random.randint(22, 35)

        for _ in range(spark_count):
            particle_life = random.uniform(0.45, 0.85)
            self.active_sparks_list.append(
                LampSparkParticle(
                    position_x                  = self.position_x + random.uniform(-0.25, 0.25),
                    position_y                  = elevation_y,
                    position_z                  = self.position_z + random.uniform(-0.65, 0.65),
                    velocity_x                  = random.uniform(-1.8, 1.8),
                    velocity_y                  = random.uniform(-0.5, 1.2),
                    velocity_z                  = random.uniform(-1.8, 1.8),
                    life_seconds                = particle_life,
                    total_life_duration_seconds = particle_life
                )
            )

# Specialized Lamp Subclasses

class StandardLamp(FluorescentLamp):
    def update(
            self,
            delta_time_seconds:   float,
            audio_pan_calculator: object,
            ceiling_height:       float,
            distance_to_player:   float
        ) -> bool:

        self.flicker_factor = 1.0
        return False


class FlickeringLamp(FluorescentLamp):
    def __init__(
            self,
            position_x: float,
            position_z: float
        ) -> None:

        super().__init__(position_x, position_z)
        self.flicker_timer_seconds: float = random.uniform(0.0, 5.0)

    def update(
            self,
            delta_time_seconds:   float,
            audio_pan_calculator: object,
            ceiling_height:       float,
            distance_to_player:   float
        ) -> bool:

        self.flicker_timer_seconds += delta_time_seconds

        if random.random() < 0.12:
            self.flicker_factor = random.uniform(0.05, 0.45)

        else:
            self.flicker_factor = min(1.0, self.flicker_factor + delta_time_seconds * 8.0)

        return False


class BlinkingLamp(FluorescentLamp):
    def __init__(
            self,
            position_x: float,
            position_z: float
        ) -> None:

        super().__init__(position_x, position_z)

        self.switch_timer_seconds: float = random.uniform(1.0, 3.5)
        self.is_illuminated:       bool  = True
        self.flicker_factor:       float = 1.0

    def update(
            self,
            delta_time_seconds:   float,
            audio_pan_calculator: object,
            ceiling_height:       float,
            distance_to_player:   float
        ) -> bool:

        self.switch_timer_seconds -= delta_time_seconds

        if self.switch_timer_seconds > 0.0:
            return False

        self.is_illuminated = not self.is_illuminated
        self.flicker_factor = 1.0 if self.is_illuminated else 0.0

        if self.is_illuminated:
            self.switch_timer_seconds = random.choice([
                random.uniform(1.4, 4.0),
                random.uniform(0.15, 0.45)
            ])

        else:
            self.switch_timer_seconds = random.choice([
                random.uniform(0.6, 2.2),
                random.uniform(0.08, 0.25)
            ])

        return True


class PoppingLamp(FluorescentLamp):
    def __init__(
            self,
            position_x: float,
            position_z: float
        ) -> None:

        super().__init__(position_x, position_z)
        self.pop_countdown_seconds: float = random.uniform(2.5, 5.5)
        self.trigger_distance:      float = 6.0
        self.is_triggered:          bool  = False

    def update(
            self,
            delta_time_seconds:   float,
            audio_pan_calculator: object,
            ceiling_height:       float,
            distance_to_player:   float
        ) -> bool:

        if self.is_broken:
            return False

        if distance_to_player > self.trigger_distance and not self.is_triggered:
            return False

        if distance_to_player <= self.trigger_distance:
            self.is_triggered = True

        if not self.is_triggered or distance_to_player > self.trigger_distance:
            return False

        self.pop_countdown_seconds -= delta_time_seconds

        if self.pop_countdown_seconds <= 1.5:
            self.flicker_factor = random.choice([0.1, 0.9, 0.0, 1.2])

        if self.pop_countdown_seconds <= 0.0:
            self.is_broken      = True
            self.flicker_factor = 0.0
            self.spawn_burst_sparks(ceiling_height - 0.09)

            calculated_pan = audio_pan_calculator(self.position_x, self.position_z)
            Player.ui_player.play_sound(
                ".vault/Anomaly/SparkPop",
                volume = 0.95,
                pan    = calculated_pan
            )
            return True

        return False

# Lamp Factory

AVAILABLE_LAMP_CLASSES = [
    StandardLamp,
    StandardLamp,
    FlickeringLamp,
    FlickeringLamp,
    BlinkingLamp,
    BlinkingLamp,
    PoppingLamp
]

def instantiate_random_lamp(
        position_x: float,
        position_z: float
    ) -> FluorescentLamp:

    lamp_class = random.choice(AVAILABLE_LAMP_CLASSES)
    return lamp_class(position_x, position_z)