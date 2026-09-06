from PyQt6.QtWidgets import QWidget

from System.Interface import (
    Buttons,
    Widgets
)

from System.Interface.Windows.FloatingWindowGPU import FloatingWindowGPU

# Segment Editor

class SegmentEditor(FloatingWindowGPU):
    def __init__(
            self,
            title:          str,
            segment_number: int     | None = None,
            defaults:       list    | None = None,
            parent:         QWidget | None = None
        ) -> None:

        super().__init__(title, parent = parent)

        self.segmented_bar = Widgets.SegmentedBar(segment_number, defaults)

        upper_button_row = Buttons.ButtonRow(
            [
                (Buttons.ButtonWithOutline, "Enable all",  self.segmented_bar.enable_all),
                (Buttons.ButtonWithOutline, "Disable all", self.segmented_bar.disable_all),
                (Buttons.ButtonWithOutline, "Zebra",       self.segmented_bar.zebra)
            ]
        )

        lower_button_row = Buttons.ButtonRow(
            [
                (Buttons.ButtonWithOutline, "Nah",   self.on_cancel),
                (Buttons.NothingButton,     "Apply", self.on_ok)
            ]
        )

        self.content_layout.addWidget(self.segmented_bar)
        self.content_layout.addLayout(upper_button_row)
        self.content_layout.addLayout(lower_button_row)

        self.segmented_bar.segment_changed.connect(self.wobble)

    def segments(self) -> list:
        return self.segmented_bar.active