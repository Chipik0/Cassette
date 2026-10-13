from __future__ import annotations

import sys
import random
import platform
import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtGui  import QPixmap

from PyQt6.QtWidgets import (
    QLabel,
    QWidget
)

from System.Common import (
    Utils,
    Constants
)

from System.Interface import Widgets

from System.Interface.Windows import (
    ErrorWindow,
    UpdateWindow,
    FeedbackWindow,
    FloatingWindowGPU
)

# About Window

class AboutWindow(FloatingWindowGPU):
    def __init__(
            self,
            more_info: bool           = False,
            parent:    QWidget | None = None
        ) -> None:

        with open(Utils.get_resource_path("version"), "r", encoding = "utf-8") as version_file:
            version_text = version_file.read().strip()

        super().__init__(
            f"Cassette {version_text} by chips047",
            parent                     = parent,
            enable_audioplayer_effects = False
        )

        self.update_checker = None

        if more_info:
            text = (
                f"System {sys.platform} {platform.machine()}\n"
                f"Python: {sys.version}"
            )

        else:
            text = open("System/Assets/About.txt", "r", encoding = "utf-8").read()

        about_label = Widgets.DescriptionLabel(text, 500)

        image_pixmap = QPixmap("System/Assets/Image/Version.png").scaled(
            500, 500,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        image_label = QLabel()
        image_label.setPixmap(image_pixmap)

        self.button_row = Widgets.ButtonRow(
            [
                (Widgets.ButtonWithOutline, "GitHub",        self.on_github),
                (Widgets.ButtonWithOutline, "Feedback",      self.on_feedback),
                (Widgets.ButtonWithOutline, "Check updates", self.on_check_updates)
            ]
        )

        ok_button = Widgets.NothingButton("Five Stars?")
        ok_button.clicked.connect(self.on_ok)

        self.content_layout.addWidget(about_label)
        self.content_layout.addWidget(image_label)
        self.content_layout.addLayout(self.button_row)
        self.content_layout.addWidget(ok_button)

    def on_github(self) -> None:
        github_link = Constants.GITHUB_LINK

        if random.random() < 0.95:
            webbrowser.open(github_link)

            return

        fox_image = Utils.get_fox_image()
        webbrowser.open(fox_image if fox_image else github_link)

    def on_feedback(self) -> None:
        FeedbackWindow().exec()

    def on_check_updates(self) -> None:
        button = self.button_row.get_button_by_number(2)

        if button:
            button.setEnabled(False)
            button.setText("Checking...")

        self.update_checker = Utils.UpdateChecker()
        self.update_checker.update_info_received.connect(self.on_update_info_received)
        self.update_checker.error_occurred.connect(self.on_update_check_failed)
        self.update_checker.fetch_latest_release()

    def on_update_info_received(
            self,
            release_information: dict
        ) -> None:

        button = self.button_row.get_button_by_number(2)

        if button:
            button.setEnabled(True)
            button.setText("Check updates")

        remote_tag = str(release_information.get("tag_name", ""))

        with open(Utils.get_resource_path("version"), "r", encoding = "utf-8") as version_file:
            local_version = version_file.read().strip()

        if Utils.is_newer_version(remote_tag, local_version):
            window = UpdateWindow(
                version             = remote_tag,
                changelog           = str(release_information.get("body", "")),
                url                 = str(release_information.get("html_url", Constants.GITHUB_LINK)),
                release_information = release_information,
                parent              = self.parent()
            )
            window.exec()

            return

        button.setText("Latest version")

    def on_update_check_failed(
            self,
            request_type: str
        ) -> None:

        button = self.button_row.get_button_by_number(2)

        if button:
            button.setEnabled(True)
            button.setText("Check updates")
            button.start_glitch()

        ErrorWindow(
            "Check Failed",
            "Unable to fetch the latest release from GitHub. Please check your network connection.",
            "I hate my Wi - Fi"
        ).exec()