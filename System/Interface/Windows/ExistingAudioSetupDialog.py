from __future__ import annotations

import os
import re

from PyQt6.QtCore import Qt

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout
)

from System.Services import (
    Player,
    ProjectSaver
)

from System.Interface import Widgets

from System.Interface.Windows import (
    BPMEditorBase,
    TrimWarningDialog
)

# Existing Audio Setup Dialog

class ExistingAudioSetupDialog(BPMEditorBase):
    def __init__(
            self,
            composition: ProjectSaver.Composition,
            parent:      QWidget | None = None
        ) -> None:

        self.composition        = composition
        self.audio_path         = composition.full_song_path
        self.filename           = os.path.basename(self.audio_path)
        self.saved_settings     = {}
        self.auto_bpm_requested = False

        super().__init__(
            "Audio",
            parent                     = parent,
            max_tilt_angle             = 14,
            enable_audioplayer_effects = False
        )

        self.title_label.setText(self.filename)
        self.setup_audio_layout()

        if self.composition.bpm:
            self.apply_saved_bpm_state()

        self.run_loading_pipeline(self.audio_path)
        self.adjustSize()

    # Layout Setup

    def setup_audio_layout(self) -> None:
        self.setup_trim_section()
        self.setup_bpm_section()
        self.setup_action_buttons("Ok", "Cancel")

        self.ok_button.setMaximumWidth(56)
        self.cancel_button.setMaximumWidth(80)

        self.auto_bpm_button = Widgets.ButtonWithOutline("Auto", enable_glitch_effect = False)
        self.auto_bpm_button.setMaximumWidth(80)
        self.auto_bpm_button.clicked.connect(self.on_auto_detect_bpm)

        bpm_layout = QHBoxLayout()
        bpm_layout.addWidget(self.bpm_input)
        bpm_layout.addWidget(self.auto_bpm_button)

        settings_layout = QHBoxLayout()
        settings_layout.addLayout(bpm_layout)
        settings_layout.addStretch()
        settings_layout.addWidget(self.cancel_button)
        settings_layout.addWidget(self.ok_button)

        self.content_layout.addWidget(self.trim_widget)
        self.content_layout.addLayout(self.build_playback_row())
        self.content_layout.addLayout(settings_layout)

    # Width Calculation

    def calculate_collapsed_width(
            self,
            bpm_text: str
        ) -> int:

        clean_text   = str(bpm_text or "").strip() or "120"
        font_metrics = self.bpm_input.fontMetrics()

        return max(font_metrics.horizontalAdvance(clean_text) + 26, 56)

    # BPM State Management

    def apply_bpm(
            self,
            bpm_value: int
        ) -> None:

        bpm_text     = str(bpm_value)
        target_width = self.calculate_collapsed_width(bpm_text)

        self.bpm_animation_timer.stop()
        self.bpm_remove_timer.stop()

        self.bpm_input.setText(bpm_text)
        self.bpm_input.setPlaceholderText("BPM")
        self.bpm_input.setFixedWidth(target_width)
        self.bpm_input.setAlignment(Qt.AlignmentFlag.AlignCenter)

        Player.bpm_informer.set_bpm(int(bpm_value))

    def apply_saved_bpm_state(self) -> None:
        self.apply_bpm(int(self.composition.bpm))

    def apply_auto_bpm(
            self,
            bpm_value: int
        ) -> None:

        self.auto_bpm_requested = False
        self.apply_bpm(bpm_value)

    # BPM Pipeline Handlers

    def bpm_ready(
            self,
            bpm:           float,
            snapped_times: list | None
        ) -> None:

        self.snapped_times = snapped_times
        self.bpm_animation_timer.stop()

        if not bpm:
            self.detected_bpm = None

            if self.auto_bpm_requested:
                self.auto_bpm_requested = False
                self.bpm_input.setPlaceholderText("Counting BPM FAILURE")

            return

        bpm_value         = round(bpm)
        self.detected_bpm = bpm_value

        if self.auto_bpm_requested:
            self.apply_auto_bpm(bpm_value)

    def on_auto_detect_bpm(self) -> None:
        if self.detected_bpm is not None and self.get_bpm_value() == self.detected_bpm:
            self.auto_bpm_button.start_glitch()
            self.bpm_input.start_glitch()
            return

        if self.detected_bpm is not None:
            self.apply_auto_bpm(self.detected_bpm)
            return

        self.auto_bpm_requested = True

        self.bpm_input.setText("")
        self.bpm_input.setPlaceholderText("Counting BPM...")
        self.bpm_input.setFixedWidth(130)

        if not self.is_bpm_thread_running():
            self.start_bpm_pipeline()

        self.bpm_animation_timer.start()

    # Audio Pipeline Handlers

    def on_audio_ready(self) -> None:
        super().on_audio_ready()

        current_start = float(self.composition.start_ms or 0) / 1000.0
        current_end   = float(self.composition.end_ms) / 1000.0 if self.composition.end_ms is not None else self.trim_widget.duration_sec

        self.trim_widget.set_times(current_start, current_end)
        self.update_textboxes(current_start, current_end)

        self.fade_in_textbox.setText(str(self.composition.fade_in_duration or 0))
        self.fade_out_textbox.setText(str(self.composition.fade_out_duration or 0))

        if self.composition.bpm and not self.auto_bpm_requested:
            self.apply_saved_bpm_state()

    # Value Retrieval

    def get_bpm_value(self) -> int:
        clean_text = str(self.bpm_input.text() or "").strip()

        if clean_text.isdigit():
            return int(clean_text)

        placeholder_text = str(self.bpm_input.placeholderText() or "")
        digits           = re.findall(r"(\d+)", placeholder_text)

        if digits:
            return int(digits[-1])

        return int(self.composition.bpm or 120)

    # Actions

    def accept_callback(self) -> None:
        if not self.validate_trim():
            self.ok_button.start_glitch()
            return

        trim_settings       = self.get_trim_settings()
        removed_glyph_count = self.composition.count_glyphs_outside_range(
            int(trim_settings["start_ms"]),
            int(trim_settings["end_ms"])
        )

        if removed_glyph_count > 0 and not TrimWarningDialog(removed_glyph_count).exec():
            return

        self.saved_settings = {
            **trim_settings,
            **self.get_bpm_settings()
        }

        self.cleanup_audio()
        super().on_ok()