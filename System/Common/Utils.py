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

from PyQt6.QtGui import (
    QFont,
    QPainterPath,
)

from PyQt6.QtNetwork import (
    QNetworkRequest,
    QNetworkAccessManager,
)

from PyQt6.QtCore import (
    QUrl,
    QObject,
    QSettings,
    pyqtSignal
)

from loguru import logger

def get_fox_image() -> str | None:
    url = "https://randomfox.ca/floof/"

    try:
        with urlopen(url, timeout = 2) as r:
            info = json.loads(r.read())
            return info.get("image")
    
    except:
        return None

def gaussian_filter1d_np(data: numpy.ndarray, sigma: float) -> numpy.ndarray:
    radius  = int(3 * sigma)
    x       = numpy.arange(-radius, radius + 1)
    kernel  = numpy.exp(-(x**2) / (2 * sigma**2))
    kernel /= kernel.sum()
    
    return numpy.convolve(data, kernel, mode='same')

def medfilt_np(data: numpy.ndarray, kernel_size: int) -> numpy.ndarray:
    if kernel_size % 2 == 0:
        raise ValueError("kernel_size must be odd")
    
    pad_width = kernel_size // 2

    padded  = numpy.pad(data, pad_width, mode = 'edge')
    shape   = (data.size, kernel_size)
    strides = (padded.strides[0], padded.strides[0])
    windows = numpy.lib.stride_tricks.as_strided(padded, shape=shape, strides=strides)
    
    return numpy.median(windows, axis = 1)

def get_processes() -> list[str]:
    try:
        return [proc.name() for proc in psutil.process_iter(attrs=['name'])]
    
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []

def is_text_in_list(text: str, items: list | None) -> bool:
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

def get_time_string() -> str:
    t = time.localtime()
    hours = t.tm_hour
    
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
    
    else:
        return "what the fuck"

def get_time_of_day() -> str:
    hour = datetime.datetime.now().hour
    
    if 5 <= hour < 12:
        return "morning"
    
    elif 12 <= hour < 17:
        return "afternoon"
    
    elif 17 <= hour < 22:
        return "evening"
    
    else:
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

def get_some_title() -> str:
    number = random.random()

    if number < 0.01:
        return get_ee_string()

    elif number < 0.3:
        string = get_process_string()
        if string:
            return string
    
    elif number < 0.6:
        string = get_weekday_string()
        if string:
            return string
    
    return get_time_string()

def NDot(size: int) -> QFont:
    Ndot = QFont("Ndot 57")
    
    px_size = round(size * 120 / 72)
    Ndot.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    Ndot.setPixelSize(px_size)
    
    return Ndot

def NType(size: int) -> QFont:
    Ntype = QFont("NType 82")
    
    px_size = round(size * 120 / 72)
    Ntype.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    Ntype.setPixelSize(px_size)
    
    return Ntype

def open_file(path: str) -> None:
    if platform.system() == "Windows":
        os.startfile(path)
    
    elif platform.system() == "Darwin":
        subprocess.run(["open", path])
    
    else:
        subprocess.run(["xdg-open", path])

def get_user_path(relative_path: str, folder: str) -> str:
    normalized_parts = os.path.normpath(relative_path).split(os.sep)
    full_path = os.path.join(os.path.expanduser("~"), folder, *normalized_parts)

    os.makedirs(os.path.dirname(full_path), exist_ok = True)

    return full_path

class StreamToLogger:
    def __init__(self, level: str = "ERROR") -> None:
        self.level = level

    def write(self, buffer: str) -> None:
        for line in buffer.rstrip().splitlines():
            if line.strip():
                logger.opt(depth = 1).log(self.level, line)

    def flush(self) -> None:
        pass

def setup_exe_logging(folder_name: str = "Logs", file_name: str = "app.log") -> str:
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)

    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    log_dir = os.path.join(base_dir, folder_name)

    try:
        os.makedirs(log_dir, exist_ok = True)

    except PermissionError:
        user_home = os.path.expanduser("~")
        log_dir = os.path.join(user_home, f".{folder_name.lower()}_fallback")
        os.makedirs(log_dir, exist_ok = True)

    log_file_path = os.path.join(log_dir, file_name)

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

def run(*args, **kwargs) -> subprocess.CompletedProcess:
    if os.name == "nt":
        kwargs.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
    
    return subprocess.run(*args, **kwargs)

def auto_cast(value: object) -> object:
    if value is None:
        return None

    if isinstance(value, (bool, int, float)):
        return value

    text_value = str(value).strip()
    low_value  = text_value.lower()

    if low_value in {"true", "yes", "1"}:
        return True
    
    if low_value in {"false", "no", "0"}:
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

        self._data: dict[str, object] = {}
        self.instance = QSettings(organization, application)
        self.load()

    def load(self) -> None:
        self._data.clear()

        for key in self.instance.allKeys():
            self._data[key] = auto_cast(self.instance.value(key))

        self.settings_reloaded.emit()

    def set_value(
        self,
        key:   str,
        value: object
    ) -> None:
        
        if self._data.get(key) == value:
            return

        self._data[key] = value
        self.instance.setValue(key, value)
        
        self.setting_changed.emit(key, value)

        self.instance.sync()

    def get(self, key: str, default: object = None) -> object:
        return self._data.get(key, default)

    def __getitem__(self, key: str) -> object:
        return self._data[key]

    def __setitem__(self, key: str, value: object) -> None:
        self.set_value(key, value)

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

