from __future__ import annotations

import os
import re
import sys
import json
import time
import numpy
import psutil
import random
import datetime
import platform
import subprocess

from urllib.request import urlopen

from PyQt6.QtCore import (
    QUrl,
    QObject,
    QSettings,
    pyqtSignal
)

from PyQt6.QtGui import (
    QFont,
    QPainterPath
)

from PyQt6.QtNetwork import (
    QNetworkRequest,
    QNetworkAccessManager
)

from loguru import logger

# General Helpers

def get_fox_image() -> str | None:
    endpoint_url = "https://randomfox.ca/floof/"

    try:
        with urlopen(endpoint_url, timeout = 2) as response:
            payload = json.loads(response.read())

            return payload.get("image")

    except Exception:
        return None

def gaussian_filter1d_np(
        data:  numpy.ndarray,
        sigma: float
    ) -> numpy.ndarray:

    radius = int(3 * sigma)
    grid   = numpy.arange(-radius, radius + 1)
    kernel = numpy.exp(-(grid ** 2) / (2 * (sigma ** 2)))

    kernel /= kernel.sum()

    return numpy.convolve(data, kernel, mode = "same")

def medfilt_np(
        data:        numpy.ndarray,
        kernel_size: int
    ) -> numpy.ndarray:

    if kernel_size % 2 == 0:
        raise ValueError("kernel_size must be odd")

    pad_width = kernel_size // 2
    padded    = numpy.pad(data, pad_width, mode = "edge")
    shape     = (data.size, kernel_size)
    strides   = (padded.strides[0], padded.strides[0])
    windows   = numpy.lib.stride_tricks.as_strided(padded, shape = shape, strides = strides)

    return numpy.median(windows, axis = 1)

def get_processes() -> list[str]:
    try:
        return [process.name() for process in psutil.process_iter(attrs = ["name"])]

    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []

def is_text_in_list(
        text:  str,
        items: list[str] | None
    ) -> bool:

    if not items:
        return False

    return any(text in item for item in items)

def get_process_string() -> str:
    processes = get_processes()

    if is_text_in_list("obs", processes):
        return random.choice(
            [
                "Why do you record me?",
                "Are we making content today?",
                "Don't forget to cut this part out in editing.",
                "Hope I don't drop the stream bitrate today.",
                "I don't like cameras.",
                "On air?"
            ]
        )

    if is_text_in_list("telegram", processes) or is_text_in_list("discord", processes):
        return random.choice(
            [
                "Who is texting you over there?",
                "Don't get distracted by chats."
            ]
        )

    return ""

def get_time_string() -> str:
    calendar_time = time.localtime()
    hours         = calendar_time.tm_hour

    if 19 <= hours <= 21:
        return random.choice(
            [
                "Good evening.",
                "Evening vibes.",
                "Time to unwind."
            ]
        )

    elif hours >= 22 or hours <= 5:
        return random.choice(
            [
                "Sleep tight.",
                "Sweet dreams.",
                "Nighty night."
            ]
        )

    elif 6 <= hours <= 11:
        return random.choice(
            [
                "Good morning.",
                "Rise and shine.",
                "You should get a coffee."
            ]
        )

    elif 12 <= hours <= 18:
        return random.choice(
            [
                "Good afternoon.",
                "A great day.",
                "Music time."
            ]
        )

    return "Hello."

def get_time_of_day() -> str:
    hour = datetime.datetime.now().hour

    if 5 <= hour < 12:
        return "morning"

    elif 12 <= hour < 17:
        return "afternoon"

    elif 17 <= hour < 22:
        return "evening"

    return "night"

def get_ee_string() -> str:
    return random.choice(
        [
            "Turn it up to eleven.",
            "Video killed the radio star.",
            "May the Music be with you.",
            "Cat."
        ]
    )

