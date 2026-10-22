from __future__ import annotations

import time
import json
import aubio
import numpy
import tempfile
import soundfile

from loguru import logger

from pathlib import Path

from System.Common import (
    Utils,
    Constants
)

class NoAudioStreams(Exception):
    pass

class PermissionError(Exception):
    pass

class CorruptedFileError(Exception):
    pass

def probe_audio(path: str) -> dict:
    command = [
        Constants.FFPROBE_PATH,
        "-v", "error",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        path
    ]

    try:
        logger.debug(f"Probing audio file: {path}")
        result = Utils.run_hidden(command)

    except FileNotFoundError:
        logger.error("FFprobe was not found. Please ensure it is included with the application.")
        raise FileNotFoundError("FFprobe was not found.")

    if result.returncode != 0:
        logger.error(f"FFprobe error: {result.stderr}")
        raise CorruptedFileError(
            "The audio file is corrupted or in an unsupported format."
        )

    try:
        logger.debug("Parsing FFprobe output")

        return json.loads(result.stdout)

    except json.JSONDecodeError:
        logger.error("Failed to parse FFprobe output. The audio file may be corrupted or in an unsupported format.")
        raise CorruptedFileError(
            "The audio file is corrupted or in an unsupported format."
        )

def ensure_wav(path: str) -> str:
    path_object = Path(path)

    if not path_object.exists():
        raise FileNotFoundError("The specified audio file was not found.")

    try:
        probe_data = probe_audio(path)

    except FileNotFoundError:
        raise

    except Exception:
        raise CorruptedFileError(
            "The audio file is corrupted or in an unsupported format."
        )

    audio_streams = [
        stream for stream in probe_data.get("streams", [])
        if stream.get("codec_type") == "audio"
    ]

    if not audio_streams:
        raise NoAudioStreams()

    format_name = probe_data.get("format", {}).get("format_name", "").lower()

    if "wav" in format_name and path_object.suffix.lower() == ".wav":
        logger.warning("Audio is WAV. Not converting.")

        return str(path_object)

    logger.warning("Audio is not WAV. Starting conversion...")

    sample_rate = audio_streams[0].get("sample_rate", "44100")

    temporary_file = tempfile.NamedTemporaryFile(suffix = ".wav", delete = False)
    temporary_path = temporary_file.name
    temporary_file.close()

    command = [
        Constants.FFMPEG_PATH,
        "-y",
        "-v", "error",
        "-threads", "2",
        "-i", path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        temporary_path
    ]

    try:
        logger.debug(f"Converting audio to WAV: {path} -> {temporary_path}")
        result = Utils.run_hidden(command)

        if result.returncode != 0:
            standard_error = (result.stderr or "").lower()

            if "permission" in standard_error or "access is denied" in standard_error:
                raise PermissionError(
                    "Permission error while accessing the file. "
                    "Please check if the file is open in another application."
                )

            raise CorruptedFileError(
                "The audio file is corrupted or in an unsupported format."
            )

        return temporary_path

    except FileNotFoundError:
        raise FileNotFoundError("FFmpeg was not found.")

def analyze_bpm_and_beats(
        audio_path:  str,
        hop_size:    int = 512,
        window_size: int = 1024
    ) -> tuple[float, list[float]]:

    try:
        audio_source = aubio.source(audio_path, 0, hop_size)

    except Exception:
        return 0.0, []

    logger.debug(f"Analyzing BPM and beats for: {audio_path}")

    sample_rate   = audio_source.samplerate or 44100
    tempo_detector = aubio.tempo("default", window_size, hop_size, sample_rate)
    tempo_detector.set_silence(-40)

    detected_beats: list[float] = []
    iteration_count: int        = 0

    while True:
        samples, frames_read = audio_source()

        if tempo_detector(samples):
            detected_beats.append(tempo_detector.get_last_s())

        if frames_read < hop_size:
            break

        iteration_count += 1

        if iteration_count % 60 == 0:
            time.sleep(0.001)

    beats_per_minute = 0.0

    if len(detected_beats) >= 2:
        beats_array = numpy.array(detected_beats, dtype = numpy.float32)
        intervals   = numpy.diff(beats_array)
        valid_intervals = intervals[(intervals > 0.08) & (intervals < 10.0)]

        if valid_intervals.size > 0:
            beats_per_minute = round(float(numpy.median(60.0 / valid_intervals)), 2)

    formatted_beats = [round(float(beat), 3) for beat in detected_beats]

    logger.debug(f"Estimated BPM: {beats_per_minute}")

    return beats_per_minute, formatted_beats

def load_audio(path: str) -> tuple[numpy.ndarray, int]:
    try:
        audio_data, sample_rate = soundfile.read(path, dtype = "float32")
        channel_count           = audio_data.shape[1] if audio_data.ndim > 1 else 1

        logger.info(f"Loaded audio file: {path} (Sample Rate: {sample_rate}, Channels: {channel_count})")

        return audio_data, sample_rate

    except soundfile.LibsndfileError:
        raise CorruptedFileError("The audio file is corrupted or in an unsupported format.")