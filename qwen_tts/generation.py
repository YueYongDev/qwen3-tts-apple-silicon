from __future__ import annotations

import gc
import contextlib
import os
import re
import shutil
import subprocess
import time
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import AppConfig, get_config
from .constants import FILENAME_MAX_LEN
from .errors import GenerationError
from .models import get_model_definition, get_model_path
from .voices import get_voice_profile

os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

_MODEL_CACHE: dict[str, Any] = {}


@dataclass(frozen=True)
class GenerationResult:
    output_path: str
    filename: str
    model_id: str
    mode: str


def clean_memory() -> None:
    gc.collect()


def make_temp_dir(config: AppConfig | None = None) -> Path:
    cfg = config or get_config()
    cfg.temp_dir.mkdir(parents=True, exist_ok=True)
    return cfg.temp_dir / f"temp_{int(time.time())}"


def make_output_filename(text_snippet: str) -> str:
    timestamp = datetime.now().strftime("%H-%M-%S")
    clean_text = re.sub(r"[^\w\s-]", "", text_snippet)[:FILENAME_MAX_LEN].strip()
    clean_text = re.sub(r"\s+", "_", clean_text) or "audio"
    return f"{timestamp}_{clean_text}.wav"


def run_quietly(callback: Any, *args: Any, **kwargs: Any) -> Any:
    with open(os.devnull, "w", encoding="utf-8") as sink:
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            return callback(*args, **kwargs)


def load_tts_model(model_id: str, config: AppConfig | None = None) -> Any:
    if model_id in _MODEL_CACHE:
        return _MODEL_CACHE[model_id]

    try:
        from mlx_audio.tts.utils import load_model
    except ImportError as exc:
        raise GenerationError("The 'mlx_audio' library is not installed in this Python environment.") from exc

    model_path = get_model_path(model_id, config=config)
    try:
        model = run_quietly(load_model, str(model_path))
    except Exception as exc:
        raise GenerationError(f"Load failed: {exc}") from exc

    _MODEL_CACHE.clear()
    _MODEL_CACHE[model_id] = model
    return model


def save_generated_audio(
    temp_folder: str | Path,
    output_subfolder: str,
    text_snippet: str,
    config: AppConfig | None = None,
) -> Path:
    cfg = config or get_config()
    save_path = cfg.outputs_dir / output_subfolder
    save_path.mkdir(parents=True, exist_ok=True)
    filename = make_output_filename(text_snippet)
    final_path = save_path / filename
    source_file = Path(temp_folder) / "audio_000.wav"

    if not source_file.exists():
        raise GenerationError(f"Generated audio file not found: {source_file}")

    shutil.move(str(source_file), str(final_path))
    shutil.rmtree(str(temp_folder), ignore_errors=True)
    return final_path


def play_audio(path: str | Path) -> None:
    try:
        subprocess.run(["afplay", str(path)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass


def run_generate_audio_quietly(**kwargs: Any) -> None:
    from mlx_audio.tts.generate import generate_audio

    run_quietly(generate_audio, verbose=False, **kwargs)


def generate_clone(
    model_id: str,
    voice_id: str,
    text: str,
    config: AppConfig | None = None,
    autoplay: bool = False,
) -> GenerationResult:
    cfg = config or get_config()
    info = get_model_definition(model_id)
    if info["mode"] != "clone":
        raise GenerationError(f"Model is not a voice cloning model: {model_id}")
    voice = get_voice_profile(voice_id, cfg)
    model = load_tts_model(model_id, cfg)
    temp_dir = make_temp_dir(cfg)

    try:
        run_generate_audio_quietly(
            model=model,
            text=text,
            ref_audio=voice["audio_path"],
            ref_text=voice["transcript"] or ".",
            output_path=str(temp_dir),
        )
        output_path = save_generated_audio(temp_dir, info["output_subfolder"], text, cfg)
        if autoplay:
            play_audio(output_path)
        return GenerationResult(
            output_path=str(output_path.resolve()),
            filename=output_path.name,
            model_id=model_id,
            mode="clone",
        )
    except GenerationError:
        raise
    except Exception as exc:
        shutil.rmtree(str(temp_dir), ignore_errors=True)
        raise GenerationError(f"Generation failed: {exc}") from exc


def generate_design(model_id: str, instruct: str, text: str, config: AppConfig | None = None, autoplay: bool = False) -> GenerationResult:
    cfg = config or get_config()
    info = get_model_definition(model_id)
    if info["mode"] != "design":
        raise GenerationError(f"Model is not a voice design model: {model_id}")
    model = load_tts_model(model_id, cfg)
    temp_dir = make_temp_dir(cfg)
    try:
        run_generate_audio_quietly(model=model, text=text, instruct=instruct, output_path=str(temp_dir))
        output_path = save_generated_audio(temp_dir, info["output_subfolder"], text, cfg)
        if autoplay:
            play_audio(output_path)
        return GenerationResult(str(output_path.resolve()), output_path.name, model_id, "design")
    except Exception as exc:
        shutil.rmtree(str(temp_dir), ignore_errors=True)
        raise GenerationError(f"Generation failed: {exc}") from exc


def generate_custom(
    model_id: str,
    speaker: str,
    instruct: str,
    speed: float,
    text: str,
    config: AppConfig | None = None,
    autoplay: bool = False,
) -> GenerationResult:
    cfg = config or get_config()
    info = get_model_definition(model_id)
    if info["mode"] != "custom":
        raise GenerationError(f"Model is not a custom voice model: {model_id}")
    model = load_tts_model(model_id, cfg)
    temp_dir = make_temp_dir(cfg)
    try:
        run_generate_audio_quietly(model=model, text=text, voice=speaker, instruct=instruct, speed=speed, output_path=str(temp_dir))
        output_path = save_generated_audio(temp_dir, info["output_subfolder"], text, cfg)
        if autoplay:
            play_audio(output_path)
        return GenerationResult(str(output_path.resolve()), output_path.name, model_id, "custom")
    except Exception as exc:
        shutil.rmtree(str(temp_dir), ignore_errors=True)
        raise GenerationError(f"Generation failed: {exc}") from exc


def list_outputs(config: AppConfig | None = None) -> list[dict]:
    cfg = config or get_config()
    if not cfg.outputs_dir.exists():
        return []
    outputs = []
    for path in sorted(cfg.outputs_dir.glob("*/*.wav"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = path.stat()
        outputs.append(
            {
                "id": str(path.relative_to(cfg.outputs_dir)),
                "filename": path.name,
                "path": str(path.resolve()),
                "created_at": stat.st_mtime,
                "size": stat.st_size,
            }
        )
    return outputs