def get_weekday_string() -> str:
    weekday     = datetime.datetime.now().weekday()
    time_of_day = get_time_of_day()

    if weekday == 4:
        return random.choice(
            [
                "Friday. Finally.",
                f"Ahh, friday {time_of_day}.",
                f"Friday. Weekend. Quiet {time_of_day}."
            ]
        )

    elif weekday in [5, 6]:
        return random.choice(
            [
                "Compose on a weekend.",
                "Spending your weekends with Cassette?",
                "Weekend inspiration, I guess."
            ]
        )

    return ""

def get_some_title() -> str:
    threshold = random.random()

    if threshold < 0.01:
        return get_ee_string()

    elif threshold < 0.3:
        process_text = get_process_string()

        if process_text:
            return process_text

    elif threshold < 0.6:
        weekday_text = get_weekday_string()

        if weekday_text:
            return weekday_text

    return get_time_string()

def NDot(size: int) -> QFont:
    font = QFont("Ndot 57")

    pixel_size = round(size * 120 / 72)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    font.setPixelSize(pixel_size)

    return font

def NType(size: int) -> QFont:
    font = QFont("NType 82")

    pixel_size = round(size * 120 / 72)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    font.setPixelSize(pixel_size)

    return font

def open_file(path: str) -> None:
    if platform.system() == "Windows":
        os.startfile(path)

    elif platform.system() == "Darwin":
        subprocess.run(["open", path])

    else:
        subprocess.run(["xdg-open", path])

def get_user_path(
        relative_path: str,
        folder:        str
    ) -> str:

    normalized_parts = os.path.normpath(relative_path).split(os.sep)
    full_path        = os.path.join(os.path.expanduser("~"), folder, *normalized_parts)

    os.makedirs(os.path.dirname(full_path), exist_ok = True)

    return full_path

# Logging

class StreamToLogger:
    def __init__(self, level: str = "ERROR") -> None:
        self.level = level

    def write(self, buffer: str) -> None:
        for line in buffer.rstrip().splitlines():
            if not line.strip():
                continue

            logger.opt(depth = 1).log(self.level, line)

    def flush(self) -> None:
        pass

def setup_exe_logging(
        folder_name: str = "Logs",
        file_name:   str = "app.log"
    ) -> str:

    if getattr(sys, "frozen", False):
        base_directory = os.path.dirname(sys.executable)

    else:
        base_directory = os.path.dirname(os.path.abspath(__file__))

    log_directory = os.path.join(base_directory, folder_name)

    try:
        os.makedirs(log_directory, exist_ok = True)

    except PermissionError:
        user_home     = os.path.expanduser("~")
        log_directory = os.path.join(user_home, f".{folder_name.lower()}_fallback")
        os.makedirs(log_directory, exist_ok = True)

    log_file_path = os.path.join(log_directory, file_name)

    logger.remove()

    if sys.__stderr__ is not None:
        logger.add(sys.__stderr__, level = "DEBUG")

    logger.add(
        log_file_path,
        encoding  = "utf-8",
        rotation  = "10 MB",
        enqueue   = False,
        catch     = True,
        backtrace = True,
        diagnose  = True
    )

    if sys.stderr is not None:
        sys.stderr = StreamToLogger("ERROR")

    if sys.stdout is not None:
        sys.stdout = StreamToLogger("INFO")

    return log_file_path

def run(*arguments: object, **keywords: object) -> subprocess.CompletedProcess:
    if os.name == "nt":
        keywords.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)

    return subprocess.run(*arguments, **keywords)

# Value Conversion

def auto_cast(value: object) -> object:
    if value is None:
        return None

    if isinstance(value, (bool, int, float)):
        return value

    text_value = str(value).strip()
    low_value  = text_value.lower()

    if low_value in {"true", "yes"}:
        return True

    if low_value in {"false", "no"}:
        return False

    try:
        return int(text_value)

    except ValueError:
        pass

    try:
        return float(text_value)

    except ValueError:
        pass

    return text_value

# Settings Management

