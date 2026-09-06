import random

from PyQt6.QtWidgets import QWidget

from System.Common    import Constants
from System.Interface import Buttons

from System.Interface.Windows.FloatingWindowGPU import FloatingWindowGPU

# Dialog Window

class DialogWindow(FloatingWindowGPU):
    def __init__(
            self,
            title:  str,
            parent: QWidget | None = None
        ) -> None:
        super().__init__(title, parent = parent)

        button_row = Buttons.ButtonRow(
            [
                (Buttons.ButtonWithOutline, random.choice(Constants.NO_TEXTS), self.on_cancel),
                (Buttons.NothingButton,     random.choice(Constants.OK_TEXTS), self.on_ok)
            ]
        )

        self.content_layout.addLayout(button_row)