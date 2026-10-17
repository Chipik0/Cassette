from __future__ import annotations

import math
import random

# Lobotomy and Anomaly Event Manager

class AnomalyEventManager:
    def __init__(self) -> None:
        self.next_event_timer_seconds: float = random.uniform(18.0, 36.0)
        self.current_event_type:       str   = "NONE"
        self.event_duration_seconds:   float = 0.0
        self.event_elapsed_seconds:    float = 0.0

        self.derealization_intensity:  float = 0.0
        self.vertigo_fov_offset:       float = 0.0
        self.vertigo_roll_offset:      float = 0.0

    def trigger_subtle_derealization(self, duration_seconds: float = 8.0) -> None:
        self.current_event_type     = "SUBTLE_DEREALIZATION"
        self.event_duration_seconds = duration_seconds
        self.event_elapsed_seconds  = 0.0

    def trigger_mild_vertigo(self, duration_seconds: float = 7.0) -> None:
        self.current_event_type     = "MILD_VERTIGO"
        self.event_duration_seconds = duration_seconds
        self.event_elapsed_seconds  = 0.0

    def trigger_combined_lobotomy(self, duration_seconds: float = 10.0) -> None:
        self.current_event_type     = "COMBINED_LOBOTOMY"
        self.event_duration_seconds = duration_seconds
        self.event_elapsed_seconds  = 0.0

    def update(self, delta_time: float) -> None:
        if self.current_event_type == "NONE":
            self.next_event_timer_seconds -= delta_time

            if self.next_event_timer_seconds <= 0.0:
                self.next_event_timer_seconds = random.uniform(22.0, 48.0)
                selected_anomaly_event        = random.choice(["SUBTLE_DEREALIZATION", "MILD_VERTIGO", "COMBINED_LOBOTOMY"])

                if selected_anomaly_event == "SUBTLE_DEREALIZATION":
                    self.trigger_subtle_derealization(random.uniform(7.0, 12.0))

                elif selected_anomaly_event == "MILD_VERTIGO":
                    self.trigger_mild_vertigo(random.uniform(6.0, 10.0))

                elif selected_anomaly_event == "COMBINED_LOBOTOMY":
                    self.trigger_combined_lobotomy(random.uniform(9.0, 14.0))

            self.derealization_intensity = max(0.0, self.derealization_intensity - delta_time * 0.4)
            self.vertigo_fov_offset      *= 0.88
            self.vertigo_roll_offset     *= 0.88
            return

        self.event_elapsed_seconds += delta_time
        normalized_progress         = min(1.0, self.event_elapsed_seconds / self.event_duration_seconds)
        bell_envelope               = math.sin(normalized_progress * math.pi)

        if self.current_event_type == "SUBTLE_DEREALIZATION":
            target_derealization            = bell_envelope * 0.55
            self.derealization_intensity    += (target_derealization - self.derealization_intensity) * min(1.0, delta_time * 3.5)
            self.vertigo_fov_offset         *= 0.88
            self.vertigo_roll_offset        *= 0.88

        elif self.current_event_type == "MILD_VERTIGO":
            self.derealization_intensity = max(0.0, self.derealization_intensity - delta_time * 0.5)
            vertigo_wave                 = math.sin(self.event_elapsed_seconds * 2.2) * bell_envelope
            self.vertigo_fov_offset      = vertigo_wave * 4.5
            self.vertigo_roll_offset     = math.cos(self.event_elapsed_seconds * 1.7) * bell_envelope * 2.2

        elif self.current_event_type == "COMBINED_LOBOTOMY":
            target_derealization         = bell_envelope * 0.48
            self.derealization_intensity += (target_derealization - self.derealization_intensity) * min(1.0, delta_time * 3.5)
            vertigo_wave                 = math.sin(self.event_elapsed_seconds * 1.9) * bell_envelope
            self.vertigo_fov_offset      = vertigo_wave * 3.8
            self.vertigo_roll_offset     = math.cos(self.event_elapsed_seconds * 1.5) * bell_envelope * 1.8

        if self.event_elapsed_seconds >= self.event_duration_seconds:
            self.current_event_type    = "NONE"
            self.event_elapsed_seconds = 0.0