from __future__ import annotations

import shutil
import threading
from pathlib import Path
from typing import Callable

from .config import AppConfig, get_config
from .constants import MODELS
from .errors import ModelNotFoundError

MODELSCOPE_OWNER = "mlx-community"


def _dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


def download_model(
    model_id: str,
    on_progress: Callable[[int], None] | None = None,
    config: AppConfig | None = None,
) -> Path:
    if model_id not in MODELS:
        raise ModelNotFoundError(f"Unknown model: {model_id}")

    folder = MODELS[model_id]["folder"]
    cfg = config or get_config()
    target = cfg.models_dir / folder
    target.mkdir(parents=True, exist_ok=True)

    stop = threading.Event()

    def reporter() -> None:
        while not stop.wait(1.0):
            if on_progress is not None:
                on_progress(_dir_size(target))

    thread = threading.Thread(target=reporter, daemon=True)
    thread.start()

    try:
        from modelscope import snapshot_download
        snapshot_download(
            f"{MODELSCOPE_OWNER}/{folder}",
            local_dir=str(target),
        )
    finally:
        stop.set()
        thread.join(timeout=2.0)
        if on_progress is not None:
            on_progress(_dir_size(target))

    return target


def delete_model(model_id: str, config: AppConfig | None = None) -> bool:
    if model_id not in MODELS:
        raise ModelNotFoundError(f"Unknown model: {model_id}")
    folder = MODELS[model_id]["folder"]
    cfg = config or get_config()
    target = cfg.models_dir / folder
    if not target.exists():
        return False
    shutil.rmtree(target)
    return True