def parse_svg_path_data(d_string: str) -> QPainterPath:
    path = QPainterPath()
    tokens = re.findall(r'([a-zA-Z]|-?[\d\.]+)', d_string)
    
    current_x = 0.0
    current_y = 0.0
    
    i = 0

    while i < len(tokens):
        cmd = tokens[i]
        
        if not cmd[0].isalpha():
            pass
        
        else:
            i += 1
        
        if cmd == 'M':
            x = float(tokens[i]); y = float(tokens[i+1])
            path.moveTo(x, y)
            current_x, current_y = x, y
            i += 2
        
        elif cmd == 'L':
            x = float(tokens[i]); y = float(tokens[i+1])
            path.lineTo(x, y)
            current_x, current_y = x, y
            i += 2
        
        elif cmd == 'H':
            x = float(tokens[i])
            path.lineTo(x, current_y)
            current_x = x
            i += 1
        
        elif cmd == 'V':
            y = float(tokens[i])
            path.lineTo(current_x, y)
            current_y = y
            i += 1
        
        elif cmd == 'C':
            c1x = float(tokens[i]);   c1y = float(tokens[i+1])
            c2x = float(tokens[i+2]); c2y = float(tokens[i+3])
            ex = float(tokens[i+4]);  ey = float(tokens[i+5])
            path.cubicTo(c1x, c1y, c2x, c2y, ex, ey)
            current_x, current_y = ex, ey
            i += 6
        
        elif cmd == 'Z' or cmd == 'z':
            path.closeSubpath()
        
        else:
            pass
    
    return path

def get_resource_path(relative_path: str) -> str:
    if getattr(sys, 'frozen', False):
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    
    else:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def get_ffmpeg_path(name: str = "ffmpeg") -> str:
    logger.debug(f"Searching for {name}...")

    plat    = sys.platform
    arch    = platform.machine().lower()
    is_arm  = "arm" in arch or "aarch64" in arch

    logger.debug(f"Platform: {plat}")
    logger.debug(arch)
    logger.debug(f"Is ARM: {is_arm}")

    if plat == "win32":
        suffix    = "arm64" if is_arm else "x64"
        file_name = f"{name}-windows-{suffix}.exe"

    elif plat == "darwin":
        suffix    = "silicon" if is_arm else "intel"
        file_name = f"{name}-macos-{suffix}"

    elif plat == "linux":
        suffix    = "arm64" if is_arm else "x64"
        file_name = f"{name}-linux-{suffix}"

    full_path = get_resource_path(f"System/FFmpeg/{file_name}")

    if os.path.exists(full_path):
        logger.success(f"Found {name}: {full_path}")
    
    else:
        logger.error(f"{name} not found at {full_path}")

    return full_path

def run_hidden(cmd: list[str]) -> subprocess.CompletedProcess:
    kwargs = {
        "capture_output": True,
        "text": True,
        "shell": False,
    }

    if platform.system() == "Windows":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        kwargs["startupinfo"] = si

    return subprocess.run(cmd, **kwargs)

class UpdateChecker(QObject):
    resource_loaded      = pyqtSignal(str, object)
    error_occurred       = pyqtSignal(str)

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
            resource_id: str,
            url:         str | None = None,
            is_json:     bool | None = None
        ) -> None:

        if url is None:
            configuration = self.DEFAULT_RESOURCES.get(resource_id)

            if not configuration:
                logger.error(f"Unknown resource identifier: {resource_id}")
                return

            target_url, json_mode = configuration

        else:
            target_url = url
            json_mode  = bool(is_json)

        request = QNetworkRequest(QUrl(target_url))
        request.setAttribute(QNetworkRequest.Attribute.User, resource_id)
        request.setAttribute(QNetworkRequest.Attribute.UserMax, json_mode)
        request.setRawHeader(b"User-Agent", b"Cassette-Updater-Script")

        self.manager.get(request)

    def fetch_all(self, resource_ids: list[str] | None = None) -> None:
        targets = resource_ids if resource_ids is not None else list(self.DEFAULT_RESOURCES.keys())

        for resource_id in targets:
            self.fetch(resource_id)

    def fetch_latest_release(self) -> None:
        self.fetch("release")

    def fetch_latest_songs_strings(self) -> None:
        self.fetch("songs")

    def fetch_latest_about_strings(self) -> None:
        self.fetch("about")

    def on_request_finished(self, reply) -> None:
        reply.deleteLater()

        resource_id = reply.request().attribute(QNetworkRequest.Attribute.User)
        is_json     = reply.request().attribute(QNetworkRequest.Attribute.UserMax)

        if reply.error() != reply.NetworkError.NoError:
            logger.error(f"Network error [{resource_id}]: {reply.errorString()}")
            self.error_occurred.emit(str(resource_id))

            return

        try:
            raw_bytes = bytes(reply.readAll())

            if not raw_bytes:
                logger.error(f"Empty data received for {resource_id}")
                self.error_occurred.emit(str(resource_id))

                return

            if is_json:
                parsed_json = json.loads(raw_bytes)
                data        = parsed_json[0] if isinstance(parsed_json, list) and parsed_json else parsed_json

            else:
                data = raw_bytes.decode("utf-8")

            self.resource_loaded.emit(str(resource_id), data)

        except Exception:
            logger.exception(f"Failed to parse data for {resource_id}")
            self.error_occurred.emit(str(resource_id))

def check_dynamic_library(module: object) -> None:
    file = module.__file__
    is_dynamic_library = file.endswith(".so") or file.endswith(".pyd")

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