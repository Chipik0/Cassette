from __future__ import annotations

import os
import re
import sys
import shutil
import zipfile
import tempfile
import platform
import subprocess
import webbrowser

from loguru import logger

from PyQt6.QtGui import QTextDocument

from PyQt6.QtCore import (
    QUrl,
    QTimer,
    pyqtSignal
)

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QApplication
)

from PyQt6.QtNetwork import (
    QNetworkReply,
    QNetworkRequest,
    QNetworkAccessManager
)

from System.Common import (
    Styles,
    Constants
)

from System.Services import Player
from System.Interface import Widgets

from System.Interface.Windows import (
    ErrorWindow,
    FloatingWindowGPU
)

# Update Window

class UpdateWindow(FloatingWindowGPU):
    download_progress_updated = pyqtSignal(float, float)

    def __init__(
            self,
            version:             str,
            changelog:           str,
            url:                 str                       = Constants.GITHUB_LINK,
            release_information: dict[str, object] | None  = None,
            parent:              QWidget           | None  = None
        ) -> None:

        super().__init__(
            f"Cassette {version}",
            parent                     = parent,
            enable_audioplayer_effects = False
        )

        self.version_text        = version
        self.changelog_text      = changelog
        self.release_url         = url
        self.release_information = release_information

        self.download_target_url = ""
        self.download_file_path  = ""
        self.temporary_file      = None
        self.download_reply      = None

        self.total_bytes         = 0
        self.received_bytes      = 0
        self.is_downloading      = False
        self.is_ready_to_install = False

        self.network_manager     = QNetworkAccessManager(self)

        self.setup_user_interface()
        self.resolve_target_asset()

    # Setup Layout

    def setup_user_interface(self) -> None:
        formatted_changelog = self.format_changelog_text(self.changelog_text)

        self.update_label = Widgets.DescriptionLabel(f"`A new version is available.`\n{formatted_changelog}", 700)

        self.scroll_area = Widgets.ElasticScrollArea(self, Styles.Colors.Floating.Background)
        self.scroll_area.setFixedWidth(700)
        self.scroll_area.add_widget(self.update_label)

        optimal_scroll_height = self.calculate_optimal_scroll_height(700, 290)
        self.scroll_area.setFixedHeight(optimal_scroll_height)

        self.status_label = Widgets.DescriptionLabel("", 700)
        self.status_label.setVisible(False)

        self.pulse_status_widget = Widgets.PulseStatusWidget(self)
        self.pulse_status_widget.setFixedHeight(60)
        self.pulse_status_widget.setVisible(False)

        self.github_button = Widgets.ButtonWithOutline("View on GitHub")
        self.cancel_button = Widgets.ButtonWithOutline("Later")
        self.action_button = Widgets.NothingButton("Update now")

        self.github_button.clicked.connect(self.open_github_release)
        self.cancel_button.clicked.connect(self.handle_cancel_clicked)
        self.action_button.clicked.connect(self.handle_action_clicked)

        self.download_progress_updated.connect(self.update_progress_display)

        button_row_layout = QHBoxLayout()
        button_row_layout.addWidget(self.github_button)
        button_row_layout.addWidget(self.cancel_button)
        button_row_layout.addWidget(self.action_button)

        self.content_layout.addWidget(self.scroll_area)
        self.content_layout.addWidget(self.status_label)
        self.content_layout.addWidget(self.pulse_status_widget)
        self.content_layout.addLayout(button_row_layout)

    def calculate_optimal_scroll_height(
            self,
            content_width:  int = 700,
            maximum_height: int = 290
        ) -> int:

        document = QTextDocument()
        document.setDocumentMargin(0)
        document.setDefaultFont(self.update_label.font())
        document.setTextWidth(float(content_width))
        document.setHtml(self.update_label.text())

        measured_height = int(document.size().height()) + 20

        return min(maximum_height, max(60, measured_height))

    # Version and Asset Resolution

    def resolve_target_asset(self) -> None:
        if not self.release_information:
            return

        assets_list = self.release_information.get("assets", [])

        if not isinstance(assets_list, list):
            return

        compatible_asset = self.find_compatible_asset(assets_list)

        if not compatible_asset:
            logger.warning("No compatible asset found for current platform and architecture.")
            self.action_button.setEnabled(False)

            return

        self.download_target_url = str(compatible_asset.get("browser_download_url", ""))
        download_size_bytes      = int(compatible_asset.get("size", 0))

        if download_size_bytes > 0:
            size_in_megabytes = download_size_bytes / (1024.0 * 1024.0)
            self.action_button.setText(f"Update now ({size_in_megabytes:.1f} MB)")

    @staticmethod
    def get_platform_asset_filename() -> str:
        platform_name = sys.platform
        machine_name  = platform.machine().lower()
        is_arm        = "arm" in machine_name or "aarch64" in machine_name

        if platform_name == "win32":
            architecture = "arm64" if is_arm else "x64"

            return f"cassette-windows-{architecture}.zip"

        if platform_name == "darwin":
            architecture = "silicon" if is_arm else "intel"

            return f"cassette-macos-{architecture}.zip"

        architecture = "arm64" if is_arm else "x64"

        return f"cassette-linux-{architecture}.zip"

    def find_compatible_asset(
            self,
            assets: list[dict[str, object]]
        ) -> dict[str, object] | None:

        target_name = self.get_platform_asset_filename()

        for asset in assets:
            asset_filename = str(asset.get("name", "")).lower()

            if asset_filename == target_name:
                return asset

        return None

    # Safety and Verification

    def has_sufficient_disk_space(self) -> bool:
        temporary_directory   = tempfile.gettempdir()
        executable_path       = sys.executable
        application_directory = os.path.dirname(executable_path)

        try:
            temporary_space_bytes   = shutil.disk_usage(temporary_directory).free
            application_space_bytes = shutil.disk_usage(application_directory).free

            one_gigabyte = 1024 * 1024 * 1024

            if temporary_space_bytes < one_gigabyte:
                return False

            if application_space_bytes < one_gigabyte:
                return False

            return True

        except OSError:
            return False

    def is_safe_application_path(
            self,
            target_path: str
        ) -> bool:

        if not target_path:
            return False

        normalized_path = os.path.abspath(target_path)

        if not os.path.isabs(normalized_path):
            return False

        dangerous_directories = {
            "/",
            "/bin",
            "/sbin",
            "/usr",
            "/usr/bin",
            "/usr/local",
            "/etc",
            "/var",
            "/tmp",
            "/home",
            "/root",
            "/Applications"
        }

        if sys.platform == "win32":
            dangerous_directories.update(
                {
                    "c:\\",
                    "c:\\windows",
                    "c:\\program files",
                    "c:\\program files (x86)"
                }
            )

        if normalized_path.lower() in {directory.lower() for directory in dangerous_directories}:
            return False

        user_home_directory = os.path.abspath(os.path.expanduser("~"))

        if normalized_path.lower() == user_home_directory.lower():
            return False

        return True

    def is_directory_writable(
            self,
            target_directory: str
        ) -> bool:

        if not os.path.exists(target_directory):
            return False

        return os.access(target_directory, os.W_OK)

    def verify_downloaded_package(self) -> bool:
        if not self.download_file_path:
            return False

        if not os.path.exists(self.download_file_path):
            return False

        if not zipfile.is_zipfile(self.download_file_path):
            return False

        try:
            with zipfile.ZipFile(self.download_file_path, "r") as archive:
                if archive.testzip() is not None:
                    return False

            return True

        except (zipfile.BadZipFile, OSError):
            return False

    def clean_up_temporary_file(self) -> None:
        if not self.download_file_path:
            return

        if not os.path.exists(self.download_file_path):
            return

        try:
            os.remove(self.download_file_path)

        except OSError:
            pass

    # Network Operations

    def start_download(self) -> None:
        if not self.download_target_url:
            self.open_github_release()

            return

        self.is_downloading = True

        self.action_button.setEnabled(False)
        self.cancel_button.setText("Cancel")

        self.status_label.setText("Connecting to server...")
        self.status_label.setVisible(True)

        self.pulse_status_widget.setVisible(True)
        self.pulse_status_widget.resume_heartbeat()
        self.pulse_status_widget.transition_to_white(duration_ms = 200)
        self.pulse_status_widget.unflatten(duration_ms = 400)
        self.pulse_status_widget.set_mode(Widgets.WaveMode.PULSE)
        self.pulse_status_widget.set_beats_per_minute(60.0, duration_ms = 0)

        self.adjustSize()

        target_file_name        = self.download_target_url.split("/")[-1]
        temporary_directory     = tempfile.gettempdir()
        self.download_file_path = os.path.join(temporary_directory, target_file_name)

        try:
            self.temporary_file = open(self.download_file_path, "wb")

        except OSError as exception:
            logger.error(f"Failed to create temporary update file: {exception}")
            self.handle_download_failure("Failed to create temporary file.")

            return

        request = QNetworkRequest(QUrl(self.download_target_url))
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy
        )
        request.setRawHeader(b"User-Agent", b"Cassette-Updater")

        self.download_reply = self.network_manager.get(request)
        self.download_reply.downloadProgress.connect(self.handle_download_progress)
        self.download_reply.readyRead.connect(self.handle_data_received)
        self.download_reply.finished.connect(self.handle_download_finished)

    def handle_data_received(self) -> None:
        if not self.download_reply or not self.temporary_file:
            return

        chunk_data = self.download_reply.readAll()

        if chunk_data.isEmpty():
            return

        self.temporary_file.write(chunk_data.data())

    def handle_download_progress(
            self,
            received_bytes: int,
            total_bytes:    int
        ) -> None:

        if total_bytes <= 0:
            return

        self.received_bytes = received_bytes
        self.total_bytes    = total_bytes

        self.download_progress_updated.emit(float(received_bytes), float(total_bytes))

    def update_progress_display(
            self,
            received_bytes: float,
            total_bytes:    float
        ) -> None:

        received_megabytes = received_bytes / (1024.0 * 1024.0)
        total_megabytes    = total_bytes / (1024.0 * 1024.0)
        progress_fraction  = min(1.0, max(0.0, received_bytes / total_bytes))
        progress_percent   = progress_fraction * 100.0

        self.status_label.setText(
            f"Downloading: {received_megabytes:.1f} MB / {total_megabytes:.1f} MB ({progress_percent:.0f}%)"
        )

        current_bpm = 60.0 + (progress_fraction * 90.0)
        self.pulse_status_widget.set_beats_per_minute(current_bpm, duration_ms = 180)

    def handle_download_finished(self) -> None:
        if not self.is_downloading:
            return

        if self.temporary_file:
            self.temporary_file.close()
            self.temporary_file = None

        if not self.download_reply:
            return

        network_error = self.download_reply.error()
        self.download_reply.deleteLater()
        self.download_reply = None

        if network_error == QNetworkReply.NetworkError.OperationCanceledError:
            self.clean_up_temporary_file()

            return

        if network_error != QNetworkReply.NetworkError.NoError:
            self.handle_download_failure("Connection lost during download.")

            return

        if not self.verify_downloaded_package():
            self.handle_download_failure("The downloaded package is corrupted.")

            return

        self.is_downloading      = False
        self.is_ready_to_install = True

        self.status_label.setText("Update package downloaded and verified. Click restart to apply.")
        self.action_button.setText("Restart now")
        self.action_button.setEnabled(True)
        self.cancel_button.setText("Later")

        self.pulse_status_widget.transition_to_sine(150)
        self.pulse_status_widget.set_loading_speed_ratio(0.5, 0)
        self.pulse_status_widget.set_amplitude(4.0, 0)

        QTimer.singleShot(150, lambda: self.pulse_status_widget.set_amplitude(0.0, 500))

        Player.ui_player.play_sound("Feedback/UpdateReady")

    def handle_download_failure(self, error_message: str) -> None:
        self.is_downloading = False

        self.clean_up_temporary_file()

        self.status_label.setText(f"Download failed: {error_message}")
        self.action_button.setText("Retry")
        self.action_button.setEnabled(True)
        self.cancel_button.setText("Close")

        self.pulse_status_widget.transition_to_red(duration_ms = 250)
        self.pulse_status_widget.flatten(duration_ms = 400)
        self.pulse_status_widget.simulate_cardiac_arrest()

        Player.ui_player.play_sound("Signals/Error/TransmitFailed")

    def handle_insufficient_disk_space(self) -> None:
        self.status_label.setText("Update blocked: Less than 1 GB of free disk space available.")
        self.status_label.setVisible(True)

        self.action_button.setEnabled(False)

        self.pulse_status_widget.setVisible(True)
        self.pulse_status_widget.transition_to_red(duration_ms = 250)
        self.pulse_status_widget.flatten(duration_ms = 400)
        self.pulse_status_widget.simulate_cardiac_arrest()

        Player.ui_player.play_sound("Signals/Error/TransmitFailed")

        ErrorWindow(
            "Insufficient Disk Space",
            "At least 1 GB of free disk space is required on both the temporary and installation drives to update.\nAutomatic update has been canceled.",
            "Go delete ya files"
        ).exec()

    def handle_permission_denied(self) -> None:
        self.status_label.setText("Update blocked: No write permission in the application directory.")
        self.status_label.setVisible(True)

        self.action_button.setEnabled(False)

        self.pulse_status_widget.setVisible(True)
        self.pulse_status_widget.transition_to_red(duration_ms = 250)
        self.pulse_status_widget.flatten(duration_ms = 400)
        self.pulse_status_widget.simulate_cardiac_arrest()

        Player.ui_player.play_sound("Signals/Error/TransmitFailed")

        ErrorWindow(
            "Write Permission Denied",
            "Cassette cannot write to its installation folder.\nPlease run as administrator or download and install the update manually.",
            "Ow"
        ).exec()

    def cancel_download(self) -> None:
        if self.download_reply:
            try:
                self.download_reply.finished.disconnect(self.handle_download_finished)
                self.download_reply.readyRead.disconnect(self.handle_data_received)
                self.download_reply.downloadProgress.disconnect(self.handle_download_progress)

            except (TypeError, RuntimeError):
                pass

            self.download_reply.abort()
            self.download_reply.deleteLater()
            self.download_reply = None

        if self.temporary_file:
            self.temporary_file.close()
            self.temporary_file = None

        self.clean_up_temporary_file()

        self.is_downloading = False

    # Installation and Restart

    def apply_update_and_restart(self) -> None:
        if not getattr(sys, "frozen", False):
            logger.warning("Running from Python source code. Binary replacement skipped.")
            self.on_ok()

            return

        if not self.verify_downloaded_package():
            self.handle_download_failure("The downloaded package is corrupted.")

            return

        executable_path       = sys.executable
        process_identifier    = os.getpid()
        temporary_folder      = tempfile.gettempdir()
        application_directory = os.path.dirname(executable_path)

        if not self.is_safe_application_path(application_directory):
            logger.critical("Unsafe application directory detected. Update aborted to prevent system damage.")
            self.handle_download_failure("Refused to update: Unsafe target directory.")

            return

        if sys.platform == "win32":
            script_path    = os.path.join(temporary_folder, "cassette_updater.bat")
            script_content = f"""@echo off
chcp 65001 > nul
:wait_process
tasklist /fi "PID eq {process_identifier}" | find ":" > nul
if errorlevel 1 (
    timeout /t 1 /nobreak > nul
    goto wait_process
)
if not exist "{application_directory}" goto cleanup
tar -xf "{self.download_file_path}" -C "{application_directory}" || powershell -Command "Expand-Archive -Force -Path '{self.download_file_path}' -DestinationPath '{application_directory}'"
start "" "{executable_path}"
:cleanup
del "{self.download_file_path}"
del "%~f0"
"""
            with open(script_path, "w", encoding = "utf-8") as script_file:
                script_file.write(script_content)

            subprocess.Popen(
                ["cmd.exe", "/c", script_path],
                creationflags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
            )

        elif sys.platform == "darwin":
            bundle_directory = os.path.abspath(os.path.join(application_directory, "../../.."))
            parent_directory = os.path.dirname(bundle_directory)

            if not bundle_directory.endswith(".app") or not self.is_safe_application_path(bundle_directory):
                logger.critical("Unsafe bundle directory on macOS. Aborting update.")
                self.handle_download_failure("Refused to update: Unsafe bundle directory.")

                return

            script_path    = os.path.join(temporary_folder, "cassette_updater.sh")
            script_content = f"""#!/bin/sh
while kill -0 {process_identifier} 2>/dev/null; do
    sleep 0.5
done
if [ -d "{bundle_directory}" ] && [ "{bundle_directory}" != "/" ] && [ "{bundle_directory}" != "/Applications" ]; then
    rm -rf "{bundle_directory}"
fi
unzip -o "{self.download_file_path}" -d "{parent_directory}"
xattr -cr "{bundle_directory}"
open "{bundle_directory}"
rm -f "{self.download_file_path}"
rm -f "$0"
"""
            with open(script_path, "w", encoding = "utf-8") as script_file:
                script_file.write(script_content)

            os.chmod(script_path, 0o755)
            subprocess.Popen(["/bin/sh", script_path], start_new_session = True)

        else:
            if not self.is_safe_application_path(application_directory):
                logger.critical("Unsafe Linux directory. Aborting update.")
                self.handle_download_failure("Refused to update: Unsafe target directory.")

                return

            script_path    = os.path.join(temporary_folder, "cassette_updater.sh")
            script_content = f"""#!/bin/sh
while kill -0 {process_identifier} 2>/dev/null; do
    sleep 0.5
done
if [ -d "{application_directory}" ] && [ "{application_directory}" != "/" ] && [ "{application_directory}" != "$HOME" ]; then
    unzip -o "{self.download_file_path}" -d "{application_directory}"
    chmod +x "{executable_path}"
    "{executable_path}" &
fi
rm -f "{self.download_file_path}"
rm -f "$0"
"""
            with open(script_path, "w", encoding = "utf-8") as script_file:
                script_file.write(script_content)

            os.chmod(script_path, 0o755)
            subprocess.Popen(["/bin/sh", script_path], start_new_session = True)

        application = QApplication.instance()

        if application:
            application.quit()

        sys.exit(0)

    # Event Handlers

    def handle_action_clicked(self) -> None:
        if self.is_ready_to_install:
            self.apply_update_and_restart()

            return

        if not self.has_sufficient_disk_space():
            self.handle_insufficient_disk_space()

            return

        executable_path       = sys.executable
        application_directory = os.path.dirname(executable_path)

        if getattr(sys, "frozen", False):
            if not self.is_safe_application_path(application_directory):
                self.handle_download_failure("Refused to update: Unsafe target directory.")

                return

            if not self.is_directory_writable(application_directory):
                self.handle_permission_denied()

                return

        self.start_download()

    def handle_cancel_clicked(self) -> None:
        if self.is_downloading:
            self.cancel_download()

        self.on_cancel()

    def open_github_release(self) -> None:
        webbrowser.open(self.release_url)

    def really_close(self) -> None:
        if self.is_downloading:
            self.cancel_download()

        super().really_close()

    # Text Formatting

    @staticmethod
    def format_changelog_text(changelog: str) -> str:
        changelog = re.sub(r"(?m)^### \*\*Cassette v\d+\.\d+\.\d+\*\*\s*\r?\n", "",      changelog)
        changelog = re.sub(r"(?m)^>\s*(.*?)\s*$",                               r"`\1`", changelog)
        changelog = re.sub(r"### \*\*(.*?)\*\*",                                r"`\1`", changelog)
        changelog = re.sub(r"\*\*(.*?)\*\*",                                    r"`\1`", changelog)
        changelog = re.sub(r"(?m)^-\s+",                                        "`•` ",  changelog)

        return changelog