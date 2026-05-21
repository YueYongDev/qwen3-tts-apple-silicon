from __future__ import annotations

import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path

from .config import AppConfig, get_config
from .constants import SAMPLE_RATE
from .errors import AudioConversionError


def clean_path(user_input: str) -> str:
    path = user_input.strip()
    if len(path) > 1 and path[0] in ["'", '"'] and path[-1] == path[0]:
        path = path[1:-1]
    return path.replace("\\ ", " ")


def is_valid_wav(path: str | Path) -> bool:
    try:
        with wave.open(str(path), "rb") as wav_file:
            return wav_file.getnchannels() > 0
    except (wave.Error, FileNotFoundError, OSError):
        return False


def ffmpeg_available() -> bool:
    return ffmpeg_executable() is not None


def ffmpeg_executable() -> str | None:
    bundled = Path(sys.executable).resolve().parent / "bin" / "ffmpeg"
    if bundled.exists():
        return str(bundled)
    return shutil.which("ffmpeg")


def convert_audio_if_needed(input_path: str | Path, config: AppConfig | None = None) -> Path:
    cfg = config or get_config()
    source = Path(input_path).expanduser()
    if not source.exists():
        raise AudioConversionError(f"Audio file does not exist: {source}")

    if source.suffix.lower() == ".wav" and is_valid_wav(source):
        return source

    cfg.temp_dir.mkdir(parents=True, exist_ok=True)
    temp_wav = cfg.temp_dir / f"temp_convert_{int(time.time())}.wav"
    ffmpeg = ffmpeg_executable()
    if ffmpeg is None:
        raise AudioConversionError("ffmpeg is not installed or not on PATH.")

    cmd = [
        ffmpeg,
        "-y",
        "-v",
        "error",
        "-i",
        str(source),
        "-ar",
        str(SAMPLE_RATE),
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        str(temp_wav),
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except FileNotFoundError as exc:
        raise AudioConversionError("ffmpeg is not installed or not on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", errors="replace").strip()
        raise AudioConversionError(detail or "Could not convert audio.") from exc

    return temp_wav
