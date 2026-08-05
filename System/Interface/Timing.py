from PyQt6.QtCore import (
    Qt,
    QTimer
)

from loguru  import logger

from System.Common import (
    Dev,
    Constants
)

# Timer

@Dev.track_ram
class Timer(QTimer):
    def __init__(
        self,
        interval:    int    = 1000,
        callback:    object = None,
        auto_start:  bool   = False,
        single_shot: bool   = False,
        fps_managed: bool   = False,
        parent:      QTimer = None
    ) -> None:

        super().__init__(parent)

        self.base_interval = interval
        self.fps_managed   = fps_managed

        self.setSingleShot(single_shot)

        if fps_managed:
            self.connect_to_settings()
            self.apply_fps_managed_interval()

        else:
            self.setInterval(self.base_interval)

        if self.interval() < 15:
            self.setTimerType(Qt.TimerType.PreciseTimer)

        if callback:
            self.timeout.connect(callback)

        if auto_start:
            self.start()
            logger.debug(f"Timer started: interval={self.interval()}ms fps_managed={fps_managed} single_shot={single_shot}")

    def connect_to_settings(self) -> None:
        Constants.current_settings.setting_changed.connect(self.on_setting_changed)
        Constants.current_settings.settings_reloaded.connect(self.apply_fps_managed_interval)

    def resolve_target_fps(self) -> int:
        target_fps = Constants.current_settings.get("target_fps", 60)
        return target_fps

    def apply_fps_managed_interval(self) -> None:
        target_fps = self.resolve_target_fps()
        interval   = int(round(1000 / target_fps))

        self.setInterval(interval)

        if self.interval() < 15:
            self.setTimerType(Qt.TimerType.PreciseTimer)

    def on_setting_changed(self, key: str, value: object) -> None:
        if key != "target_fps":
            return

        self.apply_fps_managed_interval()