class SettingsController(QObject):
    setting_changed   = pyqtSignal(str, object)
    settings_reloaded = pyqtSignal()

    def __init__(
            self,
            organization: str,
            application:  str,
            parent:       QObject | None = None
        ) -> None:

        super().__init__(parent)

        self.data:     dict[str, object] = {}
        self.instance: QSettings         = QSettings(organization, application)

        self.load()

    def load(self) -> None:
        self.data.clear()

        for key in self.instance.allKeys():
            self.data[key] = auto_cast(self.instance.value(key))

        self.settings_reloaded.emit()

    def set_value(
            self,
            key:   str,
            value: object
        ) -> None:

        if self.data.get(key) == value:
            return

        self.data[key] = value
        self.instance.setValue(key, value)

        self.setting_changed.emit(key, value)
        self.instance.sync()

    def get(
            self,
            key:     str,
            default: object = None
        ) -> object:

        value = self.data.get(key)

        if value is None:
            return default

        return value

    def __getitem__(self, key: str) -> object:
        value = self.data.get(key)

        if value is None:
            return None

        return value

    def __setitem__(
            self,
            key:   str,
            value: object
        ) -> None:

        self.set_value(key, value)

    def __contains__(self, key: object) -> bool:
        return key in self.data

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self) -> object:
        return iter(self.data)

# SVG Path Parser

def parse_svg_path_data(path_string: str) -> QPainterPath:
    path   = QPainterPath()
    tokens = re.findall(r"([a-zA-Z]|-?[\d\.]+)", path_string)

    current_x = 0.0
    current_y = 0.0
    index     = 0

    while index < len(tokens):
        command = tokens[index]

        if command[0].isalpha():
            index += 1

        if command == "M":
            current_x = float(tokens[index])
            current_y = float(tokens[index + 1])
            path.moveTo(current_x, current_y)
            index += 2

        elif command == "L":
            current_x = float(tokens[index])
            current_y = float(tokens[index + 1])
            path.lineTo(current_x, current_y)
            index += 2

        elif command == "H":
            current_x = float(tokens[index])
            path.lineTo(current_x, current_y)
            index += 1

        elif command == "V":
            current_y = float(tokens[index])
            path.lineTo(current_x, current_y)
            index += 1

        elif command == "C":
            control_one_x = float(tokens[index])
            control_one_y = float(tokens[index + 1])
            control_two_x = float(tokens[index + 2])
            control_two_y = float(tokens[index + 3])
            current_x     = float(tokens[index + 4])
            current_y     = float(tokens[index + 5])
            path.cubicTo(control_one_x, control_one_y, control_two_x, control_two_y, current_x, current_y)
            index += 6

        elif command in {"Z", "z"}:
            path.closeSubpath()

    return path

# Resource Resolution

def get_resource_path(relative_path: str) -> str:
    if getattr(sys, "frozen", False):
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))

    else:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def get_ffmpeg_path(name: str = "ffmpeg") -> str:
    platform_name = sys.platform
    architecture  = platform.machine().lower()
    is_arm        = "arm" in architecture or "aarch64" in architecture

    if platform_name == "win32":
        suffix    = "arm64" if is_arm else "x64"
        file_name = f"{name}-windows-{suffix}.exe"

    elif platform_name == "darwin":
        suffix    = "silicon" if is_arm else "intel"
        file_name = f"{name}-macos-{suffix}"

    elif platform_name == "linux":
        suffix    = "arm64" if is_arm else "x64"
        file_name = f"{name}-linux-{suffix}"

    else:
        file_name = name

    full_path = get_resource_path(f"System/FFmpeg/{file_name}")

    if os.path.exists(full_path):
        logger.success(f"Found {name}: {full_path}")

    else:
        logger.error(f"{name} not found at {full_path}")

    return full_path

def run_hidden(command: list[str]) -> subprocess.CompletedProcess:
    keywords = {
        "capture_output": True,
        "text":           True,
        "shell":          False,
    }

    if platform.system() == "Windows":
        keywords["creationflags"] = subprocess.CREATE_NO_WINDOW
        startup_info              = subprocess.STARTUPINFO()
        startup_info.dwFlags     |= subprocess.STARTF_USESHOWWINDOW
        startup_info.wShowWindow  = subprocess.SW_HIDE
        keywords["startupinfo"]   = startup_info

    return subprocess.run(command, **keywords)

