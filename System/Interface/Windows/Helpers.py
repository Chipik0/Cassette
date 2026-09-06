from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout
)

from System.Common import Styles

from System.Interface import (
    Labels,
    Textboxes
)

# Helpers

def build_column(
        title:   str,
        widgets: list[QWidget]
    ) -> QVBoxLayout:
    
    column = QVBoxLayout()
    column.addWidget(Labels.DescriptionLabel(title))

    for widget in widgets:
        column.addWidget(widget)

    column.addStretch()

    return column

def make_time_textbox() -> Textboxes.Textbox:
    textbox = Textboxes.Textbox(":time", max_length = 5)
    textbox.setStyleSheet(Styles.Controls.FloatingTextBox)
    textbox.setFixedHeight(32)
    textbox.setFixedWidth(56)

    return textbox

def make_fade_textbox(placeholder: str) -> Textboxes.Textbox:
    textbox = Textboxes.Textbox("number", 0, 5000, placeholder = placeholder)
    textbox.setStyleSheet(Styles.Controls.FloatingTextBox)
    textbox.setFixedHeight(32)

    return textbox