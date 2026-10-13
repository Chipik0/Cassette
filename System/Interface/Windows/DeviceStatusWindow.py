from __future__ import annotations

import webbrowser

from PyQt6.QtCore    import QTimer
from PyQt6.QtWidgets import QWidget

from System.Services  import RealTimeVisualizer
from System.Interface import Widgets

from System.Interface.Windows.FloatingWindowGPU import FloatingWindowGPU

# Device Status Window

class DeviceStatusWindow(FloatingWindowGPU):
    RECEIVER_GITHUB_URL = "https://github.com/chips047/Cassette-Receiver/releases/latest"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title                      = "Device Connection",
            parent                     = parent,
            max_tilt_angle             = 10,
            enable_audioplayer_effects = False
        )

        self.syncer = RealTimeVisualizer.rt_visualizer

        self.setup_ui()
        self.connect_signals()
        self.refresh_state()

    # User Interface Setup

    def setup_ui(self) -> None:
        self.pulse_widget = Widgets.PulseStatusWidget(self)
        self.pulse_widget.setFixedHeight(50)
        self.pulse_widget.setMinimumWidth(550)
        self.pulse_widget.set_manual_mode(True)
        self.pulse_widget.set_amplitude(18.0)

        self.status_label = Widgets.DescriptionLabel("Checking connection...", 460)
        self.ping_label   = Widgets.DescriptionLabel("", 460)
        self.help_label   = Widgets.DescriptionLabel("", 460)

        self.help_label.setVisible(False)

        self.github_button = Widgets.ButtonWithOutline(
            text                 = "Get Receiver APK",
            enable_glitch_effect = False
        )

        self.github_button.clicked.connect(self.open_github_releases)
        self.github_button.setVisible(False)

        self.close_button = Widgets.NothingButton("Done")
        self.close_button.clicked.connect(self.on_ok)

        self.content_layout.addWidget(self.pulse_widget)
        self.content_layout.addWidget(self.status_label)
        self.content_layout.addWidget(self.ping_label)
        self.content_layout.addWidget(self.help_label)
        self.content_layout.addWidget(self.github_button)
        self.content_layout.addWidget(self.close_button)

    # Connections

    def connect_signals(self) -> None:
        self.syncer.ping_updated.connect(self.on_ping_received)
        self.syncer.status_changed.connect(self.on_status_changed)

    # Event Handlers

    def on_ping_received(self, latency_ms: float) -> None:
        is_connected = self.syncer.client_socket is not None

        if not is_connected:
            return

        self.pulse_widget.trigger_single_beat()

        color_hex = "#55FF55" if latency_ms <= 60.0 else "#FFAA00" if latency_ms <= 120.0 else "#FF4444"

        self.ping_label.setText(
            f'Response latency: <span style="color: {color_hex}; font-weight: bold;">{latency_ms:.1f} ms</span>'
        )

    def on_status_changed(
            self,
            status_text: str,
            mode_text:   str
        ) -> None:

        self.refresh_state()

    def refresh_state(self) -> None:
        is_connected    = self.syncer.client_socket is not None
        connection_mode = self.syncer.connection_mode or "unknown"
        active_address  = self.syncer.active_ip_address or ""

        if is_connected:
            mode_description = f"USB Cable" if connection_mode == "cable" else f"Wi-Fi ({active_address})"

            self.status_label.setText(
                f'Status: <span style="color: #55FF55; font-weight: bold;">Connected</span> via {mode_description}'
            )

            last_ping = self.syncer.last_ping_ms
            ping_text = f"{last_ping:.1f} ms" if last_ping > 0 else "measuring..."

            self.ping_label.setText(f"Response latency: `{ping_text}`")
            self.ping_label.setVisible(True)

            self.help_label.setVisible(False)
            self.github_button.setVisible(False)

            self.pulse_widget.transition_to_white(duration_ms = 150)
            self.syncer.send_heartbeat_ping()

        else:
            self.status_label.setText(
                'Status: <span style="color: #FF5555; font-weight: bold;">Disconnected</span>'
            )

            self.ping_label.setVisible(False)

            instruction_text = (
                "Nothing Phone is not linked.\n"
                "1. Install `Cassette Receiver` APK on your phone.\n"
                "2. Connect via USB cable or join the same Wi-Fi network."
            )

            self.help_label.setText(instruction_text)
            self.help_label.setVisible(True)
            self.github_button.setVisible(True)

            self.pulse_widget.transition_to_red(duration_ms = 200)

        QTimer.singleShot(0, self.adjustSize)

    def open_github_releases(self) -> None:
        webbrowser.open(self.RECEIVER_GITHUB_URL)

    def really_close(self) -> None:
        try:
            self.syncer.ping_updated.disconnect(self.on_ping_received)
            self.syncer.status_changed.disconnect(self.on_status_changed)

        except (TypeError, RuntimeError):
            pass

        super().really_close()