# Updates

class UpdateChecker(QObject):
    resource_loaded = pyqtSignal(str, object)
    error_occurred  = pyqtSignal(str)

    DEFAULT_RESOURCES: dict[str, tuple[str, bool]] = {
        "release": ("https://api.github.com/repos/chips047/Cassette/releases", True),
        "songs":   ("https://raw.githubusercontent.com/chips047/Cassette/main/System/Assets/Songs.txt", False),
        "about":   ("https://raw.githubusercontent.com/chips047/Cassette/main/System/Assets/About.txt", False)
    }

    def __init__(self) -> None:
        super().__init__()

        self.manager = QNetworkAccessManager(self)
        self.manager.finished.connect(self.on_request_finished)

    def fetch(
            self,
            resource_identifier: str,
            url:                 str  | None = None,
            is_json:             bool | None = None
        ) -> None:

        if url is None:
            configuration = self.DEFAULT_RESOURCES.get(resource_identifier)

            if not configuration:
                logger.error(f"Unknown resource identifier: {resource_identifier}")
                return

            target_url, json_mode = configuration

        else:
            target_url = url
            json_mode  = bool(is_json)

        request = QNetworkRequest(QUrl(target_url))
        request.setAttribute(QNetworkRequest.Attribute.User, resource_identifier)
        request.setAttribute(QNetworkRequest.Attribute.UserMax, json_mode)
        request.setRawHeader(b"User-Agent", b"Cassette-Updater-Script")

        self.manager.get(request)

    def fetch_all(self, resource_identifiers: list[str] | None = None) -> None:
        targets = resource_identifiers if resource_identifiers is not None else list(self.DEFAULT_RESOURCES.keys())

        for resource_identifier in targets:
            self.fetch(resource_identifier)

    def fetch_latest_release(self) -> None:
        self.fetch("release")

    def fetch_latest_songs_strings(self) -> None:
        self.fetch("songs")

    def fetch_latest_about_strings(self) -> None:
        self.fetch("about")

    def on_request_finished(self, reply: object) -> None:
        reply.deleteLater()

        resource_identifier = reply.request().attribute(QNetworkRequest.Attribute.User)
        is_json             = reply.request().attribute(QNetworkRequest.Attribute.UserMax)

        if reply.error() != reply.NetworkError.NoError:
            logger.error(f"Network error [{resource_identifier}]: {reply.errorString()}")
            self.error_occurred.emit(str(resource_identifier))

            return

        try:
            raw_bytes = bytes(reply.readAll())

            if not raw_bytes:
                logger.error(f"Empty data received for {resource_identifier}")
                self.error_occurred.emit(str(resource_identifier))

                return

            if is_json:
                parsed_json = json.loads(raw_bytes)
                payload     = parsed_json[0] if isinstance(parsed_json, list) and parsed_json else parsed_json

            else:
                payload = raw_bytes.decode("utf-8")

            self.resource_loaded.emit(str(resource_identifier), payload)

        except Exception:
            logger.exception(f"Failed to parse data for {resource_identifier}")
            self.error_occurred.emit(str(resource_identifier))

def check_dynamic_library(module: object) -> None:
    file_name          = getattr(module, "__file__", "")
    is_dynamic_library = file_name.endswith(".so") or file_name.endswith(".pyd")

    if is_dynamic_library:
        logger.success(f"{module.__name__} module uses dynamic library")

    else:
        logger.error(f"{module.__name__} module doesn't use dynamic library and will be slow")

def is_newer_version(
        remote_version: str,
        local_version:  str
    ) -> bool:

    clean_remote = remote_version.strip().lstrip("vV")
    clean_local  = local_version.strip().lstrip("vV")

    remote_numbers = [int(token) for token in re.findall(r"\d+", clean_remote)]
    local_numbers  = [int(token) for token in re.findall(r"\d+", clean_local)]

    if remote_numbers and local_numbers:
        return remote_numbers > local_numbers

    return clean_remote != clean_local