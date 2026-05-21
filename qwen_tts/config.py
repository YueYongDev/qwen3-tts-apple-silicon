from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    repo_root: Path
    data_dir: Path
    models_dir: Path
    voices_dir: Path
    outputs_dir: Path
    temp_dir: Path


_ACTIVE_DATA_DIR: Path | None = None


def configure_data_dir(data_dir: str | Path | None) -> None:
    global _ACTIVE_DATA_DIR
    _ACTIVE_DATA_DIR = Path(data_dir).expanduser().resolve() if data_dir else None


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_data_dir() -> Path:
    if _ACTIVE_DATA_DIR is not None:
        return _ACTIVE_DATA_DIR

    configured = os.environ.get("QWEN_TTS_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()

    legacy_root = os.environ.get("QWEN_TTS_REPO_ROOT")
    if legacy_root:
        return Path(legacy_root).expanduser().resolve()

    return default_repo_root()


def get_config(data_dir: str | Path | None = None) -> AppConfig:
    data_root = Path(data_dir).expanduser().resolve() if data_dir else default_data_dir()
    return AppConfig(
        repo_root=default_repo_root(),
        data_dir=data_root,
        models_dir=data_root / "models",
        voices_dir=data_root / "voices",
        outputs_dir=data_root / "outputs",
        temp_dir=data_root / "temp",
    